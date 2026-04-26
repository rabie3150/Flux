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

logger = get_logger(__name__)


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
        cfg = {**DEFAULT_CONFIG, **config}

        max_clips = cfg.get("max_clips_per_fetch", 10)
        max_bg = cfg.get("max_backgrounds_per_fetch", 20)
        channels = cfg.get("source_channels", [])
        bg_cfg = cfg.get("bg_sources", {})

        ingredients: list[dict[str, Any]] = []

        # 1. Fetch Quran clips
        if channels:
            clips = await fetch_clips(pipeline_id, channels, max_clips=max_clips)
            ingredients.extend(clips)
        else:
            logger.warning("No source_channels configured for pipeline %s", pipeline_id)

        # 2. Fetch background images
        pexels_kw = bg_cfg.get("pexels_keywords", [])
        unsplash_kw = bg_cfg.get("unsplash_keywords", [])
        if pexels_kw or unsplash_kw:
            backgrounds = await fetch_backgrounds(
                pipeline_id,
                pexels_keywords=pexels_kw,
                unsplash_keywords=unsplash_kw,
                max_total=max_bg,
            )
            ingredients.extend(backgrounds)
        else:
            logger.warning("No background keywords configured for pipeline %s", pipeline_id)

        logger.info(
            "QuranPlugin.fetch complete for pipeline %s: %d ingredients (%d clips, %d backgrounds)",
            pipeline_id,
            len(ingredients),
            len(clips) if channels else 0,
            len(backgrounds) if (pexels_kw or unsplash_kw) else 0,
        )
        return ingredients

    async def render(
        self,
        pipeline_id: str,
        ingredient_ids: list[str],
        config: dict[str, Any],
    ) -> RenderResult:
        """Compose final video from approved ingredients. (Phase 3)"""
        logger.info("QuranPlugin.render called for pipeline %s (Phase 3 stub)", pipeline_id)
        return RenderResult(
            file_path=None,
            caption="",
            metadata={"pipeline_id": pipeline_id, "ingredient_ids": ingredient_ids},
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
