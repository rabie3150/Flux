# Logger Documentation

## Overview

Flux uses a highly robust, dual-output logging system designed for both developer experience and production observability. It ensures complete security through deep redaction while providing structured JSON logs for external analysis. 

1. **Console** — Human-readable plain text for development, fully redacted.
2. **File** — Structured JSON logs with rotation for production analysis, with structured metadata and redacted exception tracebacks.

All logs automatically redact sensitive tokens (API keys, bot tokens, secrets, cookies, passwords) to prevent credential leakage in log files. It recursively redacts structured metadata objects to ensure deep security.

## Files

| File | Purpose |
|------|---------|
| `flux/logger.py` | Main logging system implementation, formatters, and helpers |
| `.agents/skills/flux-review/scripts/audit_logging.py` | Automated audit script to ensure codebase-wide logging compliance |

## Current Status

| Component | Status | Phase |
|-----------|--------|-------|
| JSON file formatter | ✅ Implemented | 1 |
| Redacting text formatter | ✅ Implemented | 1 |
| File rotation (5 MB x 5 backups) | ✅ Implemented | 1 |
| Auto-redaction patterns | ✅ Implemented | 1 |
| Deep metadata redaction | ✅ Implemented | 1 |
| Traceback redaction | ✅ Implemented | 1 |
| Activity log helper | ✅ Implemented | 1 |
| Third-party noise reduction | ✅ Implemented | 1 |
| Log streaming API | 🚧 Pending | 7 |

## Architecture

```
Log Event
    ├── Console Handler (StreamHandler)
    │       └── RedactingFormatter → formats string entirely, then applies deep redaction
    │
    └── File Handler (RotatingFileHandler)
            └── JsonFormatter → extracts structured metadata, redacts strings, outputs JSON
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
| Password | `password=abc123...` | `password=<password-redacted>` |
| Authorization | `authorization: Bearer...` | `authorization:<auth-redacted>` |
| Session/Cookie | `session=abc123...` | `session=<session-redacted>` |
| Access/Refresh Tokens | `access_token=abc123...` | `access_token=<token-redacted>` |
| Private key | `private_key=abc123...` | `private_key=<key-redacted>` |
| Master key | `FLUX_MASTER_KEY=abc...` | `FLUX_MASTER_KEY=<master-key-redacted>` |

## File Rotation

| Setting | Value |
|---------|-------|
| Max file size | 5 MB |
| Backup count | 5 |
| Location | `{STORAGE_PATH}/logs/flux.log` |
| Format | JSON lines (one JSON object per line) |

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
  "metadata": {
    "duration_sec": 45.2,
    "user_ip": "127.0.0.1"
  },
  "exception": null
}
```

## Common Tasks

### How to use standard logging
```python
from flux.logger import get_logger

logger = get_logger(__name__)

# Basic logging (arguments are natively supported and redacted)
logger.info("Processing pipeline %s", pipeline_id)

# Error logging (tracebacks are automatically redacted!)
try:
    1 / 0
except Exception as e:
    logger.exception("A critical failure occurred")
```

### How to log structured activities
```python
from flux.logger import log_activity

# Structured activity logging
# Metadata is securely redacted and injected as a JSON object, not a string
log_activity(
    level="info",
    event_type="render_completed",
    message="Video rendered successfully",
    pipeline_id="abc123",
    metadata={"duration_sec": 45.2, "status": "success"},
)
```

## Log Levels by Environment

| Source | Development | Production |
|--------|-------------|------------|
| Flux app code | DEBUG | INFO |
| APScheduler | WARNING | WARNING |
| SQLAlchemy engine | DEBUG | WARNING |
| httpx | WARNING | WARNING |
| telegram | WARNING | WARNING |

## Conception References

- Monitoring strategy: `documents/conception_archive/13-monitoring-observability-and-alerting.md`
