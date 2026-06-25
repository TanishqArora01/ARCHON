from __future__ import annotations

import asyncio
import logging

import redis.asyncio as redis

from src.core.config import settings
from src.worker.tasks import worker_loop


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = redis.from_url(settings.REDIS_URL, decode_responses=True, protocol=2)
    asyncio.run(worker_loop(client))


if __name__ == "__main__":
    main()
