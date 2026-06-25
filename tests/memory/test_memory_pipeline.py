import pytest
from qdrant_client import AsyncQdrantClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models import Base, RepositoryDocument, Snapshot
from src.memory.interfaces import BaseEmbeddingProvider
from src.memory.vector_store import QdrantMemoryStore
from src.memory.pipeline import DocumentationPipeline

class MockEmbeddingProvider(BaseEmbeddingProvider):
    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3, 0.4]
        
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Return a simple mock embedding for each document
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

@pytest.fixture
def mock_docs_dir(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    
    # Create README
    readme = tmp_path / "README.md"
    readme.write_text("# Archon\nThis is the core platform.", encoding="utf-8")
    
    # Create ADR
    adr_dir = docs_dir / "adr"
    adr_dir.mkdir()
    adr = adr_dir / "ADR-001.md"
    adr.write_text("# ADR 001\nWe will use Qdrant for memory.", encoding="utf-8")
    
    return tmp_path

@pytest.mark.asyncio
async def test_memory_pipeline(mock_docs_dir):
    provider = MockEmbeddingProvider()
    client = AsyncQdrantClient(location=":memory:")
    store = QdrantMemoryStore(client)
    
    collection_name = "test_archon_memory"
    
    pipeline = DocumentationPipeline(provider, store, collection_name)
    await pipeline.ingest_directory(mock_docs_dir)
    
    # Assert collection exists
    assert await client.collection_exists(collection_name)
    
    # Count points
    count_result = await client.count(collection_name)
    assert count_result.count == 2
    
    # Scroll points to verify metadata
    points, _ = await client.scroll(collection_name, limit=10)
    
    doc_types = [p.payload["doc_type"] for p in points]
    assert "README" in doc_types
    assert "ADR" in doc_types
    
    texts = [p.payload["text"] for p in points]
    assert any("Archon" in t for t in texts)
    assert any("Qdrant" in t for t in texts)


@pytest.mark.asyncio
async def test_memory_pipeline_persists_document_metadata(mock_docs_dir):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        snapshot = Snapshot(id="snapshot-docs")
        session.add(snapshot)
        await session.commit()

        provider = MockEmbeddingProvider()
        client = AsyncQdrantClient(location=":memory:")
        store = QdrantMemoryStore(client)
        pipeline = DocumentationPipeline(
            provider,
            store,
            "test_archon_memory_db",
            db_session=session,
            snapshot_id=snapshot.id,
        )
        await pipeline.ingest_directory(mock_docs_dir)

        result = await session.execute(select(RepositoryDocument))
        docs = result.scalars().all()
        assert len(docs) == 2
        assert {doc.document_type for doc in docs} == {"README", "ADR"}
