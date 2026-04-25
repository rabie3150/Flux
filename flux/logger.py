"""Flux logging system.

Structured JSON logs for production, human-readable for development.
Redacts sensitive tokens automatically. File rotation prevents disk bloat.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flux.config import settings

# Patterns to redact from log output
_REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Telegram bot token: 123456:ABC-DEF... -> <redacted>
    (re.compile(r"(\d+:[A-Za-z0-9_-]{30,45})", re.IGNORECASE), "<telegram-token-redacted>"),
    # Generic bearer/token patterns
    (re.compile(r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<token-redacted>"),
    (re.compile(r'(bearer["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<token-redacted>"),
    # API keys
    (re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<key-redacted>"),
    # API secrets
    (re.compile(r'(api[_-]?secret["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<secret-redacted>"),
    # Client secrets
    (re.compile(r'(client[_-]?secret["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<secret-redacted>"),
    # Passwords
    (re.compile(r'(pass(word|wd)?["\']?\s*[:=]\s*["\']?)([^\s"\']{4,})', re.IGNORECASE), r"\1<password-redacted>"),
    # Authorization header
    (re.compile(r'(authorization["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{10,})', re.IGNORECASE), r"\1<auth-redacted>"),
    # Session / cookie
    (re.compile(r'(session["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<session-redacted>"),
    (re.compile(r'(cookie["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<cookie-redacted>"),
    # refresh_token / access_token
    (re.compile(r'(refresh[_-]?token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<token-redacted>"),
    (re.compile(r'(access[_-]?token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<token-redacted>"),
    # Private keys
    (re.compile(r'(private[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+/=.\-]{16,})', re.IGNORECASE), r"\1<key-redacted>"),
    # Master key / Fernet key
    (re.compile(r'(FLUX_MASTER_KEY["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_+=/\-]{20,})', re.IGNORECASE), r"\1<master-key-redacted>"),
]


def _redact(text: str) -> str:
    """Redact sensitive tokens from log strings."""
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_dict: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact(record.getMessage()),
        }
        if hasattr(record, "pipeline_id"):
            log_dict["pipeline_id"] = record.pipeline_id
        if hasattr(record, "worker_id"):
            log_dict["worker_id"] = record.worker_id
        if hasattr(record, "event_type"):
            log_dict["event_type"] = record.event_type
        if hasattr(record, "metadata") and record.metadata:
            try:
                redacted_metadata = json.loads(_redact(json.dumps(record.metadata, default=str)))
            except Exception as e:
                redacted_metadata = {"error": f"Failed to serialize metadata: {e}"}
            log_dict["metadata"] = redacted_metadata
        if record.exc_info:
            # Redact exception tracebacks too — they may contain tokens in locals
            tb_text = self.formatException(record.exc_info)
            log_dict["exception"] = _redact(tb_text)
        return json.dumps(log_dict, ensure_ascii=False)


class RedactingFormatter(logging.Formatter):
    """Plain-text formatter that redacts sensitive data."""

    def format(self, record: logging.LogRecord) -> str:
        # Format the entire string (including args and traceback) first
        formatted = super().format(record)
        # Redact any sensitive tokens from the final string
        return _redact(formatted)


def setup_logging() -> None:
    """Configure Flux logging with rotation and redaction.

    - Console: human-readable, development-friendly
    - File: JSON structured logs with rotation (5 MB x 5 backups)
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.flux_env == "development" else logging.INFO)

    # Remove any existing handlers (prevents duplicates on reload)
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Console handler — human-readable for dev
    console_handler = logging.StreamHandler(sys.stdout)
    console_fmt = RedactingFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    console_handler.setLevel(logging.DEBUG)
    root.addHandler(console_handler)

    # File handler — JSON structured, with rotation
    log_dir = Path(settings.storage_path) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "flux.log"

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(JsonFormatter())
        file_handler.setLevel(logging.INFO)
        root.addHandler(file_handler)
    except OSError as e:
        root.warning("[Flux] Could not create file log handler at %s: %s", log_file, e)

    # Reduce noise from third-party libraries
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.flux_env == "development" else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

    root.info("[Flux] Logging configured — console + rotating file (%s)", log_file)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger with Flux configuration applied."""
    return logging.getLogger(name)


def log_activity(
    level: str,
    event_type: str,
    message: str,
    pipeline_id: str | None = None,
    worker_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log an activity event to both logger and database.

    This is a convenience wrapper for structured activity logging.
    Database persistence happens via the activity_log service.
    """
    logger = get_logger("flux.activity")

    # Normalize level names
    level = level.lower()
    if level == "warn":
        level = "warning"

    extra: dict[str, Any] = {
        "event_type": event_type,
    }
    if pipeline_id:
        extra["pipeline_id"] = pipeline_id
    if worker_id:
        extra["worker_id"] = worker_id

    # Attach metadata to extra dict if provided
    if metadata:
        extra["metadata"] = metadata

    log_method = getattr(logger, level, logger.info)
    log_method(message, extra=extra)
