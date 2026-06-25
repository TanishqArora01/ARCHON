from __future__ import annotations

import hmac
import hashlib

import redis.asyncio as redis
from fastapi import Header, HTTPException, Request, status

from src.api.auth import decode_session_token
from src.core.config import settings


async def require_api_token(authorization: str | None = Header(None)) -> None:
    if not settings.API_AUTH_TOKEN:
        return

    if authorization and authorization.startswith("Bearer "):
        supplied_token = authorization.removeprefix("Bearer ").strip()
        if hmac.compare_digest(supplied_token, settings.API_AUTH_TOKEN):
            return
        try:
            decode_session_token(supplied_token)
            return
        except HTTPException:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API token",
    )


async def verify_webhook_signature(
    request: Request,
    x_hub_signature_256: str | None,
) -> None:
    if not settings.WEBHOOK_SECRET:
        return

    if not x_hub_signature_256 or not x_hub_signature_256.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature",
        )

    body = await request.body()
    expected_digest = hmac.new(
        settings.WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    expected_header = f"sha256={expected_digest}"
    if not hmac.compare_digest(x_hub_signature_256, expected_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )


async def enforce_rate_limit(
    redis_client: redis.Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window_seconds)
    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
