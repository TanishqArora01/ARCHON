from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import Repository
from src.services.analysis_pipeline import process_repository_analysis_task
from src.services.jobs import create_analysis_job

logger = logging.getLogger(__name__)


async def enqueue_repository_analysis(
    session: AsyncSession,
    repo: Repository,
    *,
    tenant_id: str | None = None,
    event_type: str = "manual",
    diff_text: str = "",
    event_metadata_extra: dict | None = None,
) -> tuple[str, dict, bool]:
    """
    Create an analysis job and enqueue it on Redis when available.

    Returns (job_id, task_payload, queued_on_redis).
    """
    event_metadata: dict = {"type": event_type}
    if event_metadata_extra:
        event_metadata.update(event_metadata_extra)

    task_payload: dict = {
        "repo_url": repo.clone_url,
        "commit_sha": repo.default_branch or "HEAD",
        "diff_text": diff_text,
        "event_metadata": event_metadata,
        "repository_id": repo.id,
    }
    job = await create_analysis_job(session, task_payload, tenant_id=tenant_id, repository_id=repo.id)
    task_payload["job_id"] = job.id
    await session.flush()

    queued = await push_analysis_task(task_payload)
    return job.id, task_payload, queued


async def push_analysis_task(task_payload: dict) -> bool:
    if not settings.USE_REDIS_QUEUE:
        logger.info("USE_REDIS_QUEUE is False, bypassing Redis queue for job %s", task_payload.get("job_id"))
        return False
        
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            protocol=2,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        await redis_client.lpush("archon:webhook:queue", json.dumps(task_payload))
        await redis_client.aclose()
        return True
    except Exception as exc:
        logger.warning("Redis unavailable, analysis job %s not enqueued: %s", task_payload.get("job_id"), exc)
        return False


async def run_inline_analysis(task_payload: dict) -> None:
    """Run analysis in-process when Redis is unavailable (local development)."""
    try:
        await process_repository_analysis_task(
            task_payload.get("repo_url", ""),
            task_payload.get("commit_sha", "HEAD"),
            task_payload.get("diff_text", ""),
            {
                **task_payload.get("event_metadata", {}),
                "job_id": task_payload.get("job_id"),
                "repository_id": task_payload.get("repository_id"),
            },
        )
    except Exception:
        logger.exception("Inline analysis failed for job %s", task_payload.get("job_id"))
