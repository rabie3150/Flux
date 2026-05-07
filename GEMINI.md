# Flux Project Context

## Project Overview
Flux is "The idle automator," a content automation engine primarily designed to run on Termux (Android) but also supports Windows/Linux. It orchestrates pipelines, handles ingredients, and schedules automated content production.

**Main Technologies**:
- **Python**: 3.11+
- **Web Framework**: FastAPI & Uvicorn
- **Concurrency**: `asyncio`
- **Scheduler**: APScheduler
- **Database**: SQLite (WAL mode) / SQLAlchemy + Alembic
- **Tools**: `yt-dlp`, FFmpeg (crucial for rendering)

## Development Philosophy & Workflow
1. **Vertical Slice > Backend-First**: Every phase must produce a working, testable slice (DB -> API -> UI -> Hardware). Do not build isolated layers in a vacuum.
2. **Risk-Driven Order**: Build highest-risk components first (e.g., FFmpeg on ARM, yt-dlp, Instagrapi persistence).
3. **Device-First Validation**: Develop on Windows/WSL for speed, but **validate on Termux (phone)**. Code is not "done" until it runs on the target ARM device.
4. **Plugin-First Architecture**: The `quran` pipeline is the reference plugin implementation.

## Git & Merging Strategy
- **Monorepo**: Contains backend, frontend (admin UI), and plugins.
- **Branching**: Use feature/phase branches (e.g., `phase/5-platform-workers`). `main` is always deployable to Termux.
- **Definition of Done (Merge Criteria)**:
  - All unit tests pass.
  - All integration tests pass.
  - Device tests pass on the target phone.
  - Admin panel is usable.
  - `bootstrap.sh` runs clean.
  - No `print()` statements (use structured logging).

## Testing Strategy
- **Unit Tests**: Fast, pure Python, no I/O (run locally).
- **Integration Tests**: Uses SQLite in-memory and FastAPI TestClient (run locally).
- **Device Tests**: Validates ARM/Termux reality (e.g., FFmpeg encode speed, YouTube API on mobile IP). Use `@pytest.mark.device`.

## Building and Running
- **Dependencies**: Managed via `uv` or `pip` (`uv.lock`, `pyproject.toml`, `requirements.txt`).
- **Start the Engine**:
  ```bash
  python flux/main.py
  # OR
  uvicorn flux.main:app --host 127.0.0.1 --port 8000 --reload
  ```
- **Termux Environment**: For Termux deployment, refer to `scripts/start.sh` (activates venv, acquires wake lock, ensures storage, starts `uvicorn`).
- **Testing**:
  ```bash
  pytest
  ```

## Development Conventions
1. **Living Documentation**: The `documents/` directory contains living docs. Code and documentation must be updated together.
   - The `documents/conception_archive/` is frozen; do not modify it.
   - Update `documents/database/README.md` for schema changes.
2. **Plugin Architecture**: New plugins should be added to `flux/plugins/` adhering to the interface described in `documents/plugins/plugin-interface.md`.
3. **Error Handling**: Follow the error classification and retry rules in `documents/error-handler/`.
