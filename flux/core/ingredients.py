"""Ingredient service — fetch results, approval gates, stock levels."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataclasses import dataclass
from flux.logger import get_logger, log_activity
from flux.models import Ingredient

logger = get_logger(__name__)


@dataclass
class StockLevel:
    """Represents current stock for a specific ingredient type."""
    type: str
    approved_unused: int
    pending: int
    total_active: int  # pending + approved
    is_low: bool
    is_maxed: bool



async def list_ingredients(
    db: AsyncSession,
    pipeline_id: str,
    type_filter: str | None = None,
    status_filter: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[Ingredient]:
    """List ingredients for a pipeline with optional filters.
    
    By default, hides ingredients with status 'dropped' unless explicitly requested.
    """
    stmt = select(Ingredient).where(Ingredient.pipeline_id == pipeline_id)

    if type_filter:
        stmt = stmt.where(Ingredient.type == type_filter)
        
    if status_filter:
        stmt = stmt.where(Ingredient.status == status_filter)
    else:
        # Exclude dropped items from general listings
        stmt = stmt.where(Ingredient.status != "dropped")

    stmt = stmt.order_by(Ingredient.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_ingredient(db: AsyncSession, ingredient_id: str) -> Ingredient | None:
    """Fetch a single ingredient by ID."""
    result = await db.execute(
        select(Ingredient).where(Ingredient.id == ingredient_id)
    )
    return result.scalar_one_or_none()


async def create_ingredient(
    db: AsyncSession,
    pipeline_id: str,
    type: str,
    file_path: str | None = None,
    source_url: str | None = None,
    metadata: dict[str, Any] | None = None,
    file_size_bytes: int | None = None,
    duration_secs: float | None = None,
    status: str = "pending",
) -> Ingredient:
    """Insert a new ingredient (typically called by plugin fetch)."""
    ingredient = Ingredient(
        pipeline_id=pipeline_id,
        type=type,
        file_path=file_path,
        source_url=source_url,
        metadata_json=json.dumps(metadata) if metadata else None,
        file_size_bytes=file_size_bytes,
        duration_secs=duration_secs,
        status=status,
    )
    db.add(ingredient)
    await db.commit()
    await db.refresh(ingredient)
    logger.info("Ingredient created: %s (%s) for pipeline %s", ingredient.type, ingredient.id, pipeline_id)
    log_activity(
        level="info",
        event_type="ingredient_created",
        message=f"Ingredient {type} created for pipeline {pipeline_id}",
        pipeline_id=pipeline_id
    )
    return ingredient


async def approve_ingredients(
    db: AsyncSession, pipeline_id: str, ingredient_ids: list[str]
) -> int:
    """Approve ingredients by ID for a specific pipeline. Returns count approved."""
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id.in_(ingredient_ids),
            Ingredient.pipeline_id == pipeline_id,
        )
    )
    ingredients = result.scalars().all()
    now = datetime.now(timezone.utc)
    count = 0
    for ing in ingredients:
        if ing.status == "pending":
            ing.status = "approved"
            ing.approved_at = now
            count += 1
    if count:
        await db.commit()
        # audit: skip duplication
        logger.info("Approved %d ingredients", count)
        log_activity(
            level="info",
            event_type="ingredients_approved",
            message=f"Approved {count} ingredients",
        )
    return count


async def reject_ingredients(
    db: AsyncSession, pipeline_id: str, ingredient_ids: list[str]
) -> int:
    """Reject ingredients by ID for a specific pipeline. Returns count rejected."""
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id.in_(ingredient_ids),
            Ingredient.pipeline_id == pipeline_id,
        )
    )
    ingredients = result.scalars().all()
    count = 0
    for ing in ingredients:
        if ing.status == "pending":
            ing.status = "rejected"
            count += 1
    if count:
        await db.commit()
        # audit: skip duplication
        logger.info("Rejected %d ingredients", count)
        log_activity(
            level="info",
            event_type="ingredients_rejected",
            message=f"Rejected {count} ingredients",
        )
    return count


async def delete_ingredients(
    db: AsyncSession, pipeline_id: str, ingredient_ids: list[str]
) -> int:
    """Physically delete ingredients and their files. Returns count deleted."""
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id.in_(ingredient_ids),
            Ingredient.pipeline_id == pipeline_id,
        )
    )
    ingredients = list(result.scalars().all())
    count = len(ingredients)
    for ing in ingredients:
        await db.delete(ing)
    if count:
        await db.commit()
        # audit: skip duplication
        logger.info("Deleted %d ingredients", count)
        log_activity(
            level="info",
            event_type="ingredients_deleted",
            message=f"Deleted {count} ingredients",
        )
    # Delete files *after* successful commit so DB stays consistent
    for ing in ingredients:
        if ing.file_path and os.path.exists(ing.file_path):
            try:
                os.unlink(ing.file_path)
            except OSError as e:
                logger.warning("Failed to delete file %s: %s", ing.file_path, e)
    return count


async def get_unused_approved_ingredients(
    db: AsyncSession,
    pipeline_id: str,
) -> list[Ingredient]:
    """Return all approved ingredients that haven't been used in produced content yet."""
    from flux.models import ProducedContent

    # 1. Get all approved ingredients for this pipeline
    stmt = select(Ingredient).where(
        Ingredient.pipeline_id == pipeline_id,
        Ingredient.status == "approved"
    )
    res = await db.execute(stmt)
    approved = list(res.scalars().all())
    
    # 2. Find which IDs have already been used
    stmt = select(ProducedContent.ingredient_ids_json).where(
        ProducedContent.pipeline_id == pipeline_id
    )
    res = await db.execute(stmt)
    used_ids = set()
    for row in res.all():
        if row[0]:
            try:
                ids = json.loads(row[0])
                if isinstance(ids, list):
                    used_ids.update(ids)
            except Exception as e:
                logger.warning("Failed to parse ingredient_ids_json for content row: %s", e)
    # 3. Filter
    return [i for i in approved if i.id not in used_ids]


