import uuid
from typing import List, Dict, Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

class QdrantMemoryStore:
    def __init__(self, client: AsyncQdrantClient):
        self.client = client
        
    async def initialize_collection(self, collection_name: str, vector_size: int):
        """Safely checks and creates a collection if it does not exist."""
        exists = await self.client.collection_exists(collection_name=collection_name)
        if not exists:
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            
    async def upsert_documents(self, collection_name: str, points: List[Dict[str, Any]]):
        """
        Upserts a list of document points into Qdrant.
        Expects each point dict to have:
        - id (optional UUID string, generates one if missing)
        - vector (List[float])
        - payload (Dict mapping to metadata including 'text')
        """
        qdrant_points = []
        for point in points:
            point_id = point.get("id")
            if not point_id:
                point_id = str(uuid.uuid4())
                
            qdrant_points.append(
                models.PointStruct(
                    id=point_id,
                    vector=point["vector"],
                    payload=point.get("payload", {})
                )
            )
            
        if qdrant_points:
            await self.client.upsert(
                collection_name=collection_name,
                points=qdrant_points
            )
