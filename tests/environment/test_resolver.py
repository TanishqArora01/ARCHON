import pytest
import asyncio
from pathlib import Path
from sqlalchemy import select
from src.environment.ingestion import RepositoryIngestor
from src.environment.resolver.pipeline import SymbolResolverPipeline
from src.db.session import engine, AsyncSessionLocal
from src.db.models import Base, SymbolEdge, SymbolNode

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "control_repo"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_resolver_pipeline():
    global engine
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        print(f"Fallback to SQLite: {exc}")
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
        
        # 3. Assert IMPORTS edge created
        # We expect __init__.py to import BaseController and ConcreteController from core.py
        import_edges = await session.execute(select(SymbolEdge).where(SymbolEdge.edge_type == "IMPORTS"))
        import_edges = import_edges.scalars().all()
        assert len(import_edges) >= 2
        
        # Check that it links to actual nodes
        # We need to filter for edges originating from __init__.py, since main.py is also parsed and flattened
        init_edges = []
        for symbol_edge in import_edges:
            f_node = await session.get(SymbolNode, symbol_edge.from_node_id)
            if "__init__.py" in f_node.file_path:
                init_edges.append(symbol_edge)

        assert len(init_edges) >= 2

        to_node = await session.get(SymbolNode, init_edges[0].to_node_id)
        assert to_node.symbol_name in ["BaseController", "ConcreteController"]
        assert "core.py" in to_node.file_path
        
        # 4. Assert CALLS edge created
        # ConcreteController.handle_request calls validate()
        # ConcreteService.process calls validate()
        call_edges = await session.execute(select(SymbolEdge).where(SymbolEdge.edge_type == "CALLS"))
        call_edges = call_edges.scalars().all()
        assert len(call_edges) >= 2
        
        called_nodes = []
        for edge in call_edges:
            called_nodes.append(await session.get(SymbolNode, edge.to_node_id))
            
        assert any(n.symbol_name == "validate" for n in called_nodes)
        assert any(n.symbol_name == "normalize" for n in called_nodes)
