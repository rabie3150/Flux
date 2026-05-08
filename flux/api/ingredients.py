"""Ingredient API endpoints — list, approve, reject, delete."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
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
    limit: int = Query(200, ge=1, le=1000),
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
    count = await ingredient_service.approve_ingredients(db, pipeline_id, req.ingredient_ids)
    logger.info("Approved %d ingredients for pipeline %s", count, pipeline_id)
    return {"approved": count, "ingredient_ids": req.ingredient_ids}


@router.post("/api/pipelines/{pipeline_id}/ingredients/reject")
async def reject_ingredients(
    pipeline_id: str,
    req: BulkIdRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reject ingredients by ID."""
    count = await ingredient_service.reject_ingredients(db, pipeline_id, req.ingredient_ids)
    logger.info("Rejected %d ingredients for pipeline %s", count, pipeline_id)
    return {"rejected": count, "ingredient_ids": req.ingredient_ids}


@router.delete("/api/pipelines/{pipeline_id}/ingredients")
async def delete_ingredients(
    pipeline_id: str,
    req: BulkIdRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Physically delete ingredients."""
    count = await ingredient_service.delete_ingredients(db, pipeline_id, req.ingredient_ids)
    logger.info("Deleted %d ingredients for pipeline %s", count, pipeline_id)
    return {"deleted": count, "ingredient_ids": req.ingredient_ids}


@router.get("/api/pipelines/{pipeline_id}/ingredients/{ingredient_id}")
async def get_ingredient(
    pipeline_id: str,
    ingredient_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a single ingredient by ID."""
    from sqlalchemy import select
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.pipeline_id == pipeline_id
        )
    )
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return _serialize_ingredient(ingredient)



from fastapi.responses import FileResponse
from pathlib import Path
from fastapi import HTTPException

@router.get("/api/pipelines/{pipeline_id}/ingredients/{ingredient_id}/preview")
async def preview_ingredient(
    pipeline_id: str,
    ingredient_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Stream an ingredient file for preview in the admin panel."""
    from flux.models import Ingredient
    from sqlalchemy import select
    
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id == ingredient_id, 
            Ingredient.pipeline_id == pipeline_id
        )
    )
    ingredient = result.scalar_one_or_none()
    
    if not ingredient or not ingredient.file_path:
        raise HTTPException(status_code=404, detail="Ingredient file not found")
        
    file_path = Path(ingredient.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing from disk")
        
    media_type = "video/mp4" if file_path.suffix.lower() in (".mp4", ".mov", ".webm") else "image/jpeg"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        headers={"Accept-Ranges": "bytes"}
    )
