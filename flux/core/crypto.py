"""Encryption utilities for secure credential storage."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)

# Initialize cipher
_cipher: Fernet | None = None

try:
    if settings.flux_master_key:
        _cipher = Fernet(settings.flux_master_key.encode("utf-8"))
    else:
        if settings.is_production:
            raise RuntimeError("FLUX_MASTER_KEY is empty in production.")
        # In development, generate an ephemeral key if missing
        logger.warning("No FLUX_MASTER_KEY provided in development. Using an ephemeral key.")
        _cipher = Fernet(Fernet.generate_key())
except (ValueError, TypeError) as e:
    if settings.is_production:
        raise RuntimeError(f"Invalid FLUX_MASTER_KEY in production: {e}")
    logger.warning("Invalid FLUX_MASTER_KEY. Using an ephemeral key for development.")
    _cipher = Fernet(Fernet.generate_key())


def encrypt_dict(data: dict[str, Any]) -> str:
    """Encrypt a dictionary into a Fernet token string."""
    if _cipher is None:
        raise RuntimeError("Cipher is not initialized")
    json_bytes = json.dumps(data).encode("utf-8")
    return _cipher.encrypt(json_bytes).decode("utf-8")


def decrypt_dict(token: str) -> dict[str, Any]:
    """Decrypt a Fernet token string back to a dictionary."""
    if not token or token == "{}":
        return {}
    if _cipher is None:
        raise RuntimeError("Cipher is not initialized")
    try:
        json_bytes = _cipher.decrypt(token.encode("utf-8"))
        return json.loads(json_bytes.decode("utf-8"))
    except InvalidToken:
        logger.error("Failed to decrypt credentials. Invalid token or master key mismatch.")
        raise ValueError("Invalid encryption token or master key mismatch.")
