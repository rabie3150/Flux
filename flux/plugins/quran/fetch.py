"""Quran clip fetching via yt-dlp.

Downloads YouTube Shorts from whitelisted channels and returns
ingredient metadata for the core engine to persist.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yt_dlp

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)

# yt-dlp download options — lightweight, mobile-friendly
_YDL_OPTS_BASE: dict[str, Any] = {
    "quiet": True,
    "no_warnings": True,
    "format": "best[height<=720][ext=mp4]/best[ext=mp4]/best",
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
                if duration > 120:
                    continue  # Probably not a Short
                videos.append({
                    "id": entry.get("id"),
                    "title": entry.get("title", ""),
                    "uploader": entry.get("uploader", ""),
                    "duration": duration,
                    "webpage_url": entry.get("webpage_url", f"https://youtube.com/shorts/{entry.get('id')}"),
                })
    except Exception as e:
        logger.error("yt-dlp failed to extract channel %s: %s", channel_url, e)

    return videos


def _download_video(video_id: str, video_url: str, output_dir: Path) -> Path | None:
    """Download a single video to output_dir. Returns file path or None."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_id}.mp4"

    if output_path.exists():
        logger.debug("Video %s already downloaded, skipping", video_id)
        return output_path

    opts = {
        **_YDL_OPTS_BASE,
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])
        logger.info("Downloaded video %s -> %s", video_id, output_path)
        return output_path
    except Exception as e:
        logger.error("Failed to download video %s: %s", video_id, e)
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
    """Fetch Quran clips from YouTube channels.

    Returns a list of ingredient metadata dicts ready for insertion.
    """
    ingredients: list[dict[str, Any]] = []
    clips_dir = _clips_dir()
    remaining = max_clips

    for channel_url in source_channels:
        if remaining <= 0:
            break

        logger.info("Scanning channel %s for Shorts", channel_url)
        videos = _extract_shorts_from_channel(channel_url, remaining)
        logger.info("Found %d candidate Shorts from %s", len(videos), channel_url)

        for video in videos:
            if remaining <= 0:
                break

            video_id = video.get("id")
            if not video_id:
                continue

            video_url = video["webpage_url"]
            file_path = _download_video(video_id, video_url, clips_dir)
            if file_path:
                ingredients.append(_build_ingredient_meta(video, file_path))
                remaining -= 1

    logger.info("Fetch complete: %d new clips for pipeline %s", len(ingredients), pipeline_id)
    return ingredients
