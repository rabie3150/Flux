# Flux — Agent Onboarding Guide

> **Target reader:** AI coding agents with no prior context about this project.  
> **Last updated:** 2026-05-31  
> **Maintainer rule:** When you change behavior, update this file and the relevant doc in `documents/`.

---

## 1. Project Overview

**Flux** is a content automation engine designed to run headless on Android (Termux) and locally on Windows/Linux. It fetches raw media ("ingredients"), renders them into finished videos/images ("produced content"), and publishes them to social platforms (YouTube, Instagram, TikTok, X) on a schedule.

The core philosophy is **generic engine + specific plugins**:

- The engine (`flux/core/`, `flux/api/`) knows only about pipelines, ingredients, renders, and posts.
- Plugins (`flux/plugins/`) provide content-specific logic (Quran shorts, language-learning shorts, etc.).
- Platform publishers (`flux/platforms/`) encapsulate the upload logic for each social network.

This means **adding a new content type never requires a database migration** — plugin data lives in JSON columns.

---

## 2. Technology Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.11+ |
| Web framework | FastAPI 0.110+ |
| Server | Uvicorn (standard) |
| Database | SQLite via SQLAlchemy 2.0 (async, `aiosqlite`) |
| Migrations | Lightweight column migrations in `flux/db.py` (no Alembic yet) |
| Scheduler | APScheduler 3.10+ (asyncio, SQLite job store) |
| Validation & settings | Pydantic v2 + `pydantic-settings` |
| HTTP client | `httpx` |
| Media processing | Pillow, FFmpeg (subprocess) |
| Notifications | `python-telegram-bot` |
| Templating | Jinja2 |
| Platform APIs | Google API Client (YouTube), `instagrapi` (Instagram) |
| Security | `cryptography` (Fernet) |
| Testing | `pytest` + `pytest-asyncio` + `httpx` |
| Linting | `ruff` |

---

## 3. Project Structure

```
flux/                          # Main application package
├── main.py                    # FastAPI entrypoint, lifespan, CORS, static files
├── config.py                  # Pydantic Settings (.env loader)
├── db.py                      # Async SQLAlchemy engine, session, Base, init_db
├── models.py                  # All ORM models (generic tables, JSON columns)
├── scheduler.py               # APScheduler init/shutdown
├── logger.py                  # Structured logging with redaction + ActivityLog persistence
├── api/                       # FastAPI routers (one per domain)
│   ├── system.py              # Health, dashboard, settings, activity log, plugins, remote
│   ├── pipelines.py           # Pipeline CRUD + trigger fetch/render
│   ├── production.py          # Produced content lifecycle
│   ├── ingredients.py         # Ingredient approval/rejection/stock levels
│   ├── workers.py             # Platform worker CRUD
│   ├── posts.py               # Post records, retry, dedup
│   └── metrics.py             # Prometheus-style metrics endpoint
├── core/                      # Business logic (engine layer)
│   ├── pipeline.py            # Pipeline service (CRUD, fetch, render, identify)
│   ├── ingredients.py         # Ingredient service + stock levels
│   ├── production.py          # ProducedContent state machine
│   ├── publish.py             # Publishing orchestrator
│   ├── workers.py             # Worker management
│   ├── scheduler_jobs.py      # APScheduler job registration
│   ├── storage.py             # Storage budget tracking
│   ├── lock.py                # Global render lock (file-based)
│   ├── notifications.py       # Telegram alerting
│   ├── crypto.py              # Credential encryption/decryption
│   └── hardening.py           # DB backup, thermal guard, rich health check
├── platforms/                 # Social media publishers
│   ├── base.py                # PlatformPublisher ABC
│   ├── publisher.py           # Publisher factory / dispatcher
│   ├── youtube.py             # YouTube Data API v3 upload
│   ├── instagram.py           # Instagrapi upload
│   ├── tiktok.py              # TikTok publisher stub
│   └── x.py                   # X/Twitter publisher stub
├── plugins/                   # Content plugins
│   ├── base.py                # ContentPlugin ABC + RenderResult dataclass
│   ├── loader.py              # Dynamic plugin discovery + DB sync
│   ├── quran/                 # Quran shorts plugin (full implementation)
│   │   ├── plugin.py          # ContentPlugin implementation
│   │   ├── fetch.py           # YouTube clip fetching
│   │   ├── render.py          # FFmpeg composition
│   │   ├── identify.py        # Whisper-based verse identification
│   │   ├── ai.py              # Gemini API for captions / Tafseer
│   │   └── ...
│   └── language_shorts/       # Language-learning shorts plugin
│       ├── plugin.py
│       ├── generate.py
│       ├── render.py
│       └── ...
├── services/                  # Shared service utilities
│   ├── backgrounds.py         # Background image/video fetching (Pexels/Unsplash)
│   └── render_utils.py        # FFmpeg helper utilities
├── tts/                       # Text-to-speech providers
│   ├── base.py
│   ├── edge_tts.py
│   └── inworld.py
└── static/admin/              # Built admin panel (static HTML/JS)

tests/
├── conftest.py                # Shared fixtures: event_loop, setup_db, db_session, client
├── integration/               # API endpoint + plugin integration tests
├── plugins/                   # Plugin-specific unit tests
└── unit/                      # Core unit tests (lock, storage, health, captions, regex)

documents/                     # Living documentation (read before touching code)
├── backend/
├── database/
├── devops/
├── error-handler/
├── frontend/
├── logger/
├── platforms/
├── plugins/
└── scheduler/

scripts/
├── start.sh                   # Termux production startup (wake lock, auto-restart)
├── bootstrap.sh               # Termux environment bootstrap
├── harden_ssh.sh              # SSH hardening for Termux
├── setup_cloudflare_tunnel.sh # Cloudflare tunnel for remote access
├── setup_youtube_worker.py    # YouTube OAuth flow helper
├── youtube_auth.py            # Standalone YouTube auth script
└── debug_tools.py             # Runtime diagnostic utilities

secrets/                       # OAuth credentials (gitignored)
```

