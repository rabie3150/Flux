# Backend Documentation

## What This System Does

The backend is the FastAPI application that serves as the core engine for Flux. It handles HTTP requests, manages the plugin system, coordinates the scheduler, and serves the admin panel.

## Current Status

| Component | Status | Phase |
|-----------|--------|-------|
| FastAPI app + lifespan | ✅ Implemented | 0 |
| Configuration (`config.py`) | ✅ Implemented | 0 |
| Health endpoint (`/api/health`) | ✅ Implemented | 0 |
| Database engine (`db.py`) | ✅ Implemented | 0 |
| CORS middleware | ✅ Implemented | 0 |
| API routers (system, pipelines, ingredients, workers) | ✅ Implemented | 1 |
| Plugin base interface (`ContentPlugin`) | ✅ Implemented | 1 |
| Pipeline service + CRUD API | ✅ Implemented | 1 |
| Ingredient service + API | ✅ Implemented | 1 |
| Platform worker CRUD API | ✅ Implemented | 1 |
| File-based render lock | ✅ Implemented | 1 |
| APScheduler setup | ✅ Implemented | 1 |
| Logging system | ✅ Implemented | 1 |
| Static files (admin panel) | ✅ Implemented | 1 (minimal HTML) |
| Plugin loader + registry | ✅ Implemented | 2 |
| Scheduler jobs (fetch, render, publish) | 🏗️ In Progress | 2–5 |
| Platform worker implementations | 🏗️ In Progress | 5 |

## Project Structure

```
flux/
├── __init__.py
├── main.py              # FastAPI entrypoint, lifespan, health endpoint
├── config.py            # Pydantic Settings, .env loading, secret management
├── db.py                # Async SQLAlchemy engine, session factory, WAL mode
├── api/                 # API route modules (Phase 1)
│   ├── __init__.py
│   ├── system.py        # Health, settings, activity log
│   ├── pipelines.py     # Pipeline CRUD
│   ├── ingredients.py   # Ingredient approve/reject/list
│   ├── production.py    # Render queue
│   ├── workers.py       # Platform worker CRUD
│   └── posts.py         # Post history
├── core/                # Core engine services (Phase 1)
│   ├── __init__.py
│   ├── pipeline.py      # Pipeline orchestrator
│   ├── ingredients.py   # Ingredient service
│   ├── production.py    # Render queue service
│   ├── lock.py          # File-based render lock
│   ├── storage.py       # Storage budget tracker
│   └── workers.py       # Worker manager
├── scheduler.py         # APScheduler setup (Phase 1)
├── notifications.py     # Telegram bot (Phase 2)
├── platforms/           # Platform worker implementations (Phase 5)
│   ├── __init__.py
│   ├── base.py
│   ├── youtube.py
│   ├── telegram.py
│   ├── instagram.py
│   ├── tiktok.py
│   └── x.py
├── plugins/             # Plugin system (Phase 0–2)
│   ├── __init__.py
│   ├── base.py          # ContentPlugin ABC
│   └── quran/           # Quran reference plugin
│       ├── __init__.py
│       ├── plugin.py
│       ├── fetch.py
│       ├── render.py
│       ├── identify.py
│       └── caption.py
└── static/admin/        # Admin panel HTML (Phase 6)
```

## Key Concepts

### Application Lifespan

`main.py` uses FastAPI's `lifespan` context manager for startup/shutdown events:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[Flux] Starting...")
    yield
    logger.info("[Flux] Shutting down")
```

This is where scheduler initialization and plugin loading will happen in Phase 1.

### Configuration

All secrets and settings live in `.env` (never committed). `config.py` uses Pydantic Settings with field validators:

- `FLUX_ENV` — `development` or `production`
- `FLUX_MASTER_KEY` — Fernet key for encrypting worker credentials
- `DATABASE_URL` — SQLite path (converted to `aiosqlite` in `db.py`)
- `STORAGE_PATH` — Media storage root (Android: `/storage/emulated/0/Flux`)
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — Notification channel
- `FLUX_REMOTE_KEY` — Bearer token for GitHub Actions remote commands

Paths are automatically expanded via `~` → home directory.

### Database Engine

`db.py` provides:
- `engine` — async SQLAlchemy engine with `aiosqlite`
- `AsyncSessionLocal` — session factory for dependency injection
- `Base` — declarative base for all models
- `get_db()` — FastAPI dependency yielding sessions
- WAL mode + foreign keys enabled on every connection via SQLAlchemy event listener

### CORS

Restricted to `http://localhost:8000` only. The admin panel is served from the same origin; no external origins are allowed.

## Development Environment

Develop on **Windows directly** for Phases 0–4. The phone is for validation only.

| Phase | Windows Dev? | Phone Needed? |
|-------|-------------|---------------|
| 0 Foundation | ✅ Yes | ❌ No |
| 1 Core Engine | ✅ Yes | ❌ No |
| 2 Fetch (APIs) | ✅ Yes | ❌ No |
| 3 Render (FFmpeg) | ✅ Yes | ⚠️ Final ARM test |
| 4 Distribute (APIs) | ✅ Yes | ⚠️ Final platform test |
| 5 Scheduler | ✅ Yes | ⚠️ Doze test only |
| 6 Integration | ⚠️ Simulate | ✅ Yes |
| 7 Hardening | ⚠️ Simulate | ✅ Yes (48h soak) |

See `conception_archive/16-build-plan.md` for full build plan.

## How to Run

```bash
# Development (Windows)
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn flux.main:app --reload --host 127.0.0.1 --port 8000

# Production (Termux)
./scripts/bootstrap.sh
./scripts/start.sh
```

## Testing

```bash
pytest tests/unit/        # Fast, no I/O
pytest tests/integration/ # DB + API client (Phase 1+)
pytest -m device          # Termux-only (Phase 3+)
```

## Conception References

- Plugin interface: `conception_archive/06-functional-specification-document.md` (Section 1)
- API design: `conception_archive/06-functional-specification-document.md` (Section 3)
- Architecture: `conception_archive/08-system-architecture-document.md`
