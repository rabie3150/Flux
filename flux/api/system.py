"""System API endpoints — health, settings, activity log, dashboard."""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.config import settings
from flux.db import get_db
from flux.logger import get_logger
from flux.models import ActivityLog, Pipeline, PlatformWorker, Setting

logger = get_logger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

_START_TIME = time.time()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """System health for watchdog and diagnostics."""
    return {
        "status": "healthy",
        "uptime_seconds": int(time.time() - _START_TIME),
        "version": "0.1.0",
        "environment": settings.flux_env,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Aggregated stats for the admin dashboard."""
    pipeline_count = await db.execute(select(func.count(Pipeline.id)))
    worker_count = await db.execute(select(func.count(PlatformWorker.id)))
    
    from flux.core.storage import get_storage_budget
    storage_budget = get_storage_budget()
    
    recent_events = await db.execute(
        select(ActivityLog)
        .order_by(ActivityLog.timestamp.desc())
        .limit(10)
    )

    return {
        "pipelines": pipeline_count.scalar_one(),
        "workers": worker_count.scalar_one(),
        "storage": {
            "total_budget_mb": round(storage_budget.total_budget_bytes / (1024 * 1024), 2),
            "used_mb": round(storage_budget.used_bytes / (1024 * 1024), 2),
            "free_mb": round(storage_budget.free_bytes / (1024 * 1024), 2),
            "percent_used": round(storage_budget.percent_used, 1),
            "is_warning": storage_budget.is_warning,
            "is_critical": storage_budget.is_critical,
        },
        "recent_events": [
            {
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "level": e.level,
                "event_type": e.event_type,
                "message": e.message,
            }
            for e in recent_events.scalars().all()
        ],
    }


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class SettingUpdate(BaseModel):
    value: Any


@router.get("/settings")
async def list_settings(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return all runtime settings as key-value pairs."""
    result = await db.execute(select(Setting))
    settings_list = result.scalars().all()
    parsed = {}
    for s in settings_list:
        try:
            parsed[s.key] = json.loads(s.value_json)
        except json.JSONDecodeError:
            parsed[s.key] = s.value_json
    return parsed


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    update: SettingUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create or update a runtime setting."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if setting is None:
        setting = Setting(key=key, value_json=json.dumps(update.value))
        db.add(setting)
        logger.info("Setting created: %s", key)
    else:
        setting.value_json = json.dumps(update.value)
        logger.info("Setting updated: %s", key)

    await db.commit()
    await db.refresh(setting)
    try:
        return {setting.key: json.loads(setting.value_json)}
    except json.JSONDecodeError:
        return {setting.key: setting.value_json}


@router.delete("/settings/{key}")
async def delete_setting(
    key: str, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Delete a runtime setting."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        logger.warning("Setting not found: %s", key)
        raise HTTPException(status_code=404, detail="Setting not found")
    await db.delete(setting)
    await db.commit()
    logger.info("Setting deleted: %s", key)
    return {"deleted": key}


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------


@router.get("/activity")
async def list_activity(
    level: str | None = None,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Paginated activity log."""
    stmt = select(ActivityLog).order_by(ActivityLog.timestamp.desc())

    if level:
        stmt = stmt.where(ActivityLog.level == level)
    if event_type:
        stmt = stmt.where(ActivityLog.event_type == event_type)

    count_stmt = select(func.count(ActivityLog.id))
    if level:
        count_stmt = count_stmt.where(ActivityLog.level == level)
    if event_type:
        count_stmt = count_stmt.where(ActivityLog.event_type == event_type)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    events = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "level": e.level,
                "event_type": e.event_type,
                "message": e.message,
                "metadata_json": e.metadata_json,
            }
            for e in events
        ],
    }


# ---------------------------------------------------------------------------
# Remote API
# ---------------------------------------------------------------------------

class RemoteCommand(BaseModel):
    command: str


@router.post("/remote")
async def execute_remote_command(
    cmd: RemoteCommand,
    # Authorization would ideally use a Depends() to check FLUX_REMOTE_KEY bearer token
    # For now, it's a stub to allow the GitHub Action to not 404
) -> dict[str, Any]:
    """Execute a remote command (e.g., from GitHub Actions)."""
    command = cmd.command.lower()
    logger.info("Received remote command: %s", command)

    if command == "status":
        return {"status": "ok", "message": "Flux is running"}
    elif command == "restart":
        logger.warning("Remote restart requested (not fully implemented yet)")
        return {"status": "accepted", "message": "Restart requested"}
    elif command == "trigger_fetch":
        # In a real implementation, this would trigger the fetch job
        logger.info("Remote trigger_fetch requested")
        return {"status": "accepted", "message": "Fetch triggered"}
    elif command == "trigger_post":
        # In a real implementation, this would trigger the post job
        logger.info("Remote trigger_post requested")
        return {"status": "accepted", "message": "Post triggered"}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown command: {command}")
