"""Produced content service — render results, status tracking, lifecycle.

Manages the `produced_content` table: creation after render starts,
updates after render completes/fails, and querying for publishing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.logger import get_logger, log_activity
from flux.models import ProducedContent

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_produced_content(
    db: AsyncSession,
    pipeline_id: str,
    ingredient_ids: list[str],
    render_method: str = "video_compose",
) -> ProducedContent:
    """Create a produced_content record when render starts.

    Status is set to 'rendering'. Caller must commit.
    """
    content = ProducedContent(
        pipeline_id=pipeline_id,
        ingredient_ids_json=json.dumps(ingredient_ids),
        render_method=render_method,
        status="rendering",
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    logger.info("ProducedContent created: %s (rendering)", content.id)
    return content


async def update_render_success(
    db: AsyncSession,
    content_id: str,
    file_path: str,
    thumbnail_path: str | None = None,
    metadata: dict[str, Any] | None = None,
    caption: str = "",
) -> ProducedContent | None:
    """Update a produced_content record after successful render.

    Status transitions: rendering → rendered.
    """
    content = await get_produced_content(db, content_id)
    if content is None:
        logger.warning("ProducedContent not found for update: %s", content_id)
        return None

    content.file_path = file_path
    content.thumbnail_path = thumbnail_path
    content.content_meta_json = json.dumps(metadata) if metadata else None
    content.caption_text = caption or None
    content.status = "rendered"
    content.rendered_at = _now()

    await db.commit()
    await db.refresh(content)
    logger.info("ProducedContent rendered: %s → %s", content_id, file_path)
    log_activity(
        level="info",
        event_type="render_completed",
        message=f"Render completed for content {content_id}",
        pipeline_id=content.pipeline_id,
    )
    return content


async def update_render_failed(
    db: AsyncSession,
    content_id: str,
    error_message: str,
) -> ProducedContent | None:
    """Mark a produced_content record as failed after render error."""
    content = await get_produced_content(db, content_id)
    if content is None:
        logger.warning("ProducedContent not found for fail update: %s", content_id)
        return None

    content.status = "failed"
    content.render_log = error_message

    await db.commit()
    await db.refresh(content)
    logger.error("ProducedContent render failed: %s — %s", content_id, error_message)
    log_activity(
        level="error",
        event_type="render_failed",
        message=f"Render failed for content {content_id}: {error_message}",
        pipeline_id=content.pipeline_id,
    )
    return content


async def mark_ready(
    db: AsyncSession,
    content_id: str,
) -> ProducedContent | None:
    """Mark rendered content as ready for publishing.

    Typically called after successful verse identification.
    """
    content = await get_produced_content(db, content_id)
    if content is None:
        return None

    content.status = "ready"
    content.ready_at = _now()
    await db.commit()
    await db.refresh(content)
    logger.info("ProducedContent ready: %s", content_id)
    return content


async def get_produced_content(
    db: AsyncSession, content_id: str
) -> ProducedContent | None:
    """Fetch a single produced_content record by ID."""
    result = await db.execute(
        select(ProducedContent).where(ProducedContent.id == content_id)
    )
    return result.scalar_one_or_none()


async def list_produced_content(
    db: AsyncSession,
    pipeline_id: str | None = None,
    status: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[ProducedContent]:
    """List produced_content records with optional filters."""
    stmt = select(ProducedContent)

    if pipeline_id:
        stmt = stmt.where(ProducedContent.pipeline_id == pipeline_id)
    if status:
        stmt = stmt.where(ProducedContent.status == status)

    stmt = (
        stmt.order_by(ProducedContent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
