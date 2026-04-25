"""System API endpoints — health, settings, activity log, dashboard."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.config import settings
from flux.db import get_db
from flux.models import ActivityLog, Pipeline, PlatformWorker, Setting

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
    recent_events = await db.execute(
        select(ActivityLog)
        .order_by(ActivityLog.timestamp.desc())
        .limit(10)
    )

    return {
        "pipelines": pipeline_count.scalar_one(),
        "workers": worker_count.scalar_one(),
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
    return {s.key: s.value_json for s in settings_list}


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    update: SettingUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create or update a runtime setting."""
    import json

    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if setting is None:
        setting = Setting(key=key, value_json=json.dumps(update.value))
        db.add(setting)
    else:
        setting.value_json = json.dumps(update.value)

    await db.commit()
    await db.refresh(setting)
    return {setting.key: setting.value_json}


@router.delete("/settings/{key}")
async def delete_setting(
    key: str, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Delete a runtime setting."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    await db.delete(setting)
    await db.commit()
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
