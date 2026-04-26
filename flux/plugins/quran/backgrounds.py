"""Background image/video fetching from Pexels and Unsplash.

Downloads media matching safe keywords, saving locally for the
render pipeline to composite behind Quran clips.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)

_PEXELS_BASE = "https://api.pexels.com/v1"
_UNSPLASH_BASE = "https://api.unsplash.com"


def _matches_blocklist(text: str | None, blocklist: list[str]) -> bool:
    """Return True if text contains any blocked keyword (case-insensitive)."""
    if not text:
        return False
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in blocklist)


def _bg_dir(subdir: str) -> Path:
    """Return the directory for background media."""
    return Path(settings.storage_path) / "library" / "backgrounds" / subdir


def _pexels_headers() -> dict[str, str]:
    key = settings.pexels_api_key
    if not key:
        logger.warning("PEXELS_API_KEY not configured")
    return {"Authorization": key}


def _unsplash_headers() -> dict[str, str]:
    key = settings.unsplash_access_key
    if not key:
        logger.warning("UNSPLASH_ACCESS_KEY not configured")
    return {"Authorization": f"Client-ID {key}"}


def _already_downloaded(source: str, media_id: str | int, ext: str = "jpg") -> Path | None:
    """Check if a background was already fetched."""
    path = _bg_dir("images") / f"{source}_{media_id}.{ext}"
    if path.exists():
        return path
    return None


def _save_image(response: httpx.Response, dest: Path) -> Path | None:
    """Save an image response to disk."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        logger.debug("Saved image %s (%d bytes)", dest, len(response.content))
        return dest
    except OSError as e:
        logger.error("Failed to save image %s: %s", dest, e)
        return None


def _build_bg_meta(
    file_path: Path,
    source: str,
    media_id: str | int,
    photographer: str,
    url: str,
    keywords: list[str],
) -> dict[str, Any]:
    """Build ingredient metadata for a background image."""
    return {
        "type": "bg_image",
        "file_path": str(file_path),
        "source_url": url,
        "metadata": {
            "source": source,
            "media_id": str(media_id),
            "photographer": photographer,
            "keywords": keywords,
        },
        "file_size_bytes": os.path.getsize(file_path) if file_path.exists() else None,
        "duration_secs": None,
    }


