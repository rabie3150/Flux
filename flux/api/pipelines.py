"""Pipeline API endpoints — CRUD, stats, worker attachment."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from flux.core import pipeline as pipeline_service
from flux.db import get_db
from flux.models import Pipeline

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    plugin_id: str = Field(..., min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PipelineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    config: dict[str, Any] | None = None
    enabled: bool | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_pipeline(p: Pipeline) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "plugin_id": p.plugin_id,
        "enabled": p.enabled,
        "config_json": p.config_json,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("")
async def list_pipelines(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all pipelines."""
    pipelines = await pipeline_service.list_pipelines(db)
    return [_serialize_pipeline(p) for p in pipelines]


@router.post("", status_code=201)
async def create_pipeline(
    data: PipelineCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new pipeline."""
    pipeline = await pipeline_service.create_pipeline(
        db,
        name=data.name,
        plugin_id=data.plugin_id,
        config=data.config,
        enabled=data.enabled,
    )
    return _serialize_pipeline(pipeline)


@router.get("/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get pipeline details."""
    pipeline = await pipeline_service.get_pipeline(db, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return _serialize_pipeline(pipeline)


@router.put("/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    data: PipelineUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update a pipeline (partial update)."""
    pipeline = await pipeline_service.update_pipeline(
        db,
        pipeline_id,
        name=data.name,
        config=data.config,
        enabled=data.enabled,
    )
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return _serialize_pipeline(pipeline)


@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a pipeline and all related data."""
    deleted = await pipeline_service.delete_pipeline(db, pipeline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"deleted": pipeline_id}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/{pipeline_id}/stats")
async def pipeline_stats(
    pipeline_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Pipeline statistics: stock levels, queue depth, etc."""
    from flux.core.ingredients import count_ingredients

    pipeline = await pipeline_service.get_pipeline(db, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Count ingredients by status
    approved = await count_ingredients(db, pipeline_id, status="approved")
    pending = await count_ingredients(db, pipeline_id, status="pending")
    rejected = await count_ingredients(db, pipeline_id, status="rejected")

    return {
        "pipeline_id": pipeline_id,
        "pipeline_name": pipeline.name,
        "enabled": pipeline.enabled,
        "stock": {
            "approved": approved,
            "pending": pending,
            "rejected": rejected,
        },
    }


# ---------------------------------------------------------------------------
# Worker Attachment
# ---------------------------------------------------------------------------


class WorkerAttachRequest(BaseModel):
    worker_id: str


@router.post("/{pipeline_id}/workers")
async def attach_worker(
    pipeline_id: str,
    req: WorkerAttachRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Attach a platform worker to this pipeline."""
    ok = await pipeline_service.attach_worker(db, pipeline_id, req.worker_id)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Pipeline or worker not found, or already attached",
        )
    return {"attached": req.worker_id}


@router.delete("/{pipeline_id}/workers/{worker_id}")
async def detach_worker(
    pipeline_id: str,
    worker_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Detach a platform worker from this pipeline."""
    ok = await pipeline_service.detach_worker(db, pipeline_id, worker_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"detached": worker_id}


@router.get("/{pipeline_id}/workers")
async def list_pipeline_workers(
    pipeline_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List workers attached to this pipeline."""
    pipeline = await pipeline_service.get_pipeline(db, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    workers = await pipeline_service.get_pipeline_workers(db, pipeline_id)
    return [
        {
            "id": w.id,
            "platform": w.platform,
            "display_name": w.display_name,
            "enabled": w.enabled,
            "schedule_cron": w.schedule_cron,
        }
        for w in workers
    ]
