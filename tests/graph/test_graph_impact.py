import pytest
import asyncio
from pathlib import Path
from sqlalchemy import select
from src.environment.ingestion import RepositoryIngestor
from src.environment.resolver.pipeline import SymbolResolverPipeline
from src.graph.builder import NetworkXGraphBuilder
from src.graph.traverser import GraphImpactTraverser
from src.db.session import engine, AsyncSessionLocal
from src.db.models import Base, SymbolNode

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "control_repo"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_graph_impact_analysis():
    global engine
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Fallback to SQLite: {e}")
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        import src.db.session
        src.db.session.engine = engine
        src.db.session.AsyncSessionLocal.configure(bind=engine)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # 1. Run Ingestion
    ingestor = RepositoryIngestor()
    snapshot_id = await ingestor.ingest(FIXTURES_DIR, "00000000-0000-0000-0000-000000000000")
    
    # 2. Run Resolver
    resolver = SymbolResolverPipeline()
    async with AsyncSessionLocal() as session:
        await resolver.execute_pipeline(snapshot_id, session)
        
        # 3. Build Graph using src/graph/builder
        builder = NetworkXGraphBuilder()
        graph = await builder.build_snapshot_graph(session, snapshot_id)
        
        # Assert graph has nodes and edges
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0
        
        # 4. Impact Analysis
        # Let's test the helper function 'validate' inside ConcreteController/ConcreteService
        # First, find the validate function or the BaseController class
        stmt = select(SymbolNode).where(SymbolNode.symbol_name == "BaseController").where(SymbolNode.snapshot_id == snapshot_id)
        res = await session.execute(stmt)
        base_controller = res.scalars().first()
        assert base_controller is not None
        
        # Now find ConcreteController
        stmt = select(SymbolNode).where(SymbolNode.symbol_name == "ConcreteController").where(SymbolNode.snapshot_id == snapshot_id)
        res = await session.execute(stmt)
        concrete_controller = res.scalars().first()
        assert concrete_controller is not None
        
        # ConcreteController INHERITS BaseController, meaning if BaseController changes, ConcreteController is impacted.
        impact_result = GraphImpactTraverser.calculate_blast_radius(graph, base_controller.id)
        
        impacted_nodes = impact_result["impacted_node_ids"]
        score = impact_result["blast_radius_score"]
        
        assert isinstance(impacted_nodes, list)
        assert isinstance(score, float)
        assert score > 0.0
        
        assert concrete_controller.id in impacted_nodes
