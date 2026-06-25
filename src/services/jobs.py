from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AnalysisJob


async def create_analysis_job(
    session: AsyncSession,
    payload: dict,
    tenant_id: str | None = None,
    repository_id: str | None = None,
    queue_name: str = "archon:webhook:queue",
) -> AnalysisJob:
    job = AnalysisJob(
        tenant_id=tenant_id,
        repository_id=repository_id,
        queue_name=queue_name,
        payload=payload,
    )
    session.add(job)
    await session.flush()
    return job
