"""Flux FastAPI application entrypoint."""

from __future__ import annotations

import sys
import asyncio

# On Windows, explicitly set ProactorEventLoop to support subprocesses.
# This MUST happen before any event loop is created or used.
if sys.platform == "win32":
    try:
        # Use a more robust way to set the policy
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
    except Exception as e:
        sys.stderr.write(f"[PRE-START] Failed to set Proactor policy: {e}\n")

import time
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from flux.api.ingredients import router as ingredients_router
from flux.api.pipelines import router as pipelines_router
from flux.api.production import router as production_router
from flux.api.system import router as system_router
from flux.api.workers import router as workers_router
from flux.config import settings
from flux.db import init_db
from flux.logger import get_logger, setup_logging
from flux.plugins import load_plugins
from flux.scheduler import init_scheduler, shutdown_scheduler

logger = get_logger(__name__)
_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Re-verify loop type on Windows
    if sys.platform == "win32":
        try:
            loop = asyncio.get_running_loop()
            if not isinstance(loop, asyncio.ProactorEventLoop):
                logger.warning("Event loop is %s, NOT ProactorEventLoop. FFmpeg may fail.", type(loop).__name__)
            else:
                logger.info("Event loop confirmed as ProactorEventLoop")
        except RuntimeError:
            # Loop not yet running, which is expected in some uvicorn versions
            logger.debug("Asyncio loop not yet running during lifespan verification")
        except Exception as e:
            logger.debug("Failed to verify loop type: %s", e)

    try:
        setup_logging()
    except Exception as e:
        # If logging setup fails, we can't log it — print to stderr as last resort
        sys.stderr.write(f"[FATAL] Logging setup failed: {e}\n")
        raise

    logger.info("[Flux] Starting in %s mode", settings.flux_env)
    logger.info("[Flux] Database: %s", settings.database_url)
    logger.info("[Flux] Storage: %s", settings.storage_path)

    try:
        await init_db()
        logger.info("[Flux] Database initialized")
    except Exception as e:
        logger.error("[Flux] Database initialization failed: %s", e)
        raise

    try:
        load_plugins()
        from flux.plugins.loader import sync_plugins_to_db
        from flux.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await sync_plugins_to_db(db)
    except Exception as e:
        logger.error("[Flux] Plugin loading or sync failed: %s", e)
        raise

    try:
        scheduler = init_scheduler()
        scheduler.start()
        logger.info("[Flux] Scheduler started")
    except Exception as e:
        logger.error("[Flux] Scheduler startup failed: %s", e)
        raise

    yield

    # Shutdown
    shutdown_scheduler()
    logger.info("[Flux] Shutting down")


app = FastAPI(
    title="Flux",
    description="The idle automator. Content automation engine.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — localhost only; no external origins needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(system_router)
app.include_router(pipelines_router)
app.include_router(production_router)
app.include_router(ingredients_router)
app.include_router(workers_router)

# Static files for admin panel
_admin_dir = Path(__file__).resolve().parent / "static" / "admin"
if _admin_dir.exists():
    app.mount("/admin", StaticFiles(directory=str(_admin_dir), html=True), name="admin")


@app.get("/api/health")
async def health_check() -> dict:
    """System health endpoint for watchdog and diagnostics."""
    return {
        "status": "healthy",
        "uptime_seconds": int(time.time() - _START_TIME),
        "version": "0.1.0",
        "environment": settings.flux_env,
    }


@app.get("/")
async def root() -> dict:
    """Root redirect to admin panel."""
    return {"message": "Flux is running", "admin": "/admin", "health": "/api/health"}

if __name__ == "__main__":
    # Start the server programmatically
    # This is the most reliable way to ensure Windows loop policy is applied
    uvicorn.run("flux.main:app", host="127.0.0.1", port=8000, reload=True)
