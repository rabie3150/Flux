"""Post Record API endpoints — publishing audit trail."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.db import get_db
from flux.logger import get_logger
from flux.models import Pipeline, PlatformWorker, PostRecord, ProducedContent

logger = get_logger(__name__)

router = APIRouter(prefix="/api/posts", tags=["posts"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PostListParams(BaseModel):
    platform: str | None = None
    status: str | None = None
    pipeline_id: str | None = None
    worker_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verse_label(content_meta: dict[str, Any] | None) -> str:
    if not content_meta:
        return "Unknown verse"
    surah = content_meta.get("surah")
    ayah = content_meta.get("ayah")
    ayah_end = content_meta.get("ayah_end")
    if not surah or not ayah:
        return "Unknown verse"
    if ayah_end and ayah_end > ayah:
        return f"{surah}:{ayah}-{ayah_end}"
    return f"{surah}:{ayah}"


def _serialize_post(
    post: PostRecord,
    worker: PlatformWorker | None = None,
    content: ProducedContent | None = None,
    pipeline: Pipeline | None = None,
) -> dict[str, Any]:
    content_meta = (
        json.loads(content.content_meta_json)
        if content and content.content_meta_json
        else {}
    )
    return {
        "id": post.id,
        "status": post.status,
        "platform": worker.platform if worker else None,
        "worker_id": post.worker_id,
        "worker_name": worker.display_name if worker else None,
        "pipeline_id": content.pipeline_id if content else None,
        "pipeline_name": pipeline.name if pipeline else None,
        "verse_label": _verse_label(content_meta),
        "caption_used": post.caption_used,
        "platform_post_id": post.platform_post_id,
        "platform_url": post.platform_url,
        "error_log": post.error_log,
        "attempt_count": post.attempt_count,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_posts(
    platform: str | None = None,
    status: str | None = None,
    pipeline_id: str | None = None,
    worker_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List post records with filtering and pagination."""
    stmt = (
        select(PostRecord, PlatformWorker, ProducedContent, Pipeline)
        .join(PlatformWorker, PostRecord.worker_id == PlatformWorker.id, isouter=True)
        .join(ProducedContent, PostRecord.produced_content_id == ProducedContent.id, isouter=True)
        .join(Pipeline, ProducedContent.pipeline_id == Pipeline.id, isouter=True)
    )

    if platform:
        stmt = stmt.where(PlatformWorker.platform == platform)
    if status:
        stmt = stmt.where(PostRecord.status == status)
    if pipeline_id:
        stmt = stmt.where(ProducedContent.pipeline_id == pipeline_id)
    if worker_id:
        stmt = stmt.where(PostRecord.worker_id == worker_id)
    if date_from:
        stmt = stmt.where(PostRecord.created_at >= date_from)
    if date_to:
        stmt = stmt.where(PostRecord.created_at <= date_to)

    stmt = stmt.order_by(PostRecord.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    rows = result.all()

    posts = [_serialize_post(post, worker, content, pipeline) for post, worker, content, pipeline in rows]

    # Total count for pagination
    count_stmt = select(PostRecord)
    if platform:
        count_stmt = count_stmt.join(PlatformWorker).where(PlatformWorker.platform == platform)
    if status:
        count_stmt = count_stmt.where(PostRecord.status == status)
    if pipeline_id:
        count_stmt = count_stmt.join(ProducedContent).where(ProducedContent.pipeline_id == pipeline_id)
    if worker_id:
        count_stmt = count_stmt.where(PostRecord.worker_id == worker_id)
    if date_from:
        count_stmt = count_stmt.where(PostRecord.created_at >= date_from)
    if date_to:
        count_stmt = count_stmt.where(PostRecord.created_at <= date_to)

    total_result = await db.execute(select(count_stmt.subquery().c.id))
    total = total_result.scalar() or 0

    return {"posts": posts, "total": total, "limit": limit, "offset": offset}


@router.get("/{post_id}")
async def get_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a single post record with full details."""
    stmt = (
        select(PostRecord, PlatformWorker, ProducedContent, Pipeline)
        .join(PlatformWorker, PostRecord.worker_id == PlatformWorker.id, isouter=True)
        .join(ProducedContent, PostRecord.produced_content_id == ProducedContent.id, isouter=True)
        .join(Pipeline, ProducedContent.pipeline_id == Pipeline.id, isouter=True)
        .where(PostRecord.id == post_id)
    )
    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")

    post, worker, content, pipeline = row
    return _serialize_post(post, worker, content, pipeline)
