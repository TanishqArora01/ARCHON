import pytest
import json
import hmac
import hashlib
from fastapi.testclient import TestClient
from unittest.mock import patch
import fakeredis.aioredis

from src.api.webhooks import app

client = TestClient(app)

@pytest.fixture
def mock_redis():
    # Use fakeredis for a lightweight in-memory redis replacement
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    with patch("src.api.webhooks.redis_client", fake_redis):
        yield fake_redis

@pytest.mark.asyncio
async def test_webhook_successful_enqueue(mock_redis):
    delivery_id = "test-delivery-123"
    payload = {
        "repository": {"clone_url": "https://github.com/psf/requests"},
        "after": "abcdef123456",
        "diff_text": "diff --git a/file b/file\n+ new line"
    }

    # Act
    response = client.post(
        "/api/v1/webhooks/vcs",
        json=payload,
        headers={"X-GitHub-Delivery": delivery_id}
    )

    # Assert
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"

    # Check idempotency key was set
    lock_val = await mock_redis.get(f"archon:webhook:idempotency:{delivery_id}")
    assert lock_val == "1"

    # Check queue
    queue_len = await mock_redis.llen("archon:webhook:queue")
    assert queue_len == 1

    queued_item = await mock_redis.rpop("archon:webhook:queue")
    task_payload = json.loads(queued_item)
    assert task_payload["repo_url"] == "https://github.com/psf/requests"
    assert task_payload["commit_sha"] == "abcdef123456"

@pytest.mark.asyncio
async def test_webhook_idempotency_deduplication(mock_redis):
    delivery_id = "test-delivery-456"
    payload = {"repository": {"clone_url": "https://test.com"}, "after": "123"}

    # First call should be accepted
    resp1 = client.post("/api/v1/webhooks/vcs", json=payload, headers={"X-GitHub-Delivery": delivery_id})
    assert resp1.status_code == 202

    # Second call with the SAME delivery ID should be deduplicated
    resp2 = client.post("/api/v1/webhooks/vcs", json=payload, headers={"X-GitHub-Delivery": delivery_id})
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "deduplicated"

    # Queue should only have 1 item
    queue_len = await mock_redis.llen("archon:webhook:queue")
    assert queue_len == 1

def test_webhook_missing_header():
    # Act
    response = client.post(
        "/api/v1/webhooks/vcs",
        json={"repo": "test"}
    )

    # Assert
    assert response.status_code == 400
    assert "Missing X-GitHub-Delivery" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_signature_validation(mock_redis, monkeypatch):
    monkeypatch.setattr("src.api.security.settings.WEBHOOK_SECRET", "secret")
    payload = {
        "repository": {"clone_url": "https://github.com/psf/requests"},
        "after": "abcdef123456",
    }
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    digest = hmac.new(b"secret", raw_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/v1/webhooks/vcs",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": "signed-delivery",
            "X-Hub-Signature-256": f"sha256={digest}",
        },
    )

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_webhook_rate_limit(mock_redis, monkeypatch):
    monkeypatch.setattr("src.api.webhooks.settings.WEBHOOK_RATE_LIMIT_PER_MINUTE", 1)
    payload = {"repository": {"clone_url": "https://test.com"}, "after": "123"}

    first = client.post("/api/v1/webhooks/vcs", json=payload, headers={"X-GitHub-Delivery": "rate-1"})
    second = client.post("/api/v1/webhooks/vcs", json=payload, headers={"X-GitHub-Delivery": "rate-2"})

    assert first.status_code == 202
    assert second.status_code == 429
