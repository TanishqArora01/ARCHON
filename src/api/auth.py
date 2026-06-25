from __future__ import annotations

import datetime
import base64
import hashlib
import hmac
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select

from src.core.config import settings
from src.db.models import VCSInstallation
from src.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 72


def create_session_token(
    provider: str,
    installation_id: str,
    tenant_id: str,
    extra: dict[str, Any] | None = None,
) -> str:
    """Create a JWT session token after successful OAuth."""
    payload = {
        "sub": installation_id,
        "provider": provider,
        "tenant_id": tenant_id,
        "iat": datetime.datetime.now(datetime.UTC),
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    if extra:
        payload.update(extra)
    return _encode_jwt(payload)


def decode_session_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT session token."""
    payload = _decode_jwt(token)
    exp = payload.get("exp")
    if not isinstance(exp, int | float):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if datetime.datetime.now(datetime.UTC).timestamp() >= exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return payload


def _encode_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    normalized_payload = {
        key: int(value.timestamp()) if isinstance(value, datetime.datetime) else value
        for key, value in payload.items()
    }
    header_part = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _base64url_encode(json.dumps(normalized_payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}"
    signature = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url_encode(signature)}"


def _decode_jwt(token: str) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected_signature = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        supplied_signature = _base64url_decode(signature_part)
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError("Invalid signature")
        header = json.loads(_base64url_decode(header_part))
        if header.get("alg") != JWT_ALGORITHM:
            raise ValueError("Unsupported algorithm")
        payload = json.loads(_base64url_decode(payload_part))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


async def get_current_user(authorization: str | None = Header(None)) -> dict[str, Any]:
    """Dependency that extracts the current user from the JWT bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    token = authorization.removeprefix("Bearer ").strip()
    return decode_session_token(token)


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


@router.get("/me")
async def get_me(user: CurrentUser) -> dict[str, Any]:
    """Return the current authenticated user's profile and connected providers."""
    installation_id = user.get("sub")
    provider = user.get("provider", "unknown")

    # Try to fetch the VCS installation for additional metadata
    username = None
    connected_providers: list[str] = [provider]

    if installation_id:
        try:
            async with AsyncSessionLocal() as session:
                installation = await session.get(VCSInstallation, installation_id)
                if installation:
                    username = (installation.meta_data or {}).get("username")
                    # Find all installations for this tenant
                    result = await session.execute(
                        select(VCSInstallation.provider)
                        .where(VCSInstallation.tenant_id == installation.tenant_id)
                        .distinct()
                    )
                    connected_providers = [row[0] for row in result.all()]
        except Exception:
            logger.warning("Could not fetch VCS installation details", exc_info=True)

    return {
        "installation_id": installation_id,
        "provider": provider,
        "tenant_id": user.get("tenant_id"),
        "username": username or f"archon-{provider}-user",
        "connected_providers": connected_providers,
    }


@router.post("/validate")
async def validate_token(user: CurrentUser) -> dict[str, str]:
    """Lightweight endpoint to validate a session token."""
    return {"status": "valid", "provider": user.get("provider", "unknown")}


@router.post("/demo")
async def demo_login() -> dict[str, str]:
    """Create a demo session token for development purposes (no OAuth required)."""
    token = create_session_token(
        provider="demo",
        installation_id="demo-install-001",
        tenant_id="demo-tenant-001",
        extra={"username": "demo-engineer"},
    )
    return {"token": token, "provider": "demo"}
