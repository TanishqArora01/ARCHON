import pytest
import asyncio
from pathlib import Path
from sqlalchemy import select
from src.environment.ingestion import RepositoryIngestor
from src.environment.resolver.pipeline import SymbolResolverPipeline
from src.db.session import engine, AsyncSessionLocal
from src.db.models import Base, SymbolEdge, SymbolNode, UnresolvedReference

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "control_repo"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_topology_completion():
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

    # 1. Ingestion
    ingestor = RepositoryIngestor()
    snapshot_id = await ingestor.ingest(FIXTURES_DIR)
    
    # 2. Resolution
    resolver = SymbolResolverPipeline()
    async with AsyncSessionLocal() as session:
        await resolver.execute_pipeline(snapshot_id, session)
        
        # 3. Verify Stage 3: Package Resolution Namespace Identifier
        unresolved = await session.execute(select(UnresolvedReference))
        unresolved = unresolved.scalars().all()
        
        # We should find requests and react as EXTERNAL_DEPENDENCY
        requests_ref = next((r for r in unresolved if r.name == "requests" and "py_repo" in r.file_path), None)
        assert requests_ref is not None, "requests reference not found"
        assert requests_ref.failure_category == "EXTERNAL_DEPENDENCY"
        
        react_ref = next((r for r in unresolved if r.name == "react" and "ts_repo" in r.file_path), None)
        assert react_ref is not None, "react reference not found"
        assert react_ref.failure_category == "EXTERNAL_DEPENDENCY"
        
        # 4. Verify Stage 5: Re-export Resolution Engine
        edges = await session.execute(select(SymbolEdge).where(SymbolEdge.edge_type == "IMPORTS"))
        edges = edges.scalars().all()
        
        # Map node ID to node for easy assertion
        nodes_result = await session.execute(select(SymbolNode))
        nodes = {n.id: n for n in nodes_result.scalars().all()}
        
        print("MAIN.PY NODES:", [n.symbol_name for n in nodes.values() if "main.py" in n.file_path])
        print("INIT.PY NODES:", [(n.symbol_name, n.symbol_type) for n in nodes.values() if "__init__.py" in n.file_path])
        print("UNRESOLVED in MAIN.PY:", [(r.name, r.failure_category) for r in unresolved if "main.py" in r.file_path])

        # Verify Python re-export: main.py -> core.py (BaseController)
        py_main_import_edges = [symbol_edge for symbol_edge in edges if "main.py" in nodes[symbol_edge.from_node_id].file_path]
        print("MAIN.PY EDGES:", py_main_import_edges)
        assert len(py_main_import_edges) > 0, "No imports found in main.py"
        
        py_reexport_resolved = False
        for symbol_edge in py_main_import_edges:
            to_node = nodes[symbol_edge.to_node_id]
            if to_node.symbol_name == "BaseController" and "core.py" in to_node.file_path and to_node.symbol_type == "CLASS":
                py_reexport_resolved = True
                break
        
        assert py_reexport_resolved, "Python re-export (main.py -> core.py) not resolved directly"
        
        # Verify TypeScript re-export: main.ts -> module.ts (BaseService)
        ts_main_import_edges = [symbol_edge for symbol_edge in edges if "main.ts" in nodes[symbol_edge.from_node_id].file_path]
        assert len(ts_main_import_edges) > 0, "No imports found in main.ts"
        
        ts_reexport_resolved = False
        for symbol_edge in ts_main_import_edges:
            to_node = nodes[symbol_edge.to_node_id]
            if to_node.symbol_name == "BaseService" and "module.ts" in to_node.file_path and to_node.symbol_type == "CLASS":
                ts_reexport_resolved = True
                break
        
        assert ts_reexport_resolved, "TypeScript re-export (main.ts -> module.ts) not resolved directly"
