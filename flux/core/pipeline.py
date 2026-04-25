"""Pipeline service — CRUD and business logic."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.models import Pipeline, PipelineWorker, PlatformWorker


async def list_pipelines(db: AsyncSession) -> list[Pipeline]:
    """Return all pipelines with their plugins."""
    result = await db.execute(select(Pipeline))
    return list(result.scalars().all())


async def get_pipeline(db: AsyncSession, pipeline_id: str) -> Pipeline | None:
    """Fetch a single pipeline by ID."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    return result.scalar_one_or_none()


async def create_pipeline(
    db: AsyncSession,
    name: str,
    plugin_id: str,
    config: dict[str, Any] | None = None,
    enabled: bool = True,
) -> Pipeline:
    """Create a new pipeline."""
    pipeline = Pipeline(
        name=name,
        plugin_id=plugin_id,
        config_json=json.dumps(config) if config else "{}",
        enabled=enabled,
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


async def update_pipeline(
    db: AsyncSession,
    pipeline_id: str,
    name: str | None = None,
    config: dict[str, Any] | None = None,
    enabled: bool | None = None,
) -> Pipeline | None:
    """Update pipeline fields. Partial update — only set provided values."""
    pipeline = await get_pipeline(db, pipeline_id)
    if pipeline is None:
        return None

    if name is not None:
        pipeline.name = name
    if config is not None:
        pipeline.config_json = json.dumps(config)
    if enabled is not None:
        pipeline.enabled = enabled

    await db.commit()
    await db.refresh(pipeline)
    return pipeline


async def delete_pipeline(db: AsyncSession, pipeline_id: str) -> bool:
    """Delete a pipeline and all its related data (cascade)."""
    pipeline = await get_pipeline(db, pipeline_id)
    if pipeline is None:
        return False
    await db.delete(pipeline)
    await db.commit()
    return True


async def attach_worker(
    db: AsyncSession, pipeline_id: str, worker_id: str
) -> bool:
    """Attach a platform worker to a pipeline. Idempotent."""
    # Check both exist
    pipeline = await get_pipeline(db, pipeline_id)
    worker_result = await db.execute(
        select(PlatformWorker).where(PlatformWorker.id == worker_id)
    )
    worker = worker_result.scalar_one_or_none()

    if pipeline is None or worker is None:
        return False

    # Check if already attached
    existing = await db.execute(
        select(PipelineWorker).where(
            PipelineWorker.pipeline_id == pipeline_id,
            PipelineWorker.worker_id == worker_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return True  # Already attached

    junction = PipelineWorker(pipeline_id=pipeline_id, worker_id=worker_id)
    db.add(junction)
    await db.commit()
    return True


async def detach_worker(
    db: AsyncSession, pipeline_id: str, worker_id: str
) -> bool:
    """Detach a platform worker from a pipeline."""
    result = await db.execute(
        select(PipelineWorker).where(
            PipelineWorker.pipeline_id == pipeline_id,
            PipelineWorker.worker_id == worker_id,
        )
    )
    junction = result.scalar_one_or_none()
    if junction is None:
        return False
    await db.delete(junction)
    await db.commit()
    return True


async def get_pipeline_workers(
    db: AsyncSession, pipeline_id: str
) -> list[PlatformWorker]:
    """Return all workers attached to a pipeline."""
    pipeline = await get_pipeline(db, pipeline_id)
    if pipeline is None:
        return []
    # Workers are loaded via relationship
    return list(pipeline.workers)
