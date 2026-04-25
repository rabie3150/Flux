"""Platform Worker API endpoints — CRUD for social media accounts."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.db import get_db
from flux.models import PlatformWorker

router = APIRouter(prefix="/api/workers", tags=["workers"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WorkerCreate(BaseModel):
    platform: str = Field(..., min_length=1, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=128)
    credentials: dict[str, Any] = Field(default_factory=dict)
    schedule_cron: str | None = Field(default=None, max_length=64)
    caption_template_override: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    enabled: bool = True


class WorkerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    credentials: dict[str, Any] | None = None
    schedule_cron: str | None = Field(default=None, max_length=64)
    caption_template_override: str | None = None
    hashtags: list[str] | None = None
    enabled: bool | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_worker(w: PlatformWorker) -> dict[str, Any]:
    return {
        "id": w.id,
        "platform": w.platform,
        "display_name": w.display_name,
        # credentials_json intentionally omitted — never expose secrets
        "schedule_cron": w.schedule_cron,
        "caption_template_override": w.caption_template_override,
        "hashtags_json": w.hashtags_json,
        "enabled": w.enabled,
        "last_posted_at": w.last_posted_at.isoformat() if w.last_posted_at else None,
        "last_error_at": w.last_error_at.isoformat() if w.last_error_at else None,
        "last_error_message": w.last_error_message,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("")
async def list_workers(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all platform workers."""
    result = await db.execute(select(PlatformWorker))
    workers = result.scalars().all()
    return [_serialize_worker(w) for w in workers]


@router.post("", status_code=201)
async def create_worker(
    data: WorkerCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new platform worker."""
    import json

    worker = PlatformWorker(
        platform=data.platform,
        display_name=data.display_name,
        credentials_json=json.dumps(data.credentials),
        schedule_cron=data.schedule_cron,
        caption_template_override=data.caption_template_override,
        hashtags_json=json.dumps(data.hashtags),
        enabled=data.enabled,
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    return _serialize_worker(worker)


@router.get("/{worker_id}")
async def get_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get worker details."""
    result = await db.execute(
        select(PlatformWorker).where(PlatformWorker.id == worker_id)
    )
    worker = result.scalar_one_or_none()
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    return _serialize_worker(worker)


@router.put("/{worker_id}")
async def update_worker(
    worker_id: str,
    data: WorkerUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update a worker (partial update)."""
    import json

    result = await db.execute(
        select(PlatformWorker).where(PlatformWorker.id == worker_id)
    )
    worker = result.scalar_one_or_none()
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    if data.display_name is not None:
        worker.display_name = data.display_name
    if data.credentials is not None:
        worker.credentials_json = json.dumps(data.credentials)
    if data.schedule_cron is not None:
        worker.schedule_cron = data.schedule_cron
    if data.caption_template_override is not None:
        worker.caption_template_override = data.caption_template_override
    if data.hashtags is not None:
        worker.hashtags_json = json.dumps(data.hashtags)
    if data.enabled is not None:
        worker.enabled = data.enabled

    await db.commit()
    await db.refresh(worker)
    return _serialize_worker(worker)


@router.delete("/{worker_id}")
async def delete_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a platform worker."""
    result = await db.execute(
        select(PlatformWorker).where(PlatformWorker.id == worker_id)
    )
    worker = result.scalar_one_or_none()
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    await db.delete(worker)
    await db.commit()
    return {"deleted": worker_id}
