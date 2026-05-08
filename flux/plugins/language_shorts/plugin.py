"""
Language Shorts Plugin — Generates educational language videos.
"""

from __future__ import annotations

import json
import random
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from flux.core import ingredients as ingredient_service
from flux.logger import get_logger
from flux.models import Pipeline
from flux.plugins.base import ContentPlugin, RenderResult
from flux.plugins.language_shorts.config import CONFIG_SCHEMA, DEFAULT_CONFIG
from flux.plugins.language_shorts.generate import GeminiGenerator
from flux.plugins.quran.backgrounds import fetch_backgrounds

logger = get_logger(__name__)

class LanguageShortsPlugin(ContentPlugin):
    """
    Generates language learning Shorts using TTS, FFmpeg, and Gemini Flash.
    """
    
    @property
    def name(self) -> str:
        return "language_shorts"

    @property
    def default_config(self) -> dict[str, Any]:
        return DEFAULT_CONFIG

    @property
    def config_schema(self) -> dict[str, Any]:
        return CONFIG_SCHEMA

    async def fetch_ingredients(self, db: AsyncSession, pipeline: Pipeline) -> int:
        """
        Fetch phase: Generates vocabulary items using Gemini Flash,
        and fetches abstract background images.
        """
        logger.info("LanguageShortsPlugin: Generating ingredients for pipeline %s", pipeline.id)
        config = pipeline.config_json_dict or self.default_config
        
        # 1. Fetch previously taught words to avoid repeats
        # We fetch all 'word_batch' ingredients for this pipeline to deduce past words
        all_ingredients = await ingredient_service.get_pipeline_ingredients(db, pipeline.id)
        taught_words = []
        for ing in all_ingredients:
            if ing.type == "word_batch" and ing.metadata_json:
                try:
                    meta = json.loads(ing.metadata_json)
                    for word_obj in meta.get("words", []):
                        if "source" in word_obj:
                            taught_words.append(word_obj["source"])
                except json.JSONDecodeError:
                    continue
                    
        logger.info("Found %d previously taught words to avoid.", len(taught_words))
        
        # 2. Generate Vocabulary
        themes = config.get("themes", ["basics"])
        theme = random.choice(themes)
        
        generator = GeminiGenerator()
        words = await generator.generate_vocabulary(
            source_lang=config.get("source_lang", "en"),
            target_lang=config.get("target_lang", "it"),
            theme=theme,
            count=config.get("words_per_video", 5),
            difficulty=config.get("difficulty", "beginner"),
            avoid_words=taught_words
        )
        
        added_count = 0
        if words:
            # We store the whole batch as one ingredient of type 'word_batch'
            batch_data = {
                "theme": theme,
                "words": words,
                "source_lang": config.get("source_lang", "en"),
                "target_lang": config.get("target_lang", "it"),
                "difficulty": config.get("difficulty", "beginner"),
                "generated_at": time.time(),
            }
            batch_ingredient = {
                "type": "word_batch",
                "file_path": None,
                "source_url": None,
                "metadata": batch_data,
                "file_size_bytes": 0,
                "duration_secs": 0,
            }
            await ingredient_service.create_ingredients(db, pipeline.id, [batch_ingredient])
            added_count += 1
            logger.info("Generated vocabulary batch for theme '%s' with %d words", theme, len(words))

        # 2. Fetch Backgrounds
        bg_config = config.get("bg_sources", {})
        bg_ingredients = await fetch_backgrounds(
            pipeline_id=pipeline.id,
            pexels_keywords=bg_config.get("pexels_keywords", []),
            unsplash_keywords=bg_config.get("unsplash_keywords", []),
            max_total=5, # Just need a few
            blocklist=bg_config.get("blocklist", [])
        )
        
        if bg_ingredients:
            await ingredient_service.create_ingredients(db, pipeline.id, bg_ingredients)
            added_count += len(bg_ingredients)

        return added_count

    async def render_from_ingredients(
        self, db: AsyncSession, pipeline: Pipeline, ingredient_ids: list[str]
    ) -> RenderResult:
        """
        Render phase: Builds the FFmpeg composite video with animated text and TTS.
        """
        logger.info("LanguageShortsPlugin: Rendering video for pipeline %s", pipeline.id)
        config = pipeline.config_json_dict or self.default_config
        
        # 1. Fetch ingredients from DB
        ingredients = await ingredient_service.get_ingredients(db, ingredient_ids)
        
        word_batch_meta = None
        bg_paths = []
        for ing in ingredients:
            if ing.type == "word_batch" and ing.metadata_json:
                word_batch_meta = json.loads(ing.metadata_json)
            elif ing.type == "bg_image" and ing.file_path:
                bg_paths.append(ing.file_path)
                
        if not word_batch_meta or not word_batch_meta.get("words"):
            raise ValueError("No word_batch ingredient found or words list empty.")
        if not bg_paths:
            raise ValueError("No bg_image ingredients found.")
            
        # 2. Setup output paths
        from flux.config import settings
        from pathlib import Path
        prod_dir = Path(settings.storage_path) / "library" / "production"
        prod_dir.mkdir(parents=True, exist_ok=True)
        
        # unique filename based on theme and timestamp
        import time
        ts = int(time.time())
        theme = word_batch_meta.get("theme", "words")
        output_video = str(prod_dir / f"lang_{theme}_{ts}.mp4")
        
        # 3. Call render
        from flux.plugins.language_shorts.render import render_video
        rendered_path = await render_video(word_batch_meta, bg_paths, output_video, config)
        
        # 4. Extract thumbnail
        from flux.plugins.quran.render import extract_thumbnail
        thumb_dir = Path(settings.storage_path) / "thumbnails"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        output_thumb = str(thumb_dir / f"lang_{theme}_{ts}_thumb.jpg")
        
        thumb_path = await extract_thumbnail(rendered_path, output_thumb, time_sec=5.0)
        
        # 5. Return result
        # Calculate duration
        timing = config.get("timing", {})
        block_dur = timing.get("en_display_secs", 2.0) + timing.get("countdown_secs", 3.0) + timing.get("reveal_hold_secs", 3.0) + timing.get("pause_between_secs", 1.5)
        duration = timing.get("intro_duration", 3.0) + (len(word_batch_meta["words"]) * block_dur) + timing.get("outro_duration", 3.0)
        
        return RenderResult(
            file_path=rendered_path,
            thumbnail_path=thumb_path,
            duration_secs=duration,
            metadata={
                "render_method": "tts_compose",
                "theme": theme,
                "words_count": len(word_batch_meta["words"])
            }
        )

    async def identify_produced_content(
        self, db: AsyncSession, pipeline: Pipeline, content_id: str
    ) -> dict[str, Any]:
        """
        Identify phase: Not needed, content is known at generation time.
        """
        return {"success": True, "metadata": {"identified_by": "language_shorts"}}

    async def get_caption(self, db: AsyncSession, pipeline: Pipeline, content_id: str, platform: str) -> str:
        """
        Caption phase: Generates the caption using Jinja2 templates.
        """
        from flux.core.production import get_produced_content
        from jinja2 import Template
        
        content = await get_produced_content(db, content_id)
        if not content:
            return ""
            
        ingredient_ids = json.loads(content.ingredient_ids_json or "[]")
        ingredients = await ingredient_service.get_ingredients(db, ingredient_ids)
        
        word_batch_meta = None
        for ing in ingredients:
            if ing.type == "word_batch" and ing.metadata_json:
                word_batch_meta = json.loads(ing.metadata_json)
                break
                
        if not word_batch_meta:
            return "Language learning vocabulary!"
            
        config = pipeline.config_json_dict or self.default_config
        templates = config.get("caption_templates", {})
        template_str = templates.get(platform, templates.get("default", ""))
        
        if not template_str:
            template_str = templates.get("default", "")
            
        template = Template(template_str)
        hashtags = config.get("hashtags", [])
        
        caption = template.render(
            theme=word_batch_meta.get("theme", "").title(),
            target_lang_name=config.get("target_lang_name", "Italian"),
            words=word_batch_meta.get("words", []),
            hashtags=" ".join(f"#{ht}" for ht in hashtags)
        )
        
        # Smart truncate for X if needed
        if platform == "x" and len(caption) > 280:
            caption = caption[:277] + "..."
            
        return caption

