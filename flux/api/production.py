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
from flux.models import VerseCache
from flux.plugins.quran.api import VerseService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/pipelines", tags=["production"])


def _verse_ref(meta: dict[str, Any]) -> str:
    surah = meta.get("surah")
    ayah = meta.get("ayah")
    ayah_end = meta.get("ayah_end")
    if not surah or not ayah:
        return "Unknown verse"
    if ayah_end and ayah_end > ayah:
        return f"{surah}:{ayah}-{ayah_end}"
    return f"{surah}:{ayah}"


async def _detected_verses(db: AsyncSession, meta: dict[str, Any]) -> dict[str, Any] | None:
    surah = meta.get("surah")
    ayah = meta.get("ayah")
    ayah_end = meta.get("ayah_end") or ayah
    if not surah or not ayah:
        return None

    rows_by_ayah = {}
    for ayah_number in range(int(ayah), int(ayah_end) + 1):
        result = await db.get(VerseCache, {"surah_number": int(surah), "ayah_number": ayah_number})
        if result:
            rows_by_ayah[ayah_number] = result

    translations = []
    arabic = []
    verses = []
    service = VerseService()
    for ayah_number in range(int(ayah), int(ayah_end) + 1):
        row = rows_by_ayah.get(ayah_number)
        if not row:
            try:
                verse_data = await service.get_verse(int(surah), ayah_number)
                if verse_data:
                    arabic_text = verse_data.get("arabic", "")
                    translation = verse_data.get("translation", "")
                    arabic.append(arabic_text)
                    translations.append(translation)
                    verses.append({
                        "ref": f"{surah}:{ayah_number}",
                        "surah": surah,
                        "ayah": ayah_number,
                        "arabic": arabic_text,
                        "translation": translation,
                    })
                continue
            except Exception as exc:
                logger.warning("Verse text lookup failed for %s:%s: %s", surah, ayah_number, exc)
                continue

        arabic_text = row.arabic_text or ""
        payload = json.loads(row.translations_json or "{}")
        translation = next(iter(payload.values()), "")
        arabic.append(arabic_text)
        translations.append(translation)
        verses.append({
            "ref": f"{surah}:{row.ayah_number}",
            "surah": surah,
            "ayah": row.ayah_number,
            "arabic": arabic_text,
            "translation": translation,
        })

    return {
        "ref": _verse_ref(meta),
        "surah": surah,
        "surah_name": meta.get("surah_name"),
        "ayah": ayah,
        "ayah_end": ayah_end if ayah_end != ayah else None,
        "verses": verses,
        "arabic": " ".join(text for text in arabic if text),
        "translation": " ".join(text for text in translations if text),
    }


async def _serialize_production(db: AsyncSession, p) -> dict[str, Any]:
    content_meta = json.loads(p.content_meta_json) if p.content_meta_json else {}
    return {
        "id": p.id,
        "pipeline_id": p.pipeline_id,
        "ingredient_ids": json.loads(p.ingredient_ids_json) if p.ingredient_ids_json else [],
        "render_method": p.render_method,
        "file_path": p.file_path,
        "thumbnail_path": p.thumbnail_path,
        "content_meta": content_meta,
        "detected_verses": await _detected_verses(db, content_meta),
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
    return [await _serialize_production(db, item) for item in items]


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
    
    return await _serialize_production(db, item)


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
    metadata = dict(data)
    if success:
        metadata["identified_by"] = "manual"
        metadata["manual_override"] = True
        if not metadata.get("ayah_end"):
            existing = json.loads(item.content_meta_json or "{}")
            existing.pop("ayah_end", None)
            item.content_meta_json = json.dumps(existing)
    
    updated = await production_service.update_identification_result(
        db, content_id, success=success, metadata=metadata
    )
    return await _serialize_production(db, updated)


@router.post("/{pipeline_id}/production/{content_id}/redo-ai")
async def redo_ai_identification(
    pipeline_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Re-run the AI identification process for a produced content item."""
    from flux.core.pipeline import identify_produced_content
    
    item = await production_service.get_produced_content(db, content_id)
    if item is None or item.pipeline_id != pipeline_id:
        raise HTTPException(status_code=404, detail="Produced content not found")

    try:
        result = await identify_produced_content(db, content_id)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error") or result.get("reason", "Identification failed"))
        
        # Fetch the updated item to return
        updated = await production_service.get_produced_content(db, content_id)
        return await _serialize_production(db, updated)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

@router.post("/{pipeline_id}/production/{content_id}/requeue")
async def requeue_produced_content(
    pipeline_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Requeue a produced content item that failed to render or post."""
    item = await production_service.get_produced_content(db, content_id)
    if item is None or item.pipeline_id != pipeline_id:
        raise HTTPException(status_code=404, detail="Produced content not found")
        
    # Reset status to pending so it can be re-rendered or re-identified
    item.status = "pending"
    item.render_log = None
    item.caption_text = None
    item.content_meta_json = json.dumps({})
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return await _serialize_production(db, item)

@router.delete("/{pipeline_id}/production/{content_id}")
async def delete_produced_content(
    pipeline_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a produced content item and its files."""
    item = await production_service.get_produced_content(db, content_id)
    if item is None or item.pipeline_id != pipeline_id:
        raise HTTPException(status_code=404, detail="Produced content not found")
        
    if item.file_path and Path(item.file_path).exists():
        Path(item.file_path).unlink()
    if item.thumbnail_path and Path(item.thumbnail_path).exists():
        Path(item.thumbnail_path).unlink()
        
    await db.delete(item)
    await db.commit()
    return {"deleted": True, "id": content_id}

