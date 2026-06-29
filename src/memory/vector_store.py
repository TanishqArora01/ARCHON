"""
src/memory/vector_store.py
──────────────────────────
Qdrant-backed memory store for repository documentation and semantic context.
"""
from __future__ import annotations

import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models


class QdrantMemoryStore:
    def __init__(self, client: AsyncQdrantClient) -> None:
        self.client = client

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def initialize_collection(self, collection_name: str, vector_size: int) -> None:
        """Idempotently creates a collection if it does not already exist."""
        exists = await self.client.collection_exists(collection_name=collection_name)
        if not exists:
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

    # ── Write ────────────────────────────────────────────────────────────────

    async def upsert_documents(
        self,
        collection_name: str,
        points: list[dict[str, Any]],
    ) -> None:
        """
        Upserts document chunk points into Qdrant.
        Each dict needs: ``vector`` (list[float]), ``payload`` (dict),
        and optionally ``id`` (UUID string).
        """
        qdrant_points = []
        for point in points:
            point_id = point.get("id") or str(uuid.uuid4())
            qdrant_points.append(
                models.PointStruct(
                    id=point_id,
                    vector=point["vector"],
                    payload=point.get("payload", {}),
                )
            )

        if qdrant_points:
            await self.client.upsert(
                collection_name=collection_name,
                points=qdrant_points,
            )

    # ── Read ─────────────────────────────────────────────────────────────────

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float | None = None,
        filter_payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Dense cosine-similarity search.

        Parameters
        ----------
        filter_payload : dict, optional
            Simple ``{field: value}`` equality filter applied before ranking.
            Example: ``{"snapshot_id": "abc-123"}``

        Returns
        -------
        list[dict] — keys: ``id``, ``score``, ``text``, ``file_path``,
        ``doc_type``, ``payload``.
        """
        exists = await self.client.collection_exists(collection_name=collection_name)
        if not exists:
            return []

        qdrant_filter = None
        if filter_payload:
            qdrant_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                    for key, value in filter_payload.items()
                ]
            )

        results = await self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        output = []
        for point in results.points:
            payload = point.payload or {}
            output.append(
                {
                    "id": str(point.id),
                    "score": point.score,
                    "text": payload.get("text", ""),
                    "file_path": payload.get("file_path", ""),
                    "doc_type": payload.get("doc_type", ""),
                    "payload": payload,
                }
            )
        return output

    # ── Delete ───────────────────────────────────────────────────────────────

    async def delete_snapshot_documents(
        self,
        collection_name: str,
        snapshot_id: str,
    ) -> int:
        """
        Remove all vectors whose payload ``snapshot_id`` equals the given value.
        Returns the number of points deleted.
        """
        exists = await self.client.collection_exists(collection_name=collection_name)
        if not exists:
            return 0

        count_before = await self._count_points(collection_name)
        await self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="snapshot_id",
                            match=models.MatchValue(value=snapshot_id),
                        )
                    ]
                )
            ),
        )
        count_after = await self._count_points(collection_name)
        return max(0, count_before - count_after)

    # ── Stats ────────────────────────────────────────────────────────────────

    async def collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Return ``{exists, point_count, vector_size}`` for a collection."""
        exists = await self.client.collection_exists(collection_name=collection_name)
        if not exists:
            return {"exists": False, "point_count": 0, "vector_size": None}

        info = await self.client.get_collection(collection_name=collection_name)
        vector_size: int | None = None
        if info.config and info.config.params and info.config.params.vectors:
            vc = info.config.params.vectors
            if hasattr(vc, "size"):
                vector_size = vc.size

        return {
            "exists": True,
            "point_count": info.points_count or 0,
            "vector_size": vector_size,
        }

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _count_points(self, collection_name: str) -> int:
        info = await self.client.get_collection(collection_name=collection_name)
        return info.points_count or 0
