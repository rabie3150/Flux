"""Flux FastAPI application entrypoint."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from flux.api.ingredients import router as ingredients_router
from flux.api.pipelines import router as pipelines_router
from flux.api.system import router as system_router
from flux.api.workers import router as workers_router
from flux.config import settings
from flux.db import init_db
from flux.logger import get_logger, setup_logging
from flux.scheduler import init_scheduler, shutdown_scheduler

logger = get_logger(__name__)
_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    setup_logging()
    logger.info("[Flux] Starting in %s mode", settings.flux_env)
    logger.info("[Flux] Database: %s", settings.database_url)
    logger.info("[Flux] Storage: %s", settings.storage_path)

    # Create database tables
    await init_db()
    logger.info("[Flux] Database initialized")

    # Initialize scheduler
    scheduler = init_scheduler()
    scheduler.start()
    logger.info("[Flux] Scheduler started")

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
app.include_router(ingredients_router)
app.include_router(workers_router)

# Static files for admin panel
app.mount("/admin", StaticFiles(directory="flux/static/admin", html=True), name="admin")


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
