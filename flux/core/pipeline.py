"""Pipeline service — CRUD and business logic."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.core import ingredients as ingredient_service
from flux.logger import get_logger, log_activity
from flux.models import Pipeline, PipelineWorker, PlatformWorker, Plugin
from flux.plugins import get_plugin

logger = get_logger(__name__)


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
    logger.info("Pipeline created: %s (%s)", pipeline.name, pipeline.id)
    log_activity(
        level="info",
        event_type="pipeline_created",
        message=f"Pipeline {name} created",
        pipeline_id=pipeline.id
    )
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
    # audit: skip duplication
    logger.info("Pipeline updated: %s", pipeline_id)
    log_activity(
        level="info",
        event_type="pipeline_updated",
        message=f"Pipeline {pipeline.name} updated",
        pipeline_id=pipeline_id
    )
    return pipeline


async def delete_pipeline(db: AsyncSession, pipeline_id: str) -> bool:
    """Delete a pipeline and all its related data (cascade)."""
    pipeline = await get_pipeline(db, pipeline_id)
    if pipeline is None:
        return False
    await db.delete(pipeline)
    await db.commit()
    # audit: skip duplication
    logger.info("Pipeline deleted: %s", pipeline_id)
    log_activity(
        level="info",
        event_type="pipeline_deleted",
        message=f"Pipeline {pipeline_id} deleted",
        pipeline_id=pipeline_id
    )
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
    # audit: skip duplication
    logger.info("Worker attached to pipeline: %s -> %s", worker_id, pipeline_id)
    log_activity(
        level="info",
        event_type="worker_attached",
        message=f"Worker {worker_id} attached to pipeline {pipeline_id}",
        pipeline_id=pipeline_id,
        worker_id=worker_id
    )
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
    # audit: skip duplication
    logger.info("Worker detached from pipeline: %s -> %s", worker_id, pipeline_id)
    log_activity(
        level="info",
        event_type="worker_detached",
        message=f"Worker {worker_id} detached from pipeline {pipeline_id}",
        pipeline_id=pipeline_id,
        worker_id=worker_id
    )
    return True


async def get_pipeline_workers(
    db: AsyncSession, pipeline_id: str
) -> list[PlatformWorker]:
    """Return all workers attached to a pipeline."""
    result = await db.execute(
        select(PlatformWorker)
        .join(PipelineWorker)
        .where(PipelineWorker.pipeline_id == pipeline_id)
    )
    return list(result.scalars().all())


async def trigger_fetch(db: AsyncSession, pipeline_id: str) -> dict[str, Any]:
    """Trigger a fetch job for a pipeline.

    Loads the pipeline's plugin, calls plugin.fetch(), and inserts
    returned ingredients into the database with status='pending'.
    """
    pipeline = await get_pipeline(db, pipeline_id)
    if pipeline is None:
        raise ValueError("Pipeline not found")

    # plugin_id on Pipeline is the DB record UUID; we need the plugin name
    plugin_record = await db.execute(
        select(Plugin).where(Plugin.id == pipeline.plugin_id)
    )
    plugin_row = plugin_record.scalar_one_or_none()
    if plugin_row is None:
        raise ValueError(f"Plugin record '{pipeline.plugin_id}' not found")

    plugin = get_plugin(plugin_row.name)
    if plugin is None:
        raise ValueError(f"Plugin '{plugin_row.name}' not loaded")

    config = json.loads(pipeline.config_json) if pipeline.config_json else {}
    ingredients = await plugin.fetch(pipeline_id, config)

    created = 0
    for item in ingredients:
        await ingredient_service.create_ingredient(
            db,
            pipeline_id=pipeline_id,
            type=item["type"],
            file_path=item.get("file_path"),
            source_url=item.get("source_url"),
            metadata=item.get("metadata"),
            file_size_bytes=item.get("file_size_bytes"),
            duration_secs=item.get("duration_secs"),
        )
        created += 1

    logger.info("Fetch triggered for pipeline %s: %d ingredients created", pipeline_id, created)
    log_activity(
        level="info",
        event_type="fetch_triggered",
        message=f"Fetched {created} ingredients for pipeline {pipeline_id}",
        pipeline_id=pipeline_id,
    )
    return {"created": created, "pipeline_id": pipeline_id}
