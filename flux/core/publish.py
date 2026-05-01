"""Publishing orchestrator — scheduler-driven posting to social platforms.

Flow:
1. Scheduler triggers worker job on cron schedule.
2. Pick next ready content from worker's attached pipelines.
3. Build caption via plugin.build_caption().
4. Call platform publisher.
5. Record PostRecord (success or failure).
6. Retry transient failures up to 3×.
7. Auto-delete local files after all platforms succeed (configurable).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.core.crypto import decrypt_dict
from flux.db import AsyncSessionLocal
from flux.logger import get_logger, log_activity
from flux.models import PipelineWorker, PlatformWorker, PostRecord, ProducedContent
from flux.platforms.publisher import get_publisher
from flux.plugins import get_plugin

logger = get_logger(__name__)

MAX_RETRIES = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_ready_content(
    db: AsyncSession, worker: PlatformWorker
) -> ProducedContent | None:
    """Pick the oldest ready content from any pipeline attached to this worker."""
    result = await db.execute(
        select(PipelineWorker.pipeline_id).where(PipelineWorker.worker_id == worker.id)
    )
    pipeline_ids = {row[0] for row in result.all()}
    if not pipeline_ids:
        return None

    stmt = (
        select(ProducedContent)
        .where(
            ProducedContent.pipeline_id.in_(pipeline_ids),
            ProducedContent.status == "ready",
        )
        .order_by(ProducedContent.ready_at.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _already_posted(
    db: AsyncSession, content_id: str, worker_id: str
) -> bool:
    """Check if this content has already been posted to this worker."""
    result = await db.execute(
        select(PostRecord).where(
            PostRecord.produced_content_id == content_id,
            PostRecord.worker_id == worker_id,
            PostRecord.status == "published",
        )
    )
    return result.scalar_one_or_none() is not None


async def _record_attempt(
    db: AsyncSession,
    content_id: str,
    worker_id: str,
    success: bool,
    post_id: str | None = None,
    url: str | None = None,
    caption: str | None = None,
    error: str | None = None,
    attempt_count: int = 1,
) -> PostRecord:
    """Record a post attempt. Updates existing record on retry."""
    result = await db.execute(
        select(PostRecord).where(
            PostRecord.produced_content_id == content_id,
            PostRecord.worker_id == worker_id,
        )
    )
    record = result.scalar_one_or_none()

    if record is None:
        record = PostRecord(
            produced_content_id=content_id,
            worker_id=worker_id,
            status="published" if success else "failed",
            platform_post_id=post_id,
            platform_url=url,
            caption_used=caption,
            error_log=error,
            attempt_count=attempt_count,
            published_at=_now() if success else None,
        )
        db.add(record)
    else:
        record.status = "published" if success else "failed"
        record.platform_post_id = post_id
        record.platform_url = url
        record.caption_used = caption
        record.error_log = error
        record.attempt_count = attempt_count
        if success:
            record.published_at = _now()

    await db.commit()
    await db.refresh(record)
    return record


async def _update_worker_status(
    db: AsyncSession, worker: PlatformWorker, success: bool, error: str | None = None
) -> None:
    """Update worker last_posted_at / last_error_at tracking."""
    if success:
        worker.last_posted_at = _now()
        worker.last_error_message = None
    else:
        worker.last_error_at = _now()
        worker.last_error_message = error
    await db.commit()


async def _maybe_auto_delete(db: AsyncSession, content: ProducedContent) -> None:
    """Delete local MP4 if all attached workers have published successfully."""
    result = await db.execute(
        select(PipelineWorker.worker_id).where(
            PipelineWorker.pipeline_id == content.pipeline_id
        )
    )
    worker_ids = {row[0] for row in result.all()}
    if not worker_ids:
        return

    for worker_id in worker_ids:
        posted = await _already_posted(db, content.id, worker_id)
        if not posted:
            return  # Not all platforms done yet

    # All platforms posted — safe to delete
    try:
        if content.file_path:
            Path(content.file_path).unlink(missing_ok=True)
            logger.info("Auto-deleted rendered file: %s", content.file_path)
        if content.thumbnail_path:
            Path(content.thumbnail_path).unlink(missing_ok=True)
            logger.info("Auto-deleted thumbnail: %s", content.thumbnail_path)
        content.status = "published"
        await db.commit()
    except OSError as exc:
        logger.warning("Auto-delete failed for %s: %s", content.id, exc)


async def publish_for_worker(worker_id: str) -> dict[str, Any]:
    """Main entry point: attempt to publish the next ready item for a worker.

    Called by APScheduler on the worker's cron schedule.
    """
    async with AsyncSessionLocal() as db:
        worker = await db.get(PlatformWorker, worker_id)
        if not worker:
            logger.warning("Worker not found: %s", worker_id)
            return {"ok": False, "error": "Worker not found"}

        if not worker.enabled:
            logger.info("Worker %s is disabled, skipping.", worker_id)
            return {"ok": True, "skipped": True, "reason": "disabled"}

        content = await _get_ready_content(db, worker)
        if not content:
            logger.info("No ready content for worker %s", worker_id)
            return {"ok": True, "skipped": True, "reason": "no_ready_content"}

        if await _already_posted(db, content.id, worker.id):
            logger.info("Content %s already posted to worker %s", content.id, worker_id)
            return {"ok": True, "skipped": True, "reason": "already_posted"}

        # Load plugin to build caption
        pipeline = await db.get(Pipeline, content.pipeline_id)
        plugin = get_plugin(pipeline.plugin_id) if pipeline else None
        if not plugin:
            logger.error("Plugin not found for pipeline %s", content.pipeline_id)
            return {"ok": False, "error": "Plugin not found"}

        config = json.loads(pipeline.config_json or "{}")
        worker_config = {
            "platform": worker.platform,
            "hashtags": json.loads(worker.hashtags_json or "[]"),
        }
        if worker.caption_template_override:
            worker_config["caption_template_override"] = worker.caption_template_override

        caption = await plugin.build_caption(
            pipeline.id, content.id, config, worker_config
        )

        # Decrypt credentials
        credentials = decrypt_dict(worker.credentials_json)

        # Get publisher
        try:
            publisher = get_publisher(
                worker.platform, worker.connection_strategy, credentials
            )
        except ValueError as exc:
            # Bad config is a permanent failure — no retry will help
            err = f"Invalid publisher config: {exc}"
            logger.error("Worker %s: %s", worker_id, err)
            await _record_attempt(
                db, content.id, worker.id, success=False, error=err, attempt_count=1
            )
            await _update_worker_status(db, worker, success=False, error=err)
            worker.enabled = False
            await db.commit()
            return {"ok": False, "error": err, "transient": False}

        # Publish
        logger.info(
            "Publishing content %s to %s (%s)",
            content.id,
            worker.platform,
            publisher.name,
        )

        result = await publisher.publish(
            file_path=content.file_path or "",
            caption=caption,
            thumbnail_path=content.thumbnail_path,
        )

        # Determine attempt count
        existing = await db.execute(
            select(PostRecord).where(
                PostRecord.produced_content_id == content.id,
                PostRecord.worker_id == worker.id,
            )
        )
        existing_record = existing.scalar_one_or_none()
        attempt_count = (existing_record.attempt_count + 1) if existing_record else 1

        if result.success:
            await _record_attempt(
                db,
                content.id,
                worker.id,
                success=True,
                post_id=result.post_id,
                url=result.url,
                caption=caption,
                attempt_count=attempt_count,
            )
            await _update_worker_status(db, worker, success=True)
            await _maybe_auto_delete(db, content)
            log_activity(
                level="info",
                event_type="post_published",
                message=f"Posted to {worker.platform} ({publisher.name})",
                pipeline_id=content.pipeline_id,
                worker_id=worker.id,
            )
            return {
                "ok": True,
                "post_id": result.post_id,
                "url": result.url,
                "platform": worker.platform,
            }

        # Failure — decide if retryable
        should_retry = result.transient and attempt_count < MAX_RETRIES
        await _record_attempt(
            db,
            content.id,
            worker.id,
            success=False,
            error=result.error,
            attempt_count=attempt_count,
        )
        await _update_worker_status(db, worker, success=False, error=result.error)

        if not should_retry:
            # Permanent failure — pause worker to avoid spam
            worker.enabled = False
            await db.commit()
            logger.error(
                "Worker %s paused after %d failed attempts. Error: %s",
                worker_id,
                attempt_count,
                result.error,
            )
            log_activity(
                level="error",
                event_type="worker_paused",
                message=f"Worker {worker.display_name} paused: {result.error}",
                worker_id=worker.id,
            )

        return {
            "ok": False,
            "error": result.error,
            "transient": result.transient,
            "attempt_count": attempt_count,
            "retry_on_next_cron": should_retry,
        }
