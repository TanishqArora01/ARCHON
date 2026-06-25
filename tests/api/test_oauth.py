from fastapi.testclient import TestClient
import pytest

from src.api.auth import create_session_token
from src.api.app import create_app
from src.api.oauth import router
from fastapi import FastAPI
from redis.exceptions import ConnectionError


def test_github_oauth_start_requires_config(monkeypatch):
    monkeypatch.setattr("src.api.oauth.settings.GITHUB_OAUTH_CLIENT_ID", None)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/api/v1/oauth/github/start", follow_redirects=False)

    assert response.status_code == 500


def test_protected_api_accepts_session_token_when_service_token_is_configured(monkeypatch):
    monkeypatch.setattr("src.api.security.settings.API_AUTH_TOKEN", "service-token")
    token = create_session_token(provider="github", installation_id="installation-1", tenant_id="tenant-1")
    client = TestClient(create_app())

    response = client.get("/api/v1/version", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_oauth_state_falls_back_to_local_store_in_development(monkeypatch):
    from src.api import oauth

    class UnavailableRedis:
        async def set(self, *args, **kwargs):
            raise ConnectionError("redis unavailable")

        async def get(self, *args, **kwargs):
            raise ConnectionError("redis unavailable")

        async def delete(self, *args, **kwargs):
            raise ConnectionError("redis unavailable")

    monkeypatch.setattr(oauth.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(oauth, "redis_client", UnavailableRedis())
    oauth._local_oauth_state.clear()

    await oauth._store_oauth_state("state-1", "github")

    assert await oauth._pop_oauth_state("state-1") == "github"
    assert await oauth._pop_oauth_state("state-1") is None
