"""Platform Worker core logic — CRUD and secure storage."""

from __future__ import annotations

import json
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.core.crypto import encrypt_dict
from flux.logger import get_logger, log_activity
from flux.models import PlatformWorker

logger = get_logger(__name__)


async def list_workers(db: AsyncSession) -> Sequence[PlatformWorker]:
    """Return all platform workers."""
    result = await db.execute(select(PlatformWorker))
    return result.scalars().all()


async def get_worker(db: AsyncSession, worker_id: str) -> PlatformWorker | None:
    """Fetch a single worker by ID."""
    result = await db.execute(select(PlatformWorker).where(PlatformWorker.id == worker_id))
    return result.scalar_one_or_none()


async def create_worker(
    db: AsyncSession,
    platform: str,
    display_name: str,
    credentials: dict[str, Any],
    schedule_cron: str | None = None,
    caption_template_override: str | None = None,
    hashtags: list[str] | None = None,
    enabled: bool = True,
) -> PlatformWorker:
    """Create a new platform worker with encrypted credentials."""
    worker = PlatformWorker(
        platform=platform,
        display_name=display_name,
        credentials_json=encrypt_dict(credentials),
        schedule_cron=schedule_cron,
        caption_template_override=caption_template_override,
        hashtags_json=json.dumps(hashtags or []),
        enabled=enabled,
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    # audit: skip duplication
    logger.info("Worker created: %s", worker.id)
    log_activity(
        level="info",
        event_type="worker_created",
        message=f"Worker {display_name} ({platform}) created",
        worker_id=worker.id
    )
    return worker


async def update_worker(
    db: AsyncSession,
    worker_id: str,
    display_name: str | None = None,
    credentials: dict[str, Any] | None = None,
    schedule_cron: str | None = None,
    caption_template_override: str | None = None,
    hashtags: list[str] | None = None,
    enabled: bool | None = None,
) -> PlatformWorker | None:
    """Update a worker."""
    worker = await get_worker(db, worker_id)
    if worker is None:
        return None

    if display_name is not None:
        worker.display_name = display_name
    if credentials is not None:
        worker.credentials_json = encrypt_dict(credentials)
    if schedule_cron is not None:
        worker.schedule_cron = schedule_cron
    if caption_template_override is not None:
        worker.caption_template_override = caption_template_override
    if hashtags is not None:
        worker.hashtags_json = json.dumps(hashtags)
    if enabled is not None:
        worker.enabled = enabled

    await db.commit()
    await db.refresh(worker)
    # audit: skip duplication
    logger.info("Worker updated: %s", worker_id)
    log_activity(
        level="info",
        event_type="worker_updated",
        message=f"Worker {worker.display_name} updated",
        worker_id=worker_id
    )
    return worker


async def delete_worker(db: AsyncSession, worker_id: str) -> bool:
    """Delete a worker."""
    worker = await get_worker(db, worker_id)
    if worker is None:
        return False
    await db.delete(worker)
    await db.commit()
    # audit: skip duplication
    logger.info("Worker deleted: %s", worker_id)
    log_activity(
        level="info",
        event_type="worker_deleted",
        message=f"Worker {worker_id} deleted",
        worker_id=worker_id
    )
    return True
