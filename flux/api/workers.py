"""Platform Worker API endpoints — CRUD for social media accounts."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from flux.core import workers as worker_service
from flux.core.publish import publish_for_worker
from flux.core.scheduler_jobs import refresh_worker_job, remove_worker_job
from flux.db import get_db
from flux.logger import get_logger
from flux.models import PlatformWorker

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workers", tags=["workers"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WorkerCreate(BaseModel):
    platform: str = Field(..., min_length=1, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=128)
    connection_strategy: str = Field(default="official", max_length=32)
    third_party_provider: str | None = Field(default=None, max_length=32)
    credentials: dict[str, Any] = Field(default_factory=dict)
    schedule_cron: str | None = Field(default=None, max_length=64)
    caption_template_override: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    enabled: bool = True


class WorkerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    connection_strategy: str | None = Field(default=None, max_length=32)
    third_party_provider: str | None = Field(default=None, max_length=32)
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
        "connection_strategy": w.connection_strategy,
        "third_party_provider": w.third_party_provider,
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
    workers = await worker_service.list_workers(db)
    return [_serialize_worker(w) for w in workers]


@router.post("", status_code=201)
async def create_worker(
    data: WorkerCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new platform worker."""
    worker = await worker_service.create_worker(
        db,
        platform=data.platform,
        display_name=data.display_name,
        credentials=data.credentials,
        connection_strategy=data.connection_strategy,
        third_party_provider=data.third_party_provider,
        schedule_cron=data.schedule_cron,
        caption_template_override=data.caption_template_override,
        hashtags=data.hashtags,
        enabled=data.enabled,
    )
    logger.info("Worker created: %s", worker.id)
    await refresh_worker_job(worker.id)
    return _serialize_worker(worker)


@router.get("/{worker_id}")
async def get_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get worker details."""
    worker = await worker_service.get_worker(db, worker_id)
    if worker is None:
        logger.warning("Worker not found: %s", worker_id)
        raise HTTPException(status_code=404, detail="Worker not found")
    return _serialize_worker(worker)


@router.put("/{worker_id}")
async def update_worker(
    worker_id: str,
    data: WorkerUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update a worker (partial update)."""
    worker = await worker_service.update_worker(
        db,
        worker_id,
        display_name=data.display_name,
        credentials=data.credentials,
        connection_strategy=data.connection_strategy,
        third_party_provider=data.third_party_provider,
        schedule_cron=data.schedule_cron,
        caption_template_override=data.caption_template_override,
        hashtags=data.hashtags,
        enabled=data.enabled,
    )
    if worker is None:
        logger.warning("Worker not found for update: %s", worker_id)
        raise HTTPException(status_code=404, detail="Worker not found")

    logger.info("Worker updated: %s", worker_id)
    await refresh_worker_job(worker_id)
    return _serialize_worker(worker)


@router.delete("/{worker_id}")
async def delete_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a platform worker."""
    deleted = await worker_service.delete_worker(db, worker_id)
    if not deleted:
        logger.warning("Worker not found for delete: %s", worker_id)
        raise HTTPException(status_code=404, detail="Worker not found")

    logger.info("Worker deleted: %s", worker_id)
    await remove_worker_job(worker_id)
    return {"deleted": worker_id}


@router.post("/{worker_id}/test")
async def test_worker_credentials(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dry-run credential validation for a worker."""
    worker = await worker_service.get_worker(db, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    from flux.core.crypto import decrypt_dict
    from flux.platforms.publisher import get_publisher

    try:
        credentials = decrypt_dict(worker.credentials_json)
    except Exception as exc:
        return {"ok": False, "error": f"Failed to decrypt credentials: {exc}"}

    publisher = get_publisher(worker.platform, worker.connection_strategy, credentials)
    if publisher is None:
        return {"ok": False, "error": f"No publisher found for {worker.platform}/{worker.connection_strategy}"}

    # If the publisher has a test method, use it; otherwise fall back to basic validation
    if hasattr(publisher, "test"):
        test_result = await publisher.test()
        return test_result

    # Basic validation: ensure required credential fields are present
    required_map = {
        ("youtube", "official"): ["client_id", "client_secret", "refresh_token"],
        ("instagram", "official"): ["app_id", "app_secret", "access_token", "instagram_account_id"],
        ("instagram", "unofficial"): ["username", "password"],
        ("x", "official"): ["api_key", "api_secret", "access_token", "access_token_secret"],
        ("tiktok", "official"): ["app_id", "app_secret", "access_token"],
    }
    required = required_map.get((worker.platform, worker.connection_strategy))
    if required:
        missing = [k for k in required if not credentials.get(k)]
        if missing:
            return {"ok": False, "error": f"Missing credentials: {', '.join(missing)}"}

    return {"ok": True, "message": "Credentials appear valid (basic check)"}


@router.post("/{worker_id}/post")
async def trigger_worker_post(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually trigger a post attempt for a worker."""
    worker = await worker_service.get_worker(db, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    result = await publish_for_worker(worker_id)
    if not result.get("ok"):
        # Bad publisher config = 400, transient failure = 503, other = 500
        status_code = 400 if not result.get("transient") and "Invalid publisher config" in result.get("error", "") else 503 if result.get("transient") else 500
        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "Post failed"),
        )
    return result
