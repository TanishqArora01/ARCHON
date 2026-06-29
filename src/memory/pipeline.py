from pathlib import Path
import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import RepositoryDocument
from src.memory.interfaces import BaseEmbeddingProvider
from src.memory.vector_store import QdrantMemoryStore

# Characters per chunk / overlap for sliding window splitter
_CHUNK_SIZE    = 600
_CHUNK_OVERLAP = 80

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

    # ── Chunking ─────────────────────────────────────────────────────────────

    def _chunk_text(self, text: str) -> list[str]:
        """
        Sliding-window character splitter with overlap.

        Produces chunks of ~_CHUNK_SIZE characters, each overlapping the
        previous by _CHUNK_OVERLAP chars so context is never hard-truncated
        at a chunk boundary.
        """
        chunks: list[str] = []
        step = _CHUNK_SIZE - _CHUNK_OVERLAP
        if step <= 0:
            step = _CHUNK_SIZE
        for i in range(0, max(1, len(text)), step):
            chunk = text[i : i + _CHUNK_SIZE].strip()
            if chunk:
                chunks.append(chunk)
            if i + _CHUNK_SIZE >= len(text):
                break
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
        
        for filepath in target_dir.rglob("*"):
            if filepath.is_dir():
                continue
            
            if filepath.suffix not in valid_extensions:
                continue
                
            await self.ingest_file(filepath)

    async def ingest_file(self, filepath: Path) -> None:
        """Ingests a single file into the documentation vector store."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Skipping {filepath} due to read error: {e}")
            return
            
        doc_type = self._determine_doc_type(filepath)
        chunks = self._chunk_text(content)
        
        if not chunks:
            return

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        if self.db_session is not None and self.snapshot_id is not None:
            doc_record = RepositoryDocument(
                snapshot_id=self.snapshot_id,
                file_path=str(filepath),
                document_type=doc_type,
                content_hash=content_hash,
                meta_data={"chunk_count": len(chunks)},
            )
            self.db_session.add(doc_record)
            await self.db_session.commit()
            
        # Embed all chunks for this file
        embeddings = await self.provider.embed_documents(chunks)
        
        # Prepare points
        points_to_upsert = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings, strict=False)):
            payload = {
                "text": chunk,
                "file_path": str(filepath),
                "doc_type": doc_type,
                "chunk_index": i,
                "content_hash": content_hash,
            }
            if self.snapshot_id:
                payload["snapshot_id"] = self.snapshot_id
                
            points_to_upsert.append({
                "id": str(uuid.uuid4()),
                "vector": vector,
                "payload": payload,
            })
            
        if points_to_upsert:
            # Assumes vector size matches the provider's output
            vector_size = len(points_to_upsert[0]["vector"])
            await self.store.initialize_collection(self.collection_name, vector_size)
            await self.store.upsert_documents(self.collection_name, points_to_upsert)
