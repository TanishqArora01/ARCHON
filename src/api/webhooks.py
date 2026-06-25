import json
import logging
from typing import Any

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import redis.asyncio as redis

from src.api.security import enforce_rate_limit, verify_webhook_signature
from src.core.config import settings
from src.db.session import AsyncSessionLocal
from src.services.jobs import create_analysis_job
from src.services.repositories import get_or_create_default_tenant, upsert_repository

logger = logging.getLogger(__name__)

router = APIRouter()

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class WebhookPayload(BaseModel):
    repository: dict[str, Any] = Field(default_factory=dict)
    after: str | None = None
    pull_request: dict[str, Any] = Field(default_factory=dict)
    repo_url: str | None = None
    commit_sha: str | None = None
    diff_text: str = ""

    model_config = {"extra": "allow"}

    @property
    def resolved_repo_url(self) -> str | None:
        return self.repository.get("clone_url") or self.repo_url

    @property
    def resolved_commit_sha(self) -> str | None:
        return (
            self.after
            or self.pull_request.get("head", {}).get("sha")
            or self.commit_sha
        )


@router.post("/api/v1/webhooks/vcs")
async def vcs_webhook(
    request: Request,
    payload: WebhookPayload,
    x_github_delivery: str | None = Header(None),
    x_hub_signature_256: str | None = Header(None),
):
    if not x_github_delivery:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Delivery header")

    await verify_webhook_signature(request, x_hub_signature_256)

    client_host = request.client.host if request.client else "unknown"
    rate_key = f"archon:webhook:rate:{client_host}"
    try:
        await enforce_rate_limit(
            redis_client,
            rate_key,
            settings.WEBHOOK_RATE_LIMIT_PER_MINUTE,
            60,
        )
    except redis.ConnectionError:
        logger.warning("Redis connection failed, skipping webhook rate limit")

    # Idempotency check via Redis SETNX
    lock_key = f"archon:webhook:idempotency:{x_github_delivery}"
    try:
        acquired = await redis_client.set(
            lock_key,
            "1",
            nx=True,
            ex=settings.WEBHOOK_IDEMPOTENCY_TTL_SECONDS,
        )

        if not acquired:
            logger.info("Duplicate webhook delivery detected: %s", x_github_delivery)
            return JSONResponse(status_code=200, content={"status": "deduplicated", "message": "Duplicate event ignored"})

    except redis.ConnectionError:
        logger.warning("Redis connection failed, skipping idempotency check")

    repo_url = payload.resolved_repo_url
    commit_sha = payload.resolved_commit_sha

    task_payload = {
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "diff_text": payload.diff_text,
        "event_metadata": payload.model_dump(mode="json"),
    }

    try:
        async with AsyncSessionLocal() as session:
            tenant = await get_or_create_default_tenant(session)
            repository_id = None
            if repo_url:
                repo_owner, repo_name = _extract_repo_identity(repo_url)
                repository = await upsert_repository(
                    session,
                    provider="github" if "github" in repo_url else "git",
                    owner=repo_owner,
                    name=repo_name,
                    clone_url=repo_url,
                    default_branch=payload.repository.get("default_branch"),
                    tenant_id=tenant.id,
                )
                repository_id = repository.id
            job = await create_analysis_job(session, task_payload, tenant_id=tenant.id, repository_id=repository_id)
            task_payload["job_id"] = job.id
            task_payload["repository_id"] = repository_id
            await session.commit()
    except Exception as exc:
        logger.warning("Could not persist webhook job metadata: %s", exc)

    try:
        await redis_client.lpush("archon:webhook:queue", json.dumps(task_payload))
    except redis.ConnectionError as exc:
        logger.warning("Redis connection failed, could not enqueue task")
        raise HTTPException(status_code=503, detail="Queue service unavailable") from exc

    return JSONResponse(status_code=202, content={"status": "accepted", "message": "Webhook queued for processing"})


def _extract_repo_identity(repo_url: str) -> tuple[str, str]:
    trimmed = repo_url.rstrip("/").removesuffix(".git")
    parts = trimmed.split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "unknown", trimmed or "unknown"


app = FastAPI(title="Archon Webhooks API")
app.include_router(router)
