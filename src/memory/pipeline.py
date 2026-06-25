from pathlib import Path
import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import RepositoryDocument
from src.memory.interfaces import BaseEmbeddingProvider
from src.memory.vector_store import QdrantMemoryStore

class DocumentationPipeline:
    def __init__(
        self,
        provider: BaseEmbeddingProvider,
        store: QdrantMemoryStore,
        collection_name: str,
        db_session: AsyncSession | None = None,
        snapshot_id: str | None = None,
    ):
        self.provider = provider
        self.store = store
        self.collection_name = collection_name
        self.db_session = db_session
        self.snapshot_id = snapshot_id
        self.chunk_size = 500
        
    def _chunk_text(self, text: str) -> list[str]:
        """Simple character-bound chunk splitter."""
        chunks = []
        for i in range(0, len(text), self.chunk_size):
            chunks.append(text[i:i + self.chunk_size])
        return chunks
        
    def _determine_doc_type(self, filepath: Path) -> str:
        name = filepath.name.lower()
        parent = filepath.parent.name.lower()
        if name == "readme.md":
            return "README"
        elif parent == "adr" or "adr-" in name:
            return "ADR"
        elif parent == "rfc" or "rfc-" in name:
            return "RFC"
        elif filepath.suffix == ".json" and "api" in name:
            return "API_SPEC"
        else:
            return "GENERAL_DOC"

    async def ingest_directory(self, target_dir: Path):
        """Crawls directory and ingests documentation files."""
        valid_extensions = {".md", ".txt", ".json"}
        
        points_to_upsert = []
        document_rows: dict[str, RepositoryDocument] = {}
        
        for filepath in target_dir.rglob("*"):
            if filepath.is_dir():
                continue
            
            if filepath.suffix not in valid_extensions:
                continue
                
            try:
                content = filepath.read_text(encoding="utf-8")
            except Exception as e:
                print(f"Skipping {filepath} due to read error: {e}")
                continue
                
            doc_type = self._determine_doc_type(filepath)
            chunks = self._chunk_text(content)
            
            if not chunks:
                continue

            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if self.db_session is not None and self.snapshot_id is not None:
                document_rows[str(filepath)] = RepositoryDocument(
                    snapshot_id=self.snapshot_id,
                    file_path=str(filepath),
                    document_type=doc_type,
                    content_hash=content_hash,
                    meta_data={"chunk_count": len(chunks)},
                )
                
            # Embed all chunks for this file
            embeddings = await self.provider.embed_documents(chunks)
            
            # Prepare points
            for i, (chunk, vector) in enumerate(zip(chunks, embeddings, strict=False)):
                points_to_upsert.append({
                    "id": str(uuid.uuid4()),
                    "vector": vector,
                    "payload": {
                        "text": chunk,
                        "file_path": str(filepath),
                        "doc_type": doc_type,
                        "chunk_index": i,
                        "content_hash": content_hash,
                    },
                })
                
        if points_to_upsert:
            # Assumes vector size matches the provider's output
            vector_size = len(points_to_upsert[0]["vector"])
            await self.store.initialize_collection(self.collection_name, vector_size)
            await self.store.upsert_documents(self.collection_name, points_to_upsert)

        if self.db_session is not None and document_rows:
            self.db_session.add_all(document_rows.values())
            await self.db_session.commit()
