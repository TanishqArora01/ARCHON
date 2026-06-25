from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken

from src.core.config import settings


class SecretManager:
    def __init__(self, key: str | None = None):
        raw_key = key or settings.SECRET_ENCRYPTION_KEY
        self._fernet = Fernet(raw_key.encode("utf-8")) if raw_key else None

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        if not self._fernet:
            raise ValueError("SECRET_ENCRYPTION_KEY is required to encrypt secrets")
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        if not self._fernet:
            raise ValueError("SECRET_ENCRYPTION_KEY is required to decrypt secrets")
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise ValueError("Secret decryption failed") from exc


def normalize_fernet_key(value: str) -> str:
    try:
        Fernet(value.encode("utf-8"))
        return value
    except ValueError:
        return base64.urlsafe_b64encode(value.encode("utf-8").ljust(32, b"0")[:32]).decode("utf-8")
