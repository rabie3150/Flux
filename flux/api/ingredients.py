"""Ingredient API endpoints — list, approve, reject, delete."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from flux.core import ingredients as ingredient_service
from flux.db import get_db
from flux.logger import get_logger
from flux.models import Ingredient

logger = get_logger(__name__)

router = APIRouter(tags=["ingredients"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class BulkIdRequest(BaseModel):
    ingredient_ids: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_ingredient(i: Ingredient) -> dict[str, Any]:
    return {
        "id": i.id,
        "pipeline_id": i.pipeline_id,
        "type": i.type,
        "file_path": i.file_path,
        "source_url": i.source_url,
        "metadata_json": i.metadata_json,
        "status": i.status,
        "approved_at": i.approved_at.isoformat() if i.approved_at else None,
        "file_size_bytes": i.file_size_bytes,
        "duration_secs": i.duration_secs,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/api/pipelines/{pipeline_id}/ingredients")
async def list_ingredients(
    pipeline_id: str,
    type: str | None = None,
    status: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List ingredients for a pipeline with optional filters."""
    ingredients = await ingredient_service.list_ingredients(
        db, pipeline_id, type_filter=type, status_filter=status, limit=limit, offset=offset
    )
    return {
        "pipeline_id": pipeline_id,
        "limit": limit,
        "offset": offset,
        "count": len(ingredients),
        "ingredients": [_serialize_ingredient(i) for i in ingredients],
    }


@router.post("/api/pipelines/{pipeline_id}/ingredients/approve")
async def approve_ingredients(
    pipeline_id: str,
    req: BulkIdRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approve ingredients by ID."""
    count = await ingredient_service.approve_ingredients(db, req.ingredient_ids)
    logger.info("Approved %d ingredients for pipeline %s", count, pipeline_id)
    return {"approved": count, "ingredient_ids": req.ingredient_ids}


@router.post("/api/pipelines/{pipeline_id}/ingredients/reject")
async def reject_ingredients(
    pipeline_id: str,
    req: BulkIdRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reject ingredients by ID."""
    count = await ingredient_service.reject_ingredients(db, req.ingredient_ids)
    logger.info("Rejected %d ingredients for pipeline %s", count, pipeline_id)
    return {"rejected": count, "ingredient_ids": req.ingredient_ids}


@router.delete("/api/pipelines/{pipeline_id}/ingredients")
async def delete_ingredients(
    pipeline_id: str,
    req: BulkIdRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Physically delete ingredients."""
    count = await ingredient_service.delete_ingredients(db, req.ingredient_ids)
    logger.info("Deleted %d ingredients for pipeline %s", count, pipeline_id)
    return {"deleted": count, "ingredient_ids": req.ingredient_ids}
