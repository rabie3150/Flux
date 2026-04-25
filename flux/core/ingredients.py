"""Ingredient service — fetch results, approval gates, stock levels."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.models import Ingredient


async def list_ingredients(
    db: AsyncSession,
    pipeline_id: str,
    type_filter: str | None = None,
    status_filter: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[Ingredient]:
    """List ingredients for a pipeline with optional filters."""
    stmt = select(Ingredient).where(Ingredient.pipeline_id == pipeline_id)

    if type_filter:
        stmt = stmt.where(Ingredient.type == type_filter)
    if status_filter:
        stmt = stmt.where(Ingredient.status == status_filter)

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
        status="pending",
    )
    db.add(ingredient)
    await db.commit()
    await db.refresh(ingredient)
    return ingredient


async def approve_ingredients(
    db: AsyncSession, ingredient_ids: list[str]
) -> int:
    """Approve ingredients by ID. Returns count approved."""
    result = await db.execute(
        select(Ingredient).where(Ingredient.id.in_(ingredient_ids))
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
    return count


async def reject_ingredients(
    db: AsyncSession, ingredient_ids: list[str]
) -> int:
    """Reject ingredients by ID. Returns count rejected."""
    result = await db.execute(
        select(Ingredient).where(Ingredient.id.in_(ingredient_ids))
    )
    ingredients = result.scalars().all()
    count = 0
    for ing in ingredients:
        if ing.status == "pending":
            ing.status = "rejected"
            count += 1
    if count:
        await db.commit()
    return count


async def delete_ingredients(
    db: AsyncSession, ingredient_ids: list[str]
) -> int:
    """Physically delete ingredients. Returns count deleted."""
    result = await db.execute(
        select(Ingredient).where(Ingredient.id.in_(ingredient_ids))
    )
    ingredients = result.scalars().all()
    count = len(ingredients)
    for ing in ingredients:
        await db.delete(ing)
    if count:
        await db.commit()
    return count


async def count_ingredients(
    db: AsyncSession,
    pipeline_id: str,
    type: str | None = None,
    status: str | None = None,
) -> int:
    """Count ingredients matching criteria."""
    stmt = select(func.count(Ingredient.id)).where(
        Ingredient.pipeline_id == pipeline_id
    )
    if type:
        stmt = stmt.where(Ingredient.type == type)
    if status:
        stmt = stmt.where(Ingredient.status == status)
    result = await db.execute(stmt)
    return result.scalar_one()
