"""Flux FastAPI application entrypoint."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from flux.config import settings

logger = logging.getLogger(__name__)
_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("[Flux] Starting in %s mode", settings.flux_env)
    logger.info("[Flux] Database: %s", settings.database_url)
    logger.info("[Flux] Storage: %s", settings.storage_path)
    yield
    # Shutdown
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

# Static files for admin panel
# Note: admin panel files will be added in Phase 6
# app.mount("/admin", StaticFiles(directory="flux/static/admin", html=True), name="admin")


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
    """Root redirect to health."""
    return {"message": "Flux is running", "health": "/api/health"}