---

## 4. Build and Run Commands

### 4.1 Environment setup

```bash
# Create venv (Python 3.11+)
python -m venv .venv
source .venv/bin/activate  # Linux/mac/Termux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt          # runtime
pip install -r requirements-dev.txt      # dev + test
# OR: pip install -e ".[dev]"
```

### 4.2 Configuration

Copy `.env.example` to `.env` and fill values. Key variables:

| Variable | Purpose |
|----------|---------|
| `FLUX_ENV` | `development` or `production` |
| `FLUX_MASTER_KEY` | Fernet key (required in production) |
| `DATABASE_URL` | SQLite path, e.g. `sqlite:///~/flux/app.db` |
| `STORAGE_PATH` | Media storage root (default: `/storage/emulated/0/Flux` for Termux) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Alert notifications |
| `GEMINI_API_KEYS` | JSON list of API keys for AI features |
| `YOUTUBE_CLIENT_SECRETS_PATH` | OAuth client secrets JSON |

### 4.3 Run the server

```bash
# Development (auto-reload)
python -m flux.main
# OR:
uvicorn flux.main:app --host 127.0.0.1 --port 8000 --reload

# Production (Termux)
bash scripts/start.sh
```

### 4.4 Linting

```bash
ruff check .          # lint
ruff check --fix .    # auto-fix
ruff format .         # format
```

---

## 5. Testing Instructions

### 5.1 Run tests

```bash
pytest                          # all tests
pytest tests/unit               # unit tests only
pytest tests/integration        # integration tests only
pytest tests/plugins            # plugin tests only
pytest -v                       # verbose
pytest --tb=short               # shorter tracebacks
```

### 5.2 Test architecture

- **Database:** Each test gets a fresh in-memory SQLite (`sqlite+aiosqlite:///:memory:`) via the `setup_db` fixture (autouse, per-test).
- **HTTP client:** The `client` fixture provides an `httpx.AsyncClient` wired to the FastAPI app with the test DB override.
- **Event loop:** Session-scoped event loop fixture for asyncio consistency.
- **Async fixtures:** Use `@pytest.mark.anyio` or rely on `asyncio_mode = "auto"` (configured in `pyproject.toml`).

