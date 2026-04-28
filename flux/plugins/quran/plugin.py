"""Quran Shorts plugin — Phase 2: Fetch implementation.

Downloads Quran Shorts from YouTube channels and background images
from Pexels/Unsplash. All ingredients enter the pipeline as pending
for operator approval.
"""

from __future__ import annotations

from typing import Any

from flux.logger import get_logger
from flux.plugins.base import ContentPlugin, RenderResult

from .backgrounds import fetch_backgrounds
from .config import CONFIG_SCHEMA, DEFAULT_CONFIG
from .fetch import fetch_clips
from .render import render_from_ingredients

logger = get_logger(__name__)


def _deep_merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge overrides into defaults. Dicts are merged recursively; other types are replaced."""
    result = dict(defaults)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class QuranPlugin(ContentPlugin):
    """Quran Shorts content plugin for Flux."""

    @property
    def name(self) -> str:
        return "quran_shorts"

    @property
    def display_name(self) -> str:
        return "Quran Shorts"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def ingredient_types(self) -> list[str]:
        return ["quran_clip", "bg_image", "bg_video"]

    async def fetch(
        self, pipeline_id: str, config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Fetch new Quran clips and background images.

        Downloads Shorts from configured YouTube channels and background
        images from Pexels/Unsplash. Returns ingredient metadata dicts
        for the core engine to persist.

        Each dict contains:
            - type: "quran_clip" | "bg_image"
            - file_path: absolute path to downloaded file
            - source_url: original URL
            - metadata: dict with source-specific info
            - file_size_bytes: int | None
            - duration_secs: float | None
        """
        # Merge with defaults so missing keys don't crash
        cfg = _deep_merge(DEFAULT_CONFIG, config)

        max_clips = cfg.get("max_clips_per_fetch", 10)
        max_bg = cfg.get("max_backgrounds_per_fetch", 20)
        channels = cfg.get("source_channels", [])
        bg_cfg = cfg.get("bg_sources", {})

        ingredients: list[dict[str, Any]] = []
        clips: list[dict[str, Any]] = []
        backgrounds: list[dict[str, Any]] = []

        # 1. Fetch Quran clips
        if channels:
            try:
                clips = await fetch_clips(pipeline_id, channels, max_clips=max_clips)
                ingredients.extend(clips)
            except Exception as e:
                logger.error("Clip fetch failed for pipeline %s: %s", pipeline_id, e)
        else:
            logger.warning("No source_channels configured for pipeline %s", pipeline_id)

        # 2. Fetch background images
        pexels_kw = bg_cfg.get("pexels_keywords", [])
        unsplash_kw = bg_cfg.get("unsplash_keywords", [])
        blocklist = bg_cfg.get("blocklist", [])
        if pexels_kw or unsplash_kw:
            try:
                backgrounds = await fetch_backgrounds(
                    pipeline_id,
                    pexels_keywords=pexels_kw,
                    unsplash_keywords=unsplash_kw,
                    max_total=max_bg,
                    blocklist=blocklist,
                )
                ingredients.extend(backgrounds)
            except Exception as e:
                logger.error("Background fetch failed for pipeline %s: %s", pipeline_id, e)
        else:
            logger.warning("No background keywords configured for pipeline %s", pipeline_id)

        logger.info(
            "QuranPlugin.fetch complete for pipeline %s: %d ingredients (%d clips, %d backgrounds)",
            pipeline_id,
            len(ingredients),
            len(clips),
            len(backgrounds),
        )
        return ingredients

    async def render(
        self,
        pipeline_id: str,
        ingredient_ids: list[str],
        config: dict[str, Any],
    ) -> RenderResult:
        """Compose final video from approved ingredients."""
        logger.info(
            "QuranPlugin.render called for pipeline %s with %d ingredients",
            pipeline_id,
            len(ingredient_ids),
        )

        # Resolve ingredient file paths from config (injected by core engine)
        # or fall back to DB query for direct calls.
        render_ingredients = config.get("_render_ingredients", {})
        clip_path: str | None = render_ingredients.get("clip_path")
        bg_paths: list[str] = render_ingredients.get("bg_paths", [])

        if not clip_path or not bg_paths:
            from flux.db import AsyncSessionLocal
            from flux.models import Ingredient
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Ingredient).where(
                        Ingredient.id.in_(ingredient_ids),
                        Ingredient.pipeline_id == pipeline_id,
                        Ingredient.status == "approved",
                    )
                )
                ingredients = result.scalars().all()

                for ing in ingredients:
                    if ing.type == "quran_clip" and ing.file_path:
                        clip_path = ing.file_path
                    elif ing.type in ("bg_image", "bg_video") and ing.file_path:
                        bg_paths.append(ing.file_path)

        if not clip_path:
            logger.error("No approved quran_clip found among ingredients for pipeline %s", pipeline_id)
            return RenderResult(
                file_path=None,
                caption="",
                metadata={"error": "no_clip", "pipeline_id": pipeline_id},
            )

        if not bg_paths:
            logger.error("No approved backgrounds found among ingredients for pipeline %s", pipeline_id)
            return RenderResult(
                file_path=None,
                caption="",
                metadata={"error": "no_background", "pipeline_id": pipeline_id},
            )

        try:
            result = await render_from_ingredients(clip_path, bg_paths, config)
        except Exception as e:
            logger.error("Render failed for pipeline %s: %s", pipeline_id, e)
            return RenderResult(
                file_path=None,
                caption="",
                metadata={"error": str(e), "pipeline_id": pipeline_id},
            )

        return RenderResult(
            file_path=result["file_path"],
            thumbnail_path=result["thumbnail_path"],
            caption="",
            metadata=result["metadata"],
        )

    async def identify_content(
        self,
        pipeline_id: str,
        produced_content_id: str,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Identify verse reference from rendered content. (Phase 4)"""
        logger.info("QuranPlugin.identify_content called (Phase 4 stub)")
        return None

    async def build_caption(
        self,
        pipeline_id: str,
        produced_content_id: str,
        config: dict[str, Any],
        worker_config: dict[str, Any],
    ) -> str:
        """Generate caption for a specific platform worker. (Phase 4)"""
        logger.info("QuranPlugin.build_caption called (Phase 4 stub)")
        return ""

    def get_config_schema(self) -> dict[str, Any]:
        """Return JSONSchema for pipeline configuration."""
        return CONFIG_SCHEMA
