"""Background worker task entrypoints."""

from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as redis

from src.services.analysis_pipeline import process_repository_analysis_task

logger = logging.getLogger(__name__)


async def worker_loop(redis_client: redis.Redis) -> None:
    logger.info("Starting background worker loop...")
    while True:
        try:
            result = await redis_client.brpop("archon:webhook:queue", timeout=0)
            if result:
                _, item_data = result
                payload = json.loads(item_data)

                repo_url = payload.get("repo_url", "")
                commit_sha = payload.get("commit_sha", "")
                diff_text = payload.get("diff_text", "")
                event_metadata = payload.get("event_metadata", {})
                if payload.get("job_id"):
                    event_metadata["job_id"] = payload["job_id"]
                if payload.get("repository_id"):
                    event_metadata["repository_id"] = payload["repository_id"]

                await process_repository_analysis_task(repo_url, commit_sha, diff_text, event_metadata)
        except Exception as exc:
            logger.error("Error processing background task: %s", exc, exc_info=True)
            await asyncio.sleep(1)
