import pytest
import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import AsyncQdrantClient

from src.db.models import Base, Snapshot, SymbolNode, SymbolEdge
from src.memory.interfaces import BaseEmbeddingProvider
from src.memory.vector_store import QdrantMemoryStore
from src.retrieval.engine import HybridRetrievalEngine
from src.retrieval.assembler import ContextAssembler

class MockEmbeddingProvider(BaseEmbeddingProvider):
    async def embed_query(self, text: str) -> list[float]:
        return [0.5, 0.5, 0.5, 0.5]
        
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.5, 0.5, 0.5, 0.5] for _ in texts]

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_execute_fused_retrieval():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as db_session:
        # 1. Setup mock SQLite database data
        snapshot_id = str(uuid.uuid4())
        snapshot = Snapshot(id=snapshot_id)
        db_session.add(snapshot)
    
        node_a = SymbolNode(
            id=str(uuid.uuid4()), snapshot_id=snapshot_id, file_path="core/auth.py", 
            symbol_name="AuthService", symbol_type="class", meta_data={}
        )
        node_b = SymbolNode(
            id=str(uuid.uuid4()), snapshot_id=snapshot_id, file_path="api/routes.py", 
            symbol_name="login", symbol_type="function", meta_data={}
        )
        
        edge = SymbolEdge(
            id=str(uuid.uuid4()), snapshot_id=snapshot_id, 
            from_node_id=node_b.id, to_node_id=node_a.id, edge_type="CALLS"
        )
        
        db_session.add_all([node_a, node_b, edge])
        await db_session.commit()
    
        # 2. Setup mock Qdrant collection and data
        qclient = AsyncQdrantClient(location=":memory:")
        qstore = QdrantMemoryStore(qclient)
        collection_name = "test_hybrid_retrieval"
        
        await qstore.initialize_collection(collection_name, 4)
        
        await qstore.upsert_documents(collection_name, [
            {
                "id": str(uuid.uuid4()),
                "vector": [0.5, 0.5, 0.5, 0.5],
                "payload": {
                    "text": "AuthService acts as the single source of truth.",
                    "file_path": "docs/adr/ADR-002-auth.md",
                    "doc_type": "ADR"
                }
            }
        ])
    
        # 3. Execute hybrid retrieval
        provider = MockEmbeddingProvider()
        engine = HybridRetrievalEngine(provider)
        
        context = await engine.execute_fused_retrieval(
            db_session=db_session,
            qdrant_store=qstore,
            snapshot_id=snapshot_id,
            collection_name=collection_name,
            target_symbol_id=node_a.id,
            query_text="authentication mechanisms"
        )
    
        # 4. Assert Structural Outputs
        # A change to node_a (AuthService) affects node_b (login) because node_b CALLS node_a.
        assert node_b.id in context.structural.impacted_symbol_ids
        assert "core/auth.py" in context.structural.impacted_file_paths
        assert "api/routes.py" in context.structural.impacted_file_paths
        assert context.structural.blast_radius_score > 0.0
    
        # 5. Assert Semantic Outputs
        assert len(context.semantic.documentation_chunks) == 1
        assert "AuthService" in context.semantic.documentation_chunks[0]
        assert "ADR-002" in context.semantic.source_files[0]
    
        # 6. Verify Context Assembler Formatting
        markdown_output = ContextAssembler.format_context_for_llm(context)
        assert markdown_output.startswith("<!-- TRACKING_TOKEN: ")
        assert "STRUCTURAL IMPACT ANALYSIS" in markdown_output
        assert "api/routes.py" in markdown_output
        assert "ADR-002-auth.md" in markdown_output
        assert "AuthService acts as the single source of truth." in markdown_output


@pytest.mark.asyncio
async def test_execute_fused_retrieval_includes_repository_rule_violations(tmp_path):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    rules_dir = tmp_path / ".aegis"
    rules_dir.mkdir()
    rules_dir.joinpath("rules.yaml").write_text(
        """
Controller:
  can_call:
    - Service
  cannot_call:
    - Database
Database: {}
""",
        encoding="utf-8",
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db_session:
        snapshot_id = str(uuid.uuid4())
        snapshot = Snapshot(id=snapshot_id, repository_path=str(tmp_path))
        db_session.add(snapshot)

        controller = SymbolNode(
            id=str(uuid.uuid4()),
            snapshot_id=snapshot_id,
            file_path="controllers/user_controller.py",
            symbol_name="UserController",
            symbol_type="CLASS",
            meta_data={},
        )
        database = SymbolNode(
            id=str(uuid.uuid4()),
            snapshot_id=snapshot_id,
            file_path="db/database.py",
            symbol_name="Database",
            symbol_type="DATABASE",
            meta_data={},
        )
        edge = SymbolEdge(
            id=str(uuid.uuid4()),
            snapshot_id=snapshot_id,
            from_node_id=controller.id,
            to_node_id=database.id,
            edge_type="CALLS",
        )
        db_session.add_all([controller, database, edge])
        await db_session.commit()

        qclient = AsyncQdrantClient(location=":memory:")
        qstore = QdrantMemoryStore(qclient)

        context = await HybridRetrievalEngine(MockEmbeddingProvider()).execute_fused_retrieval(
            db_session=db_session,
            qdrant_store=qstore,
            snapshot_id=snapshot_id,
            collection_name="empty_docs",
            target_symbol_id=database.id,
            query_text="architecture boundary",
        )

        assert len(context.structural.architecture_violations) == 1
        violation = context.structural.architecture_violations[0]
        assert violation["from_component"] == "Controller"
        assert violation["to_component"] == "Database"
        assert violation["rule_type"] == "cannot_call"

        markdown_output = ContextAssembler.format_context_for_llm(context)
        assert "Repository Rule Violations" in markdown_output
        assert "cannot call Database" in markdown_output