### 5.3 Writing new tests

- Place API tests in `tests/integration/`.
- Place pure-logic tests in `tests/unit/`.
- Place plugin tests under `tests/plugins/<plugin_name>/`.
- Use the `db_session` fixture for direct DB access.
- Use the `client` fixture for endpoint tests.
- Import models inside fixtures/tests to ensure tables are registered.

---

## 6. Code Style Guidelines

### 6.1 Ruff configuration (`pyproject.toml`)

- Line length: **100**
- Target Python: **3.11**

### 6.2 Conventions used throughout

1. **`from __future__ import annotations`** at the top of every file.
2. **Type hints everywhere.** Use `str | None` (PEP 604), `dict[str, Any]`, etc.
3. **Docstrings** for modules, classes, and public functions.
4. **Async by default** for I/O-bound code (DB, HTTP, FFmpeg subprocess).
5. **JSON columns for extensibility.** Plugin-specific data goes in `*_json` Text columns; never add plugin-specific columns to core tables.
6. **Path handling.** Use `pathlib.Path`. Expand `~` in validators (`config.py`). Use forward slashes in SQLite URLs.
7. **Logging.** Always use `flux.logger.get_logger(__name__)`. Never `print()`. Use `log_activity()` for auditable events.
8. **Error handling.** Catch at layer boundaries, log with context, and propagate user-friendly messages via HTTPException where appropriate.

---

## 7. Security Considerations

### 7.1 Secrets management

- **Never commit `.env`** or files in `secrets/`.
- Credentials stored in `platform_workers.credentials_json` are encrypted at rest with `FLUX_MASTER_KEY` (Fernet).
- The master key is required in production; startup will fail if missing.

### 7.2 Log redaction

`flux/logger.py` automatically redacts sensitive tokens from all log output:

- Telegram tokens, Bearer tokens, API keys, client secrets
- Passwords, session IDs, CSRF tokens, JWTs
- YouTube OAuth tokens (`ya29.*`), Google API keys (`AIza...`)
- Instagrapi session cookies

### 7.3 CORS

Only `http://localhost:8000` is allowed. No external origins.

### 7.4 Remote access

The `/api/system/remote` endpoint accepts commands from GitHub Actions. It expects an `Authorization: Bearer <FLUX_REMOTE_KEY>` header. The key is random and set via `.env`.

### 7.5 SSH hardening

`scripts/harden_ssh.sh` disables password auth and enforces key-based login on Termux.

---

## 8. Plugin System

### 8.1 How to add a plugin

1. Create a package under `flux/plugins/<plugin_name>/`.
2. Implement `ContentPlugin` (from `flux.plugins.base`) in `plugin.py`.
3. The loader scans `flux.plugins.*` at startup and auto-registers any `ContentPlugin` subclass.
4. The plugin is synced to the `plugins` DB table automatically.

### 8.2 ContentPlugin interface

Required abstract methods:

- `name` / `display_name` / `version` — metadata
- `ingredient_types` — list of ingredient type strings
- `fetch(pipeline_id, config, known_items)` → list of ingredient dicts
- `render(pipeline_id, ingredient_ids, config)` → `RenderResult`
- `identify_content(pipeline_id, produced_content_id, config)` → identification dict
- `build_caption(pipeline_id, produced_content_id, config, worker_config)` → caption string
- `get_config_schema()` → JSONSchema dict for the admin UI

### 8.3 Existing plugins

| Plugin | Location | Description |
|--------|----------|-------------|
| `quran` | `flux/plugins/quran/` | Fetches Quran recitation clips, renders subtitled videos with AI-generated captions/Tafseer, identifies verses via Whisper |
| `language_shorts` | `flux/plugins/language_shorts/` | Generates vocabulary-learning short videos |

---

## 9. Platform Publishing

