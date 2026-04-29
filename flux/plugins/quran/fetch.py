"""Quran clip fetching via yt-dlp.

Downloads YouTube Shorts from whitelisted channels and returns
ingredient metadata for the core engine to persist.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)

# Shorts max duration in seconds (YouTube Shorts are ≤60s, but we allow a buffer)
MAX_SHORT_DURATION = 120

# yt-dlp download options — lightweight, mobile-friendly
_YDL_OPTS_BASE: dict[str, Any] = {
    "quiet": True,
    "no_warnings": True,
    "format": "best[ext=mp4]/best",
    "merge_output_format": "mp4",
    "writethumbnail": False,
    "writeinfojson": False,
    "writesubtitles": False,
}


def _clips_dir() -> Path:
    """Return the directory where Quran clips are stored."""
    return Path(settings.storage_path) / "library" / "quran_clips"


def _extract_shorts_from_channel(channel_url: str, max_clips: int) -> list[dict[str, Any]]:
    """List Shorts from a channel without downloading yet.

    Returns a list of video info dicts with at least:
    id, title, uploader, duration, webpage_url
    """
    # Ensure we're targeting the Shorts tab
    if "/shorts" not in channel_url:
        channel_url = channel_url.rstrip("/") + "/shorts"

    opts = {
        **_YDL_OPTS_BASE,
        "extract_flat": False,
        "playlistend": max_clips,
        "ignoreerrors": True,
    }

    videos: list[dict[str, Any]] = []
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if not info:
                return videos

            entries = info.get("entries") or []
            for entry in entries:
                if not entry:
                    continue
                # Filter: only keep entries that look like Shorts
                duration = entry.get("duration") or 0
                if duration > MAX_SHORT_DURATION:
                    continue  # Probably not a Short
                videos.append({
                    "id": entry.get("id"),
                    "title": entry.get("title", ""),
                    "uploader": entry.get("uploader", ""),
                    "duration": duration,
                    "webpage_url": entry.get("webpage_url", f"https://youtube.com/shorts/{entry.get('id')}"),
                    "channel_url": entry.get("channel_url", channel_url),
                })
    except (DownloadError, ExtractorError) as e:
        logger.error("yt-dlp failed to extract channel %s: %s", channel_url, e)
    except Exception as e:
        logger.error("Unexpected error extracting channel %s: %s", channel_url, e)

    return videos


def _download_video(video_id: str, video_url: str, output_dir: Path) -> Path | None:
    """Download a single video to output_dir. Returns file path or None if already downloaded or failed."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_id}.mp4"

    if output_path.exists():
        logger.debug("Video %s already downloaded, skipping", video_id)
        return None

    opts = {
        **_YDL_OPTS_BASE,
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])
        logger.info("Downloaded video %s -> %s", video_id, output_path)
        return output_path
    except (DownloadError, ExtractorError) as e:
        logger.error("yt-dlp failed to download video %s: %s", video_id, e)
        return None
    except Exception as e:
        logger.error("Unexpected error downloading video %s: %s", video_id, e)
        return None


def _build_ingredient_meta(video_info: dict[str, Any], file_path: Path) -> dict[str, Any]:
    """Build ingredient metadata dict from video info."""
    file_size = os.path.getsize(file_path) if file_path.exists() else None
    return {
        "type": "quran_clip",
        "file_path": str(file_path),
        "source_url": video_info["webpage_url"],
        "metadata": {
            "yt_id": video_info["id"],
            "title": video_info["title"],
            "uploader": video_info["uploader"],
            "channel_url": video_info.get("channel_url", ""),
        },
        "file_size_bytes": file_size,
        "duration_secs": video_info.get("duration"),
    }


async def fetch_clips(
    pipeline_id: str,
    source_channels: list[str],
    max_clips: int = 10,
) -> list[dict[str, Any]]:
    """Fetch Quran clips from YouTube channels until max_clips is reached.

    Returns a list of ingredient metadata dicts ready for insertion.
    """
    ingredients: list[dict[str, Any]] = []
    clips_dir = _clips_dir()
    
    from flux.db import AsyncSessionLocal
    from flux.models import Ingredient
    from sqlalchemy import select, and_

    async with AsyncSessionLocal() as db:
        for channel_url in source_channels:
            if len(ingredients) >= max_clips:
                break

            logger.info("Scanning channel %s for Shorts", channel_url)
            
            # Fetch a larger batch to improve chances of finding new ones
            videos = _extract_shorts_from_channel(channel_url, max_clips * 3)
            
            for video in videos:
                if len(ingredients) >= max_clips:
                    break

                video_id = video.get("id")
                if not video_id:
                    continue

                # 1. DB Check: Skip if already in database
                stmt = select(Ingredient).where(
                    and_(
                        Ingredient.pipeline_id == pipeline_id,
                        Ingredient.metadata_json.like(f'%{video_id}%')
                    )
                )
                res = await db.execute(stmt)
                if res.scalar_one_or_none():
                    logger.debug("Video %s already in DB, skipping", video_id)
                    continue

                # 2. Disk Check: Skip if exists
                file_path = clips_dir / f"{video_id}.mp4"
                if file_path.exists():
                    logger.debug("Video %s already on disk, skipping", video_id)
                    continue

                # 3. Download
                logger.info("Found new video %s, downloading...", video_id)
                downloaded_path = _download_video(video_id, video["webpage_url"], clips_dir)
                if downloaded_path:
                    ingredients.append(_build_ingredient_meta(video, downloaded_path))
                    logger.info("Added new ingredient: %s", video_id)

    logger.info("Fetch complete: %d new clips found for pipeline %s", len(ingredients), pipeline_id)
    return ingredients
