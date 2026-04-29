"""Production API endpoints — generated videos and artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from flux.core import production as production_service
from flux.core.pipeline import get_pipeline
from flux.db import get_db
from flux.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/pipelines", tags=["production"])


def _serialize_production(p) -> dict[str, Any]:
    return {
        "id": p.id,
        "pipeline_id": p.pipeline_id,
        "ingredient_ids": json.loads(p.ingredient_ids_json) if p.ingredient_ids_json else [],
        "render_method": p.render_method,
        "file_path": p.file_path,
        "thumbnail_path": p.thumbnail_path,
        "content_meta": json.loads(p.content_meta_json) if p.content_meta_json else {},
        "caption_text": p.caption_text,
        "status": p.status,
        "render_log": p.render_log,
        "rendered_at": p.rendered_at.isoformat() if p.rendered_at else None,
        "ready_at": p.ready_at.isoformat() if p.ready_at else None,
    }


@router.get("/{pipeline_id}/production")
async def list_produced_content(
    pipeline_id: str,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List produced content for a specific pipeline."""
    pipeline = await get_pipeline(db, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    items = await production_service.list_produced_content(
        db, pipeline_id=pipeline_id, status=status, limit=limit, offset=offset
    )
    return [_serialize_production(item) for item in items]


@router.get("/{pipeline_id}/production/{content_id}")
async def get_produced_content(
    pipeline_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get details of a specific produced content item."""
    item = await production_service.get_produced_content(db, content_id)
    if item is None or item.pipeline_id != pipeline_id:
        raise HTTPException(status_code=404, detail="Produced content not found")
    
    return _serialize_production(item)


@router.post("/{pipeline_id}/production/{content_id}/identify")
async def update_production_metadata(
    pipeline_id: str,
    content_id: str,
    data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually update metadata (e.g. verse ID) for content."""
    item = await production_service.get_produced_content(db, content_id)
    if item is None or item.pipeline_id != pipeline_id:
        raise HTTPException(status_code=404, detail="Produced content not found")

    # If surah and ayah are provided, mark as ready
    success = bool(data.get("surah") and data.get("ayah"))
    
    updated = await production_service.update_identification_result(
        db, content_id, success=success, metadata=data
    )
    return _serialize_production(updated)


@router.get("/{pipeline_id}/production/{content_id}/stream")
async def stream_produced_content(
    pipeline_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Stream the rendered MP4 video file."""
    item = await production_service.get_produced_content(db, content_id)
    if item is None or item.pipeline_id != pipeline_id:
        raise HTTPException(status_code=404, detail="Produced content not found")
        
    if not item.file_path or not Path(item.file_path).exists():
        raise HTTPException(status_code=404, detail="Rendered video file not found on disk")
        
    # FileResponse handles range requests automatically in Starlette/FastAPI
    return FileResponse(
        path=item.file_path,
        media_type="video/mp4",
        filename=Path(item.file_path).name,
        headers={"Accept-Ranges": "bytes"}
    )