async def count_ingredients(
    db: AsyncSession,
    pipeline_id: str,
    ingredient_type: str | None = None,
    status: str | None = None,
) -> int:
    """Count ingredients matching criteria."""
    stmt = select(func.count(Ingredient.id)).where(
        Ingredient.pipeline_id == pipeline_id
    )
    if ingredient_type:
        stmt = stmt.where(Ingredient.type == ingredient_type)
    if status:
        stmt = stmt.where(Ingredient.status == status)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_stock_level(
    db: AsyncSession,
    pipeline_id: str,
    ingredient_type: str,
    low_threshold: int = 5,
    max_threshold: int = 50,
) -> StockLevel:
    """Evaluate current stock levels for a specific ingredient type."""
    # Count pending
    pending = await count_ingredients(db, pipeline_id, ingredient_type, "pending")
    
    # Count approved and unused
    from flux.models import ProducedContent
    
    stmt_approved = select(Ingredient.id).where(
        Ingredient.pipeline_id == pipeline_id,
        Ingredient.type == ingredient_type,
        Ingredient.status == "approved"
    )
    res_app = await db.execute(stmt_approved)
    approved_ids = {row[0] for row in res_app.all()}
    
    stmt_used = select(ProducedContent.ingredient_ids_json).where(
        ProducedContent.pipeline_id == pipeline_id
    )
    res_used = await db.execute(stmt_used)
    used_ids = set()
    for row in res_used.all():
        if row[0]:
            try:
                ids = json.loads(row[0])
                if isinstance(ids, list):
                    used_ids.update(ids)
            except Exception:
                pass
                
    approved_unused = len(approved_ids - used_ids)
    total_active = pending + approved_unused
    
    return StockLevel(
        type=ingredient_type,
        approved_unused=approved_unused,
        pending=pending,
        total_active=total_active,
        is_low=total_active <= low_threshold,
        is_maxed=total_active >= max_threshold,
    )