### 9.1 How to add a platform

1. Subclass `PlatformPublisher` in `flux/platforms/<platform>.py`.
2. Implement `publish(file_path, caption, thumbnail_path)` → `PublishResult`.
3. Register in `flux/platforms/publisher.py` dispatcher.

### 9.2 Existing platforms

| Platform | Strategy | Status |
|----------|----------|--------|
| YouTube | Official Data API v3 | Full |
| Instagram | `instagrapi` (unofficial) | Full |
| TikTok | Stub | Planned |
| X | Stub | Planned |

---

## 10. Deployment & Operations

### 10.1 Target environment

Primary target is **Termux on Android** (headless phone-as-server). Secondary development on Windows.

### 10.2 Termux startup

`scripts/start.sh`:
- Activates venv
- Acquires wake lock (`termux-wake-lock`)
- Ensures storage paths exist
- Enables SQLite WAL mode
- Runs Uvicorn with auto-restart on crash

### 10.3 GitHub Actions

- `.github/workflows/watchdog.yml` — Every 30 min, hits `/api/health`. Sends Telegram alert on failure.
- `.github/workflows/remote-command.yml` — Manual dispatch to send commands (`status`, `restart`, `trigger_fetch`, `trigger_post`) to `/api/system/remote`.

Requires repository secrets: `FLUX_HEALTH_URL`, `FLUX_REMOTE_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

### 10.4 Health checks

- `/api/health` — Rich subsystem check (DB, scheduler, storage, thermal, workers).
- Thermal guard blocks renders above 65°C (Android/Linux via sysfs).
- Storage budget warning at 80%, critical at 95%.

### 10.5 Backups & retention

- Daily SQLite backups with 7-day rotation (`flux/core/hardening.py`).
- Data retention cleanup: rejected ingredients > 7 days, activity logs > 30 days, old render logs > 7 days.

---

## 11. Key Files to Know

| File | Why it matters |
|------|----------------|
| `flux/main.py` | App lifespan, startup sequence, router mounting |
| `flux/config.py` | All settings; add new env vars here |
| `flux/db.py` | Engine, session, `init_db()`, lightweight migrations |
| `flux/models.py` | All tables; keep generic — no plugin-specific columns |
| `flux/logger.py` | Structured logs + redaction + activity persistence |
| `flux/scheduler.py` | APScheduler singleton |
| `flux/core/pipeline.py` | Fetch → Render → Identify orchestration |
| `flux/core/hardening.py` | Backup, thermal, health |
| `flux/plugins/base.py` | Plugin contract |
| `flux/platforms/base.py` | Publisher contract |
| `tests/conftest.py` | Test fixtures |

---

## 12. Common Pitfalls

1. **Windows event loop:** `flux/main.py` forces `ProactorEventLoop` on Windows before any async code runs. Do not override this.
2. **SQLite URL conversion:** `flux/db.py` swaps `sqlite:///` → `sqlite+aiosqlite:///` for the engine, but APScheduler uses the sync URL. Be careful when adding new DB tools.
3. **Render lock:** Only one render runs globally at a time (`flux/core/lock.py`). Timeouts are configurable; scheduled jobs may pass `timeout=0` to skip if busy.
4. **Plugin DB sync:** The `plugins` table is the source of truth for pipeline creation, but the registry is in-memory. If a plugin fails to load, pipelines referencing it will error at fetch/render time.
5. **Credential encryption:** `credentials_json` is encrypted at rest. The encryption helper is in `flux/core/crypto.py`. Always decrypt before passing to platform publishers.

---

## 13. Documentation Index

Living docs are in `documents/`:

- `documents/backend/api.md` — API design notes
- `documents/plugins/plugin-interface.md` — Plugin authoring guide
- `documents/platforms/youtube.md` — YouTube platform notes
- `documents/database/` — Schema rationale and query patterns
- `documents/devops/` — Bootstrap, security, monitoring
- `documents/conception_archive/` — Frozen design history (read-only)

**Rule:** If your change affects behavior, update the relevant doc file before finishing.