async def _fetch_pexels(
    keywords: list[str],
    per_keyword: int = 3,
    max_total: int = 20,
    blocklist: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch images from Pexels."""
    ingredients: list[dict[str, Any]] = []
    if not settings.pexels_api_key:
        logger.warning("Skipping Pexels: no API key")
        return ingredients

    headers = _pexels_headers()
    blocklist = blocklist or []
    rate_limited = False
    async with httpx.AsyncClient(timeout=30.0) as client:
        for keyword in keywords:
            if len(ingredients) >= max_total or rate_limited:
                break

            try:
                resp = await client.get(
                    f"{_PEXELS_BASE}/search",
                    headers=headers,
                    params={
                        "query": keyword,
                        "orientation": "portrait",
                        "per_page": per_keyword,
                    },
                )
                if resp.status_code == 429:
                    logger.warning("Pexels rate limited (429). Stopping Pexels fetch.")
                    rate_limited = True
                    continue
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                logger.warning("Pexels search failed for '%s': %s", keyword, e)
                continue

            for photo in data.get("photos", []):
                if len(ingredients) >= max_total:
                    break

                photo_id = photo.get("id")
                photographer = photo.get("photographer", "")
                photo_url = photo.get("url", "")
                alt_text = photo.get("alt", "")

                # Blocklist filter: check photographer, alt text, and URL
                if blocklist and (
                    _matches_blocklist(photographer, blocklist)
                    or _matches_blocklist(alt_text, blocklist)
                    or _matches_blocklist(photo_url, blocklist)
                ):
                    logger.debug("Pexels image %s blocked by blocklist", photo_id)
                    continue

                existing = _already_downloaded("pexels", photo_id)
                if existing:
                    logger.debug("Pexels image %s already fetched", photo_id)
                    ingredients.append(_build_bg_meta(
                        existing, "pexels", photo_id,
                        photographer,
                        photo_url,
                        [keyword],
                    ))
                    continue

                # Download the image
                src_url = photo.get("src", {}).get("large") or photo.get("src", {}).get("original")
                if not src_url:
                    continue

                try:
                    img_resp = await client.get(src_url, timeout=30.0)
                    img_resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.warning("Failed to download Pexels image %s: %s", photo_id, e)
                    continue

                dest = _bg_dir("images") / f"pexels_{photo_id}.jpg"
                saved = _save_image(img_resp, dest)
                if saved:
                    ingredients.append(_build_bg_meta(
                        saved, "pexels", photo_id,
                        photographer,
                        photo_url,
                        [keyword],
                    ))

    logger.info("Pexels fetch complete: %d images", len(ingredients))
    return ingredients


async def _fetch_unsplash(
    keywords: list[str],
    per_keyword: int = 2,
    max_total: int = 10,
    blocklist: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch images from Unsplash (fallback)."""
    ingredients: list[dict[str, Any]] = []
    if not settings.unsplash_access_key:
        logger.warning("Skipping Unsplash: no access key")
        return ingredients

    headers = _unsplash_headers()
    blocklist = blocklist or []
    rate_limited = False
    async with httpx.AsyncClient(timeout=30.0) as client:
        for keyword in keywords:
            if len(ingredients) >= max_total or rate_limited:
                break

            try:
                resp = await client.get(
                    f"{_UNSPLASH_BASE}/search/photos",
                    headers=headers,
                    params={
                        "query": keyword,
                        "orientation": "portrait",
                        "per_page": per_keyword,
                    },
                )
                if resp.status_code == 429:
                    logger.warning("Unsplash rate limited (429). Stopping Unsplash fetch.")
                    rate_limited = True
                    continue
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                logger.warning("Unsplash search failed for '%s': %s", keyword, e)
                continue

            for result in data.get("results", []):
                if len(ingredients) >= max_total:
                    break

                img_id = result.get("id")
                photographer = result.get("user", {}).get("name", "")
                photo_url = result.get("links", {}).get("html", "")
                description = result.get("description") or result.get("alt_description", "")

                # Blocklist filter
                if blocklist and (
                    _matches_blocklist(photographer, blocklist)
                    or _matches_blocklist(description, blocklist)
                    or _matches_blocklist(photo_url, blocklist)
                ):
                    logger.debug("Unsplash image %s blocked by blocklist", img_id)
                    continue

                existing = _already_downloaded("unsplash", img_id)
                if existing:
                    logger.debug("Unsplash image %s already fetched", img_id)
                    ingredients.append(_build_bg_meta(
                        existing, "unsplash", img_id,
                        photographer,
                        photo_url,
                        [keyword],
                    ))
                    continue

                # Download regular size image
                img_url = result.get("urls", {}).get("regular")
                if not img_url:
                    continue

                try:
                    img_resp = await client.get(img_url, timeout=30.0)
                    img_resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.warning("Failed to download Unsplash image %s: %s", img_id, e)
                    continue

                dest = _bg_dir("images") / f"unsplash_{img_id}.jpg"
                saved = _save_image(img_resp, dest)
                if saved:
                    ingredients.append(_build_bg_meta(
                        saved, "unsplash", img_id,
                        photographer,
                        photo_url,
                        [keyword],
                    ))

    logger.info("Unsplash fetch complete: %d images", len(ingredients))
    return ingredients


async def fetch_backgrounds(
    pipeline_id: str,
    pexels_keywords: list[str],
    unsplash_keywords: list[str],
    max_total: int = 20,
    blocklist: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch background images from Pexels and Unsplash.

    Tries Pexels first; falls back to Unsplash if Pexels is rate-limited
    or returns no results.
    """
    ingredients = await _fetch_pexels(pexels_keywords, max_total=max_total, blocklist=blocklist)

    # If Pexels gave us less than half, supplement with Unsplash
    if len(ingredients) < max_total // 2:
        remaining = max_total - len(ingredients)
        unsplash = await _fetch_unsplash(unsplash_keywords, max_total=remaining, blocklist=blocklist)
        ingredients.extend(unsplash)

    logger.info("Background fetch complete: %d total images for pipeline %s", len(ingredients), pipeline_id)
    return ingredients
