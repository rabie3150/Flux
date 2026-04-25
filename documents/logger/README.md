# Logger Documentation

## What This System Does

Flux uses a dual-output logging system:

1. **Console** — Human-readable plain text for development
2. **File** — Structured JSON logs with rotation for production analysis

All logs automatically redact sensitive tokens (API keys, bot tokens, secrets, passwords, session cookies) to prevent credential leakage in log files. Exception tracebacks are also redacted before writing.

## Current Status

| Component | Status | Phase |
|-----------|--------|-------|
| JSON file formatter | ✅ Implemented | 1 |
| Redacting text formatter | ✅ Implemented | 1 |
| File rotation (5 MB x 5 backups) | ✅ Implemented | 1 |
| Auto-redaction patterns (14 patterns) | ✅ Implemented | 1 |
| Traceback redaction | ✅ Implemented | 1 |
| Metadata redaction in structured logs | ✅ Implemented | 1 |
| Activity log helper | ✅ Implemented | 1 |
| Third-party noise reduction | ✅ Implemented | 1 |
| Logging coverage (API + services) | ✅ Implemented | 1 |
| Log streaming API | 🚧 Pending | 7 |
| Log level override from settings | 🚧 Pending | 3 |

## Architecture

```
Log Event
    ├── Console Handler (StreamHandler)
    │       └── RedactingFormatter → plain text with redaction
    │
    └── File Handler (RotatingFileHandler)
            └── JsonFormatter → structured JSON
                ├── message (redacted)
                ├── exception traceback (redacted)
                └── metadata dict (redacted)
```

## Redaction Rules

| Pattern | Example Match | Redacted To |
|---------|--------------|-------------|
| Telegram bot token | `123456:ABC-DEF123...` | `<telegram-token-redacted>` |
| Generic token | `token=abc123...` | `token=<token-redacted>` |
| Bearer token | `bearer=abc123...` | `bearer=<token-redacted>` |
| API key | `api_key=abc123...` | `api_key=<key-redacted>` |
| API secret | `api_secret=abc123...` | `api_secret=<secret-redacted>` |
| Client secret | `client_secret=abc123...` | `client_secret=<secret-redacted>` |
| Password | `password=secret123` | `password=<password-redacted>` |
| Authorization header | `authorization=Bearer...` | `authorization=<auth-redacted>` |
| Session | `session=abc123...` | `session=<session-redacted>` |
| Cookie | `cookie=abc123...` | `cookie=<cookie-redacted>` |
| Refresh token | `refresh_token=abc...` | `refresh_token=<token-redacted>` |
| Access token | `access_token=abc...` | `access_token=<token-redacted>` |
| Private key | `private_key=abc...` | `private_key=<key-redacted>` |
| Master key | `FLUX_MASTER_KEY=abc...` | `FLUX_MASTER_KEY=<master-key-redacted>` |

Token patterns include base64 characters (`+/=.`) so JWTs and Fernet tokens are caught.

## File Rotation

| Setting | Value |
|---------|-------|
| Max file size | 5 MB |
| Backup count | 5 |
| Location | `{STORAGE_PATH}/logs/flux.log` |
| Format | JSON lines (one JSON object per line) |

If the log directory is unwritable, the file handler is skipped with a warning — the app continues with console logging only.

## JSON Log Schema

```json
{
  "timestamp": "2026-04-25T19:52:00+00:00",
  "level": "INFO",
  "logger": "flux.core.pipeline",
  "message": "Pipeline created: Test Pipeline",
  "pipeline_id": "abc123...",
  "worker_id": null,
  "event_type": "pipeline_created",
  "metadata": {"duration_sec": 45.2},
  "exception": null
}
```

## Usage

```python
from flux.logger import get_logger, log_activity

# Standard logging
logger = get_logger(__name__)
logger.info("Processing pipeline %s", pipeline_id)
logger.warning("Storage at 85%% capacity")

# Structured activity logging
log_activity(
    level="info",
    event_type="render_completed",
    message="Video rendered successfully",
    pipeline_id="abc123",
    metadata={"duration_sec": 45.2},
)
```

## Logging Audit Script

Run the dedicated logging audit to check coverage:

```bash
python .agents/skills/flux-review/scripts/audit_logging.py
```

Checks for:
- `print()` in production code
- Bare `except:` without logging
- Files missing `get_logger` import
- HTTPException paths without preceding logger calls
- Direct `logging.*` calls (should use logger instance)

## Log Levels by Environment

| Source | Development | Production |
|--------|-------------|------------|
| Flux app code | DEBUG | INFO |
| APScheduler | WARNING | WARNING |
| SQLAlchemy engine | DEBUG | WARNING |
| httpx | WARNING | WARNING |
| telegram | WARNING | WARNING |

## Conception References

- Monitoring strategy: `conception_archive/13-monitoring-observability-and-alerting.md`
