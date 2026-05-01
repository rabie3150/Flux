"""Quran Shorts plugin implementation."""

from __future__ import annotations

import json
import random
from typing import Any

from jinja2 import Template
from sqlalchemy import select

from flux.db import AsyncSessionLocal
from flux.logger import get_logger
from flux.models import Ingredient, ProducedContent
from flux.plugins.base import ContentPlugin, RenderResult

from .ai import GeminiAIClient
from .api import VerseService
from .backgrounds import fetch_backgrounds
from .config import CONFIG_SCHEMA, DEFAULT_CONFIG
from .fetch import fetch_clips
from .identify import _SURAH_NAMES, identify_from_metadata
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
        self, pipeline_id: str, config: dict[str, Any], known_items: set[str] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch new Quran clips and background images."""
        cfg = _deep_merge(DEFAULT_CONFIG, config)
        max_clips = cfg.get("max_clips_per_fetch", 10)
        max_bg = cfg.get("max_backgrounds_per_fetch", 20)
        channels = cfg.get("source_channels", [])
        bg_cfg = cfg.get("bg_sources", {})

        ingredients: list[dict[str, Any]] = []
        if channels:
            try:
                clips = await fetch_clips(
                    pipeline_id, channels, max_clips=max_clips, known_items=known_items
                )
                ingredients.extend(clips)
            except Exception as e:
                logger.error("Clip fetch failed for pipeline %s: %s", pipeline_id, e)

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

        return ingredients

    async def render(
        self,
        pipeline_id: str,
        ingredient_ids: list[str],
        config: dict[str, Any],
    ) -> RenderResult:
        """Compose final video from approved ingredients."""
        render_ingredients = config.get("_render_ingredients", {})
        clip_path: str | None = render_ingredients.get("clip_path")
        bg_paths = render_ingredients.get("bg_paths") or []

        if not clip_path or not bg_paths:
            return RenderResult(file_path=None, caption="", metadata={"error": "missing_ingredients"})

        cfg = _deep_merge(DEFAULT_CONFIG, config)
        try:
            result = await render_from_ingredients(clip_path, bg_paths, cfg)
            return RenderResult(
                file_path=result["file_path"],
                thumbnail_path=result["thumbnail_path"],
                caption="",
                metadata=result["metadata"],
            )
        except Exception as e:
            logger.error("Render failed: %s", repr(e))
            return RenderResult(file_path=None, caption="", metadata={"error": repr(e)})

    async def identify_content(
        self,
        pipeline_id: str,
        produced_content_id: str,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Identify verse reference from rendered content. (Phase 4)"""
        logger.info("QuranPlugin.identify_content called for %s", produced_content_id)

        async with AsyncSessionLocal() as db:
            res = await db.execute(select(ProducedContent).where(ProducedContent.id == produced_content_id))
            content = res.scalar_one_or_none()
            if not content: return None
            
            ing_ids = json.loads(content.ingredient_ids_json)
            res = await db.execute(select(Ingredient).where(Ingredient.id.in_(ing_ids), Ingredient.type == "quran_clip"))
            clip = res.scalar_one_or_none()
            if not clip: return None
            
            clip_meta = json.loads(clip.metadata_json or "{}")
            source_url = clip.source_url

        id_result = identify_from_metadata(clip_meta)
        
        if not id_result or id_result.get("needs_ai"):
            from flux.config import settings
            if settings.gemini_api_keys:
                logger.info("Regex ID incomplete, falling back to Gemini AI...")
                ai_client = GeminiAIClient(settings.gemini_api_keys)
                # Pass both the URL and the description for best accuracy.
                # Many channels put the verse reference in the title or description.
                title = clip_meta.get("title", "")
                description = clip_meta.get("description", "")
                combined = f"Title: {title}\nDescription: {description}".strip()
                ai_result = await ai_client.identify_verse(
                    video_url=source_url, 
                    description=combined
                )
                if ai_result:
                    # Replace regex result entirely to avoid stale keys (e.g. wrong verse_key)
                    id_result = ai_result

        if id_result:
            surah_num = id_result.get("surah")
            if surah_num in _SURAH_NAMES:
                id_result["surah_name"] = _SURAH_NAMES[surah_num]["en"]
            return id_result

        return None

    async def build_caption(
        self,
        pipeline_id: str,
        produced_content_id: str,
        config: dict[str, Any],
        worker_config: dict[str, Any],
    ) -> str:
        """Generate caption for a specific platform worker. (Phase 4)"""
        logger.info("QuranPlugin.build_caption called for %s", produced_content_id)

        async with AsyncSessionLocal() as db:
            res = await db.execute(select(ProducedContent).where(ProducedContent.id == produced_content_id))
            content = res.scalar_one_or_none()
            if not content or not content.content_meta_json: return ""
            
            meta = json.loads(content.content_meta_json)
            surah = meta.get("surah")
            ayah = meta.get("ayah")
            surah_name = meta.get("surah_name", f"Surah {surah}")

        if not surah or not ayah: return ""

        verse_data = await VerseService().get_verse(surah, ayah)
        if not verse_data: return ""

        cfg = _deep_merge(DEFAULT_CONFIG, config)
        platform = worker_config.get("platform", "default")
        templates = cfg.get("caption_templates", {})
        template_str = templates.get(platform, templates.get("default", ""))
        
        if not template_str: return ""

        pool = cfg.get("hashtags", [])
        count = min(len(pool), random.randint(3, 5))
        hashtags = " ".join([f"#{h}" for s in random.sample(pool, count)]) if pool else ""

        caption = Template(template_str).render(
            surah_name=surah_name,
            verse_ref=f"{surah}:{ayah}",
            arabic_text=verse_data.get("arabic", ""),
            translation=verse_data.get("translation", ""),
            hashtags=hashtags
        )

        if platform == "x" and len(caption) > 280:
            caption = caption[:277] + "..."

        return caption.strip()

    def get_config_schema(self) -> dict[str, Any]:
        return CONFIG_SCHEMA
