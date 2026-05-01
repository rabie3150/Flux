"""Quran.com API client and verse service.

Fetches Arabic text and translations, with a local SQLite cache.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.db import AsyncSessionLocal
from flux.logger import get_logger
from flux.models import VerseCache

logger = get_logger(__name__)

BASE_URL = "https://api.quran.com/api/v4"

class VerseService:
    """Service to fetch and cache Quranic verses."""

    def __init__(self, translation_id: int = 131):  # 131 = Sahih International
        self.translation_id = translation_id

    async def get_verse(self, surah: int, ayah: int) -> dict[str, Any] | None:
        """Get verse data from cache or API."""
        async with AsyncSessionLocal() as db:
            # 1. Check cache
            cached = await self._get_from_cache(db, surah, ayah)
            if cached:
                return cached

            # 2. Fetch from API
            try:
                data = await self._fetch_from_api(surah, ayah)
                if data:
                    # 3. Store in cache
                    await self._save_to_cache(db, surah, ayah, data)
                    return data
            except Exception as e:
                logger.error("Failed to fetch verse %d:%d from API: %s", surah, ayah, e)
        
        return None

    async def _get_from_cache(self, db: AsyncSession, surah: int, ayah: int) -> dict[str, Any] | None:
        result = await db.execute(
            select(VerseCache).where(
                VerseCache.surah_number == surah,
                VerseCache.ayah_number == ayah
            )
        )
        row = result.scalar_one_or_none()
        if row:
            return {
                "surah": row.surah_number,
                "ayah": row.ayah_number,
                "arabic": row.arabic_text,
                "translation": json.loads(row.translations_json or "{}").get(str(self.translation_id)),
                "tafseer": row.tafseer_json
            }
        return None

    async def _fetch_from_api(self, surah: int, ayah: int) -> dict[str, Any] | None:
        """Fetch verse data from Quran.com API."""
        verse_key = f"{surah}:{ayah}"
        url = f"{BASE_URL}/verses/by_key/{verse_key}"
        params = {
            "language": "en",
            "words": "false",
            "translations": self.translation_id,
            "fields": "text_uthmani"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()["verse"]

            # Extract translation text
            translations = data.get("translations", [])
            translation_text = translations[0]["text"] if translations else ""
            # Strip HTML tags from translation if any
            import re
            translation_text = re.sub('<[^<]+?>', '', translation_text)

            return {
                "surah": surah,
                "ayah": ayah,
                "arabic": data.get("text_uthmani"),
                "translation": translation_text,
                "tafseer": None # Tafseer requires a separate API call if needed
            }

    async def get_verse_range(self, surah: int, ayah_start: int, ayah_end: int) -> dict[str, Any] | None:
        """Fetch multiple verses and return concatenated arabic + translation."""
        verses: list[dict[str, Any]] = []
        for ayah in range(ayah_start, ayah_end + 1):
            v = await self.get_verse(surah, ayah)
            if v:
                verses.append(v)
        if not verses:
            return None
        return {
            "surah": surah,
            "ayah": ayah_start,
            "ayah_end": ayah_end,
            "arabic": " ".join(v["arabic"] for v in verses if v.get("arabic")),
            "translation": " ".join(v["translation"] for v in verses if v.get("translation")),
        }

    async def _save_to_cache(self, db: AsyncSession, surah: int, ayah: int, data: dict[str, Any]):
        translations = {str(self.translation_id): data["translation"]}
        cache_entry = VerseCache(
            surah_number=surah,
            ayah_number=ayah,
            arabic_text=data["arabic"],
            translations_json=json.dumps(translations),
            tafseer_json=data.get("tafseer")
        )
        db.add(cache_entry)
        await db.commit()
        logger.info("Cached verse %d:%d", surah, ayah)
