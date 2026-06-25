import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from src.db.models import Base, SymbolNode, SymbolEdge, UnresolvedReference
from src.db.session import AsyncSessionLocal
from src.environment.ingestion import RepositoryIngestor
from src.environment.resolver.pipeline import SymbolResolverPipeline
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "control_repo"

engine = create_async_engine("sqlite+aiosqlite:///:memory:")

@pytest.mark.asyncio
async def test_naming_variance_pipeline():
    import src.db.session
    src.db.session.engine = engine
    src.db.session.AsyncSessionLocal.configure(bind=engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # 1. Run Ingestion
    ingestor = RepositoryIngestor()
    snapshot_id = await ingestor.ingest(FIXTURES_DIR)

    # 2. Run Resolver Pipeline (which now includes Stage 1 and Stage 4)
    resolver = SymbolResolverPipeline()
    async with AsyncSessionLocal() as session:
        await resolver.execute_pipeline(snapshot_id, session)

        nodes_result = await session.execute(select(SymbolNode))
        nodes = {n.id: n for n in nodes_result.scalars().all()}

        # 3. Assert Naming Variance Resolution
        # 3a. Verify UnresolvedReference for `Widget` does NOT exist
        unresolved_result = await session.execute(select(UnresolvedReference))
        unresolved = unresolved_result.scalars().all()
        widget_unresolved = [u for u in unresolved if u.name == "Widget" and "naming_variance.ts" in u.file_path]
        assert len(widget_unresolved) == 0, "Widget should be completely resolved, no UnresolvedReference expected."

        # 3b. Verify Edge mapping
        # naming_variance.ts imports `Widget`. The IMPORTS edge should point to `privateCore`.
        edges_result = await session.execute(select(SymbolEdge).where(SymbolEdge.edge_type == "IMPORTS"))
        imports_edges = edges_result.scalars().all()

        naming_variance_imports = []
        for e in imports_edges:
            f_node = nodes[e.from_node_id]
            if "naming_variance.ts" in f_node.file_path:
                naming_variance_imports.append(e)

        assert len(naming_variance_imports) >= 1, "Missing IMPORTS edge in naming_variance.ts"

        target_nodes = [nodes[e.to_node_id].symbol_name for e in naming_variance_imports]
        assert "privateCore" in target_nodes, f"Expected privateCore in targets, got {target_nodes}"

        # Also verify that Python Stage 4 export logic resolves without crash
        # (Already tested by existing tests implicitly if nothing broke)
