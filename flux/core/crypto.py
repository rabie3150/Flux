"""Encryption utilities for secure credential storage.

Uses Fernet symmetric encryption. The master key is read from
FLUX_MASTER_KEY environment variable on each operation (lazy init),
so key changes take effect without module reload.

In development, if no master key is provided, a deterministic ephemeral
key is generated from the project path hash so it survives restarts.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)


def _get_ephemeral_key() -> bytes:
    """Generate a deterministic ephemeral key for development.

    Uses a hash of the project root path so the key is consistent
    across process restarts in the same checkout.
    """
    from pathlib import Path

    project_root = str(Path(__file__).resolve().parents[2])
    key_bytes = hashlib.sha256(project_root.encode()).digest()
    # Fernet keys must be 32 bytes, base64url-encoded (44 chars)
    import base64

    return base64.urlsafe_b64encode(key_bytes[:32])


def _get_cipher() -> Fernet:
    """Lazy-initialize and return the Fernet cipher.

    Re-reads settings on every call so key changes take effect
    without restarting the Python process.
    """
    master_key = settings.flux_master_key

    if master_key:
        try:
            return Fernet(master_key.encode("utf-8"))
        except (ValueError, TypeError) as e:
            if settings.is_production:
                raise RuntimeError(f"Invalid FLUX_MASTER_KEY in production: {e}")
            logger.warning("Invalid FLUX_MASTER_KEY. Using ephemeral key: %s", e)
            return Fernet(_get_ephemeral_key())

    # No master key configured
    if settings.is_production:
        raise RuntimeError("FLUX_MASTER_KEY is required when running in production.")

    logger.warning("No FLUX_MASTER_KEY provided in development. Using an ephemeral key.")
    return Fernet(_get_ephemeral_key())


def encrypt_dict(data: dict[str, Any]) -> str:
    """Encrypt a dictionary into a Fernet token string."""
    cipher = _get_cipher()
    json_bytes = json.dumps(data).encode("utf-8")
    return cipher.encrypt(json_bytes).decode("utf-8")


def decrypt_dict(token: str) -> dict[str, Any]:
    """Decrypt a Fernet token string back to a dictionary."""
    if not token or token == "{}":
        return {}
    cipher = _get_cipher()
    try:
        json_bytes = cipher.decrypt(token.encode("utf-8"))
        return json.loads(json_bytes.decode("utf-8"))
    except InvalidToken:
        logger.error("Failed to decrypt credentials. Invalid token or master key mismatch.")
        raise ValueError("Invalid encryption token or master key mismatch.")
