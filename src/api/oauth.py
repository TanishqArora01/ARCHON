from __future__ import annotations

import secrets
import time
from urllib.parse import urlencode

import httpx
import redis.asyncio as redis
from redis.exceptions import RedisError
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from src.api.auth import create_session_token
from src.core.config import settings
from src.core.secrets import SecretManager
from src.db.models import VCSInstallation
from src.db.session import AsyncSessionLocal
from src.services.repositories import get_or_create_default_tenant

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
_local_oauth_state: dict[str, tuple[str, float]] = {}
OAUTH_STATE_TTL_SECONDS = 600


@router.get("/{provider}/start")
async def start_oauth(provider: str) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    if provider == "github":
        if not settings.GITHUB_OAUTH_CLIENT_ID or not settings.GITHUB_OAUTH_REDIRECT_URI:
            raise HTTPException(status_code=500, detail="GitHub OAuth is not configured")
        await _store_oauth_state(state, provider)
        query = urlencode(
            {
                "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
                "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
                "scope": "repo read:org",
                "state": state,
            }
        )
        return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")
    if provider == "gitlab":
        if not settings.GITLAB_OAUTH_CLIENT_ID or not settings.GITLAB_OAUTH_REDIRECT_URI:
            raise HTTPException(status_code=500, detail="GitLab OAuth is not configured")
        await _store_oauth_state(state, provider)
        query = urlencode(
            {
                "client_id": settings.GITLAB_OAUTH_CLIENT_ID,
                "redirect_uri": settings.GITLAB_OAUTH_REDIRECT_URI,
                "response_type": "code",
                "scope": "api read_repository",
                "state": state,
            }
        )
        return RedirectResponse(f"{settings.GITLAB_API_URL.rstrip('/')}/oauth/authorize?{query}")
    raise HTTPException(status_code=404, detail="Unsupported OAuth provider")


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str) -> RedirectResponse:
    stored_provider = await _pop_oauth_state(state)
    if stored_provider != provider:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    token_data = await _exchange_code(provider, code)
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="OAuth provider did not return an access token")

    # Fetch user info from the provider
    username = await _fetch_username(provider, access_token)

    secret_manager = SecretManager()
    async with AsyncSessionLocal() as session:
        tenant = await get_or_create_default_tenant(session)
        installation = VCSInstallation(
            tenant_id=tenant.id,
            provider=provider,
            access_token_ciphertext=secret_manager.encrypt(access_token),
            refresh_token_ciphertext=secret_manager.encrypt(refresh_token),
            meta_data={
                "token_type": token_data.get("token_type"),
                "scope": token_data.get("scope"),
                "username": username,
            },
        )
        session.add(installation)
        await session.flush()
        await session.commit()

        # Create a JWT session token and redirect back to the frontend SPA
        jwt_token = create_session_token(
            provider=provider,
            installation_id=installation.id,
            tenant_id=tenant.id,
            extra={"username": username},
        )

        frontend_callback = f"{settings.FRONTEND_URL}/oauth/callback"
        redirect_query = urlencode({"token": jwt_token, "provider": provider})
        return RedirectResponse(f"{frontend_callback}?{redirect_query}")


async def _store_oauth_state(state: str, provider: str) -> None:
    try:
        await redis_client.set(f"archon:oauth:state:{state}", provider, ex=OAUTH_STATE_TTL_SECONDS)
    except RedisError as exc:
        if settings.ENVIRONMENT not in {"development", "test"}:
            raise HTTPException(status_code=503, detail="OAuth state store is unavailable") from exc
        _local_oauth_state[state] = (provider, time.time() + OAUTH_STATE_TTL_SECONDS)


async def _pop_oauth_state(state: str) -> str | None:
    try:
        provider = await redis_client.get(f"archon:oauth:state:{state}")
        if provider is not None:
            await redis_client.delete(f"archon:oauth:state:{state}")
        return provider
    except RedisError as exc:
        if settings.ENVIRONMENT not in {"development", "test"}:
            raise HTTPException(status_code=503, detail="OAuth state store is unavailable") from exc

    now = time.time()
    expired_states = [key for key, (_, expires_at) in _local_oauth_state.items() if expires_at <= now]
    for key in expired_states:
        _local_oauth_state.pop(key, None)

    state_record = _local_oauth_state.pop(state, None)
    if state_record is None:
        return None
    provider, expires_at = state_record
    if expires_at <= now:
        return None
    return provider


async def _exchange_code(provider: str, code: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        if provider == "github":
            if not settings.GITHUB_OAUTH_CLIENT_ID or not settings.GITHUB_OAUTH_CLIENT_SECRET:
                raise HTTPException(status_code=500, detail="GitHub OAuth is not configured")
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
                    "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
                },
            )
        elif provider == "gitlab":
            if not settings.GITLAB_OAUTH_CLIENT_ID or not settings.GITLAB_OAUTH_CLIENT_SECRET:
                raise HTTPException(status_code=500, detail="GitLab OAuth is not configured")
            response = await client.post(
                f"{settings.GITLAB_API_URL.rstrip('/')}/oauth/token",
                data={
                    "client_id": settings.GITLAB_OAUTH_CLIENT_ID,
                    "client_secret": settings.GITLAB_OAUTH_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GITLAB_OAUTH_REDIRECT_URI,
                },
            )
        else:
            raise HTTPException(status_code=404, detail="Unsupported OAuth provider")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail=f"{provider.title()} OAuth token exchange failed") from exc
        return response.json()


async def _fetch_username(provider: str, access_token: str) -> str | None:
    """Fetch the authenticated user's username from the OAuth provider."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "github":
                resp = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "Archon",
                    },
                )
                resp.raise_for_status()
                return resp.json().get("login")
            elif provider == "gitlab":
                resp = await client.get(
                    f"{settings.GITLAB_API_URL.rstrip('/')}/api/v4/user",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                return resp.json().get("username")
    except Exception:
        pass
    return None
