# DevOps Documentation

## What This System Does

DevOps covers deployment, infrastructure, security, monitoring, and the operational lifecycle of Flux on an Android phone running Termux. The goal is a self-healing system that can run 24/7 with minimal operator intervention.

## Current Status

| Component | Status | Phase |
|-----------|--------|-------|
| `bootstrap.sh` — one-command install | ✅ Implemented | 0 |
| `start.sh` — auto-restart daemon | ✅ Implemented | 0 |
| `.env.example` — configuration template | ✅ Implemented | 0 |
| `pyproject.toml` — project metadata + tool config | ✅ Implemented | 0 |
| SQLite WAL mode | ✅ Implemented | 0 |
| Logging system (file rotation, redaction) | ✅ Implemented | 1 |
| GitHub Actions watchdog | 🚧 Pending | 7 |
| Cloudflare Tunnel | 🚧 Pending | 7 |
| Tailscale SSH | 🚧 Pending | 7 |
| Backup cron | 🚧 Pending | 7 |
| Thermal guard | 🚧 Pending | 7 |

## Bootstrap Script (`scripts/bootstrap.sh`)

One-command setup for a clean Termux installation:

```bash
pkg update && pkg upgrade -y
pkg install -y python ffmpeg git openssh yt-dlp clang make libjpeg-turbo libpng termux-api termux-boot
termux-setup-storage
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sqlite3 app.db "PRAGMA journal_mode=WAL;"
```

**Packages explained:**
- `python` — runtime
- `ffmpeg` — video rendering
- `git` — version control
- `openssh` — remote access
- `yt-dlp` — YouTube downloads
- `clang`, `make` — compiling Python packages with C extensions
- `libjpeg-turbo`, `libpng` — image processing
- `termux-api`, `termux-boot` — Android integration

## Start Script (`scripts/start.sh`)

Production startup with auto-restart loop:

```bash
termux-wake-lock
while true; do
    uvicorn flux.main:app --host 127.0.0.1 --port 8000
    sleep 10
done
```

- Binds to **localhost only** (`127.0.0.1`) — no LAN exposure
- `termux-wake-lock` prevents Android from killing the process
- Auto-restarts on crash with 10-second delay

## Development Environment

### Windows (Primary Development)

Develop directly on Windows for Phases 0–4. Python, SQLite, and FFmpeg all work natively.

```powershell
# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

# Run
uvicorn flux.main:app --reload --host 127.0.0.1 --port 8000

# Test
pytest tests/unit/
ruff check flux/
python .agents/skills/flux-review/scripts/audit.py
```

**What doesn't work on Windows:**
- `termux-wake-lock` / `termux-boot`
- Android storage paths (`/storage/emulated/0/...`)
- ARM-specific binaries (Whisper.cpp)

**What works fine on Windows:**
- FastAPI backend, SQLite database, APScheduler
- FFmpeg filtergraph development and testing
- API integrations (YouTube, Telegram, Pexels)
- Unit and integration tests

### WSL (Optional)

If you prefer a Linux environment, WSL works well and behaves closer to Termux. Not required.

### Termux (Validation Only)

The phone is for final validation, not daily development. Slower iteration, but required for:
- ARM FFmpeg performance testing
- Instagrapi session behavior
- Android Doze mode effects on scheduler
- 48-hour soak tests

## Security Model

| Layer | Protection |
|-------|-----------|
| Admin panel | `127.0.0.1` only — no LAN/public WiFi exposure |
| Remote access | Tailscale mesh VPN + SSH key-only auth on port 8022 |
| Public endpoints | Only `/api/health` and `/api/system/remote` via Cloudflare Tunnel |
| Admin endpoints | NEVER exposed on public URL |
| Secrets | `.env` file, never committed; master key encrypts worker credentials |
| v1 auth | None — network-level access control only |

## Git Strategy

- `main` is always deployable
- Phase branches: `phase/1-core-engine`, `phase/2-quran-fetch`, etc.
- Squash-merge to `main` after device validation
- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`

## Monitoring (Future)

| Check | Method | Frequency |
|-------|--------|-----------|
| Health ping | GitHub Actions `curl` | Every 30 min |
| Render queue depth | Internal metric | Every 5 min |
| Storage usage | Internal metric | Every hour |
| Worker errors | Telegram notification | Event-driven |
| Thermal status | Internal metric | Before every render |

## Conception References

- Infrastructure: `conception_archive/10-infrastructure-and-deployment-plan.md`
- Security: `conception_archive/11-security-and-risk-assessment.md`
- Monitoring: `conception_archive/13-monitoring-observability-and-alerting.md`
- Build plan: `conception_archive/16-build-plan.md`
