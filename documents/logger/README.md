# Logger Documentation

## What This System Does

Flux uses a dual-output logging system:

1. **Console** — Human-readable plain text for development
2. **File** — Structured JSON logs with rotation for production analysis

All logs automatically redact sensitive tokens (API keys, bot tokens, secrets) to prevent credential leakage in log files.

## Current Status

| Component | Status | Phase |
|-----------|--------|-------|
| JSON file formatter | ✅ Implemented | 1 |
| Redacting text formatter | ✅ Implemented | 1 |
| File rotation (5 MB x 5 backups) | ✅ Implemented | 1 |
| Auto-redaction patterns | ✅ Implemented | 1 |
| Activity log helper | ✅ Implemented | 1 |
| Third-party noise reduction | ✅ Implemented | 1 |
| Log streaming API | 🚧 Pending | 7 |

## Architecture

```
Log Event
    ├── Console Handler (StreamHandler)
    │       └── RedactingFormatter → plain text with redaction
    │
    └── File Handler (RotatingFileHandler)
            └── JsonFormatter → structured JSON
```

## Redaction Rules

| Pattern | Example Match | Redacted To |
|---------|--------------|-------------|
| Telegram bot token | `123456:ABC-DEF123...` | `<telegram-token-redacted>` |
| Generic token | `token=abc123...` | `token=<token-redacted>` |
| Bearer token | `bearer=abc123...` | `bearer=<token-redacted>` |
| API key | `api_key=abc123...` | `api_key=<key-redacted>` |
| Client secret | `client_secret=abc123...` | `client_secret=<secret-redacted>` |
| Master key | `FLUX_MASTER_KEY=abc...` | `FLUX_MASTER_KEY=<master-key-redacted>` |

## File Rotation

| Setting | Value |
|---------|-------|
| Max file size | 5 MB |
| Backup count | 5 |
| Location | `{STORAGE_PATH}/logs/flux.log` |
| Format | JSON lines (one JSON object per line) |

Example rotated files:
```
/storage/emulated/0/Flux/logs/
├── flux.log          ← current
├── flux.log.1        ← most recent backup
├── flux.log.2
├── flux.log.3
├── flux.log.4
└── flux.log.5        ← oldest backup
```

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
