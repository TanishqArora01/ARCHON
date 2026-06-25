import pytest
import asyncio
from pathlib import Path
from sqlalchemy import select, func
from src.environment.ingestion import RepositoryIngestor
from src.db.session import engine, AsyncSessionLocal
from src.db.models import Base, Snapshot, SymbolNode

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "control_repo"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each testcase."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_repository_ingestion_pipeline():
    global engine
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        # Fallback to sqlite if postgres is not available during local test run
        print(f"Failed to connect to Postgres, falling back to SQLite for tests: {e}")
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        import src.db.session
        src.db.session.engine = engine
        src.db.session.AsyncSessionLocal.configure(bind=engine)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    ingestor = RepositoryIngestor()
    
    # Run the crawler
    snapshot_id = await ingestor.ingest(FIXTURES_DIR, "00000000-0000-0000-0000-000000000000")
    
    assert snapshot_id is not None
    
    # Verify via DB
    async with AsyncSessionLocal() as session:
        # Check Snapshot
        snap = await session.get(Snapshot, snapshot_id)
        assert snap is not None
        
        # Count SymbolNodes
        stmt = select(func.count()).select_from(SymbolNode).where(SymbolNode.snapshot_id == snapshot_id)
        result = await session.execute(stmt)
        node_count = result.scalar()
        
        # We expect at least the classes and functions from core.py, module.ts, __init__.py
        # core.py: 2 classes, 1 method, 1 func -> 4 symbols
        # module.ts: 3 exports, 1 interface, 2 classes, 1 method, 1 func -> 8 symbols
        # __init__.py: 1 import -> 1 symbol
        # total expected ~13
        assert node_count >= 13

        # Validate python and ts are processed
        ts_nodes = await session.execute(select(SymbolNode).where(SymbolNode.symbol_name == "ConcreteService"))
        assert ts_nodes.scalars().first() is not None
        
        py_nodes = await session.execute(select(SymbolNode).where(SymbolNode.symbol_name == "ConcreteController"))
        assert py_nodes.scalars().first() is not None
