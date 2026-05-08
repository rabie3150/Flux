"""Prometheus-compatible metrics endpoint."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.db import get_db
from flux.models import Ingredient, PlatformWorker, PostRecord, ProducedContent

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("", response_class=PlainTextResponse)
async def get_metrics(db: AsyncSession = Depends(get_db)) -> str:
    """Return system metrics in Prometheus exposition format."""
    lines: list[str] = []

    def _add_metric(name: str, value: Any, type_val: str, help_text: str, labels: dict[str, str] | None = None) -> None:
        if name not in [line.split(" ")[1] for line in lines if line.startswith("# HELP")]:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {type_val}")
        
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
            lines.append(f"{name}{{{label_str}}} {value}")
        else:
            lines.append(f"{name} {value}")

    # 1. Post Metrics
    post_res = await db.execute(
        select(PostRecord.status, func.count(PostRecord.id)).group_by(PostRecord.status)
    )
    for row in post_res.all():
        _add_metric(
            "flux_posts_total",
            row[1],
            "counter",
            "Total number of post attempts by status",
            {"status": row[0]},
        )

    # 2. Render Metrics
    render_res = await db.execute(
        select(ProducedContent.status, func.count(ProducedContent.id)).group_by(ProducedContent.status)
    )
    for row in render_res.all():
        _add_metric(
            "flux_renders_total",
            row[1],
            "counter",
            "Total number of produced content items by status",
            {"status": row[0]},
        )

    # 3. Ingredients Metrics
    ing_res = await db.execute(
        select(Ingredient.status, func.count(Ingredient.id)).group_by(Ingredient.status)
    )
    for row in ing_res.all():
        _add_metric(
            "flux_ingredients_total",
            row[1],
            "gauge",
            "Current stock of ingredients by status",
            {"status": row[0]},
        )

    # 4. Storage Metrics
    from flux.core.storage import get_storage_budget
    try:
        budget = get_storage_budget()
        _add_metric(
            "flux_storage_used_bytes",
            budget.used_bytes,
            "gauge",
            "Total disk space used by Flux data",
        )
        _add_metric(
            "flux_storage_budget_bytes",
            budget.total_budget_bytes,
            "gauge",
            "Configured maximum storage budget for Flux",
        )
    except Exception:
        pass

    # 5. Worker Metrics
    workers_res = await db.execute(
        select(PlatformWorker.enabled, func.count(PlatformWorker.id)).group_by(PlatformWorker.enabled)
    )
    for row in workers_res.all():
        status = "enabled" if row[0] else "disabled"
        _add_metric(
            "flux_workers_active",
            row[1],
            "gauge",
            "Number of configured platform workers",
            {"state": status},
        )

    # Output formatted string with trailing newline
    return "\n".join(lines) + "\n"
