"""Quran Shorts render pipeline — FFmpeg-based video composition.

Composites a Quran clip (with black-background colorkey removal) over a
background image or video, producing a 1080×1920 vertical MP4 ready for
social platforms.

Termux/ARM considerations:
- `-preset fast` reduces CPU load vs `slow`.
- `-crf 26` balances quality and file size on mobile.
- Output uses yuv420p for maximum compatibility.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)

# Output dimensions for vertical Shorts/Reels
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
CANVAS_FPS = 30

# Colorkey settings for black-background Quran clips
COLORKEY_COLOR = "0x000000"
COLORKEY_SIMILARITY = 0.3
COLORKEY_BLEND = 0.1

# Encoding presets (mobile-friendly)
ENCODE_PRESET = "fast"
ENCODE_CRF = 26


def _production_dir() -> Path:
    """Return the directory where rendered videos are stored."""
    return Path(settings.storage_path) / "library" / "production"


def _thumbnails_dir() -> Path:
    """Return the directory where thumbnails are stored."""
    return Path(settings.storage_path) / "thumbnails"


async def _run_ffmpeg(
    *args: str,
    timeout: float = 300.0,
) -> tuple[int, str, str]:
    """Run FFmpeg with given arguments. Returns (returncode, stdout, stderr)."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + list(args)
    logger.debug("FFmpeg cmd: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error("FFmpeg timed out after %.0fs", timeout)
        try:
            proc.kill()
            await proc.wait()
        except Exception as e:
            logger.debug("Failed to kill timed-out FFmpeg process: %s", e)
        return -1, "", f"FFmpeg timed out after {timeout}s"
    except FileNotFoundError:
        logger.error("FFmpeg not found in PATH")
        return -1, "", "FFmpeg not found in PATH"

    out = stdout.decode("utf-8", errors="replace")
    err = stderr.decode("utf-8", errors="replace")
    return proc.returncode or 0, out, err


def _build_colorkey_filter() -> str:
    """Build the FFmpeg colorkey filter string for black background removal."""
    return (
        f"colorkey={COLORKEY_COLOR}:"
        f"{COLORKEY_SIMILARITY}:"
        f"{COLORKEY_BLEND}"
    )


def _build_scale_filter(width: int, height: int) -> str:
    """Build FFmpeg scale filter maintaining aspect ratio, fitting inside box."""
    return (
        f"scale={width}:{height}:"
        f"force_original_aspect_ratio=decrease"
    )


async def render_video(
    clip_path: str,
    background_path: str,
    output_path: str,
    duration: float | None = None,
) -> str:
    """Render a Quran clip composited over a background.

    Args:
        clip_path: Path to the Quran clip MP4 (black background).
        background_path: Path to background image or video.
        output_path: Where to write the rendered MP4.
        duration: Optional duration limit in seconds (trims output).

    Returns:
        Absolute path to the rendered MP4.

    Raises:
        RuntimeError: If FFmpeg fails or output is not created.
    """
    if not Path(clip_path).exists():
        raise FileNotFoundError(f"Clip not found: {clip_path}")
    if not Path(background_path).exists():
        raise FileNotFoundError(f"Background not found: {background_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    bg_ext = Path(background_path).suffix.lower()
    is_video_bg = bg_ext in (".mp4", ".mov", ".webm", ".mkv")

    # Build filtergraph
    colorkey = _build_colorkey_filter()
    scale = _build_scale_filter(CANVAS_WIDTH, CANVAS_HEIGHT)

    # Inputs:
    #   0 = background (image or video)
    #   1 = Quran clip
    filter_complex = (
        f"[0:v]{scale},setsar=1,fps={CANVAS_FPS},format=yuv420p[bg];"
        f"[1:v]{colorkey},{scale},format=yuv420p[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1[video]"
    )

    args: list[str] = []

    if not is_video_bg:
        # Loop static image to match clip duration
        args.extend(["-loop", "1", "-i", background_path])
    else:
        args.extend(["-i", background_path])

    args.extend([
        "-i", clip_path,
        "-filter_complex", filter_complex,
        "-map", "[video]",
        "-map", "1:a?",
        "-c:v", "libx264",
        "-preset", ENCODE_PRESET,
        "-crf", str(ENCODE_CRF),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
    ])

    if duration:
        args.extend(["-t", str(duration)])

    args.append(output_path)

    returncode, stdout, stderr = await _run_ffmpeg(*args)

    if returncode != 0:
        raise RuntimeError(
            f"FFmpeg render failed (code {returncode}): {stderr}"
        )

    if not Path(output_path).exists():
        raise RuntimeError(
            f"FFmpeg reported success but output missing: {output_path}"
        )

    logger.info(
        "Rendered video: %s (%d bytes)",
        output_path,
        Path(output_path).stat().st_size,
    )
    return output_path


async def extract_thumbnail(
    video_path: str,
    output_path: str,
    time_sec: float = 2.0,
) -> str:
    """Extract a single-frame thumbnail from a video.

    Args:
        video_path: Source MP4.
        output_path: Where to write the JPEG thumbnail.
        time_sec: Timestamp to extract (default 2s).

    Returns:
        Absolute path to the thumbnail JPEG.

    Raises:
        RuntimeError: If FFmpeg fails.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    args = [
        "-ss", str(time_sec),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        "-vf", f"scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}:force_original_aspect_ratio=decrease",
        output_path,
    ]

    returncode, _stdout, stderr = await _run_ffmpeg(*args)

    if returncode != 0:
        raise RuntimeError(
            f"Thumbnail extraction failed (code {returncode}): {stderr}"
        )

    if not Path(output_path).exists():
        raise RuntimeError(
            f"Thumbnail missing after extraction: {output_path}"
        )

    logger.info("Extracted thumbnail: %s", output_path)
    return output_path


async def render_from_ingredients(
    clip_path: str,
    background_paths: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    """High-level render orchestrator for the Quran plugin.

    Selects the first background, renders the clip over it, extracts a
    thumbnail, and returns result metadata.

    Args:
        clip_path: Path to approved Quran clip.
        background_paths: List of approved background image/video paths.
        config: Pipeline config (may include timing_sets, canvas, etc. in future).

    Returns:
        Dict with keys: file_path, thumbnail_path, duration, metadata.
    """
    if not background_paths:
        raise ValueError("At least one background is required for rendering")

    prod_dir = _production_dir()
    thumb_dir = _thumbnails_dir()
    prod_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique output filenames based on clip basename
    clip_name = Path(clip_path).stem
    output_video = str(prod_dir / f"{clip_name}_rendered.mp4")
    output_thumb = str(thumb_dir / f"{clip_name}_thumb.jpg")

    # Use first background for v1 (slideshow support in v3.1)
    bg_path = background_paths[0]

    # Render
    rendered_path = await render_video(clip_path, bg_path, output_video)

    # Thumbnail at 2s
    thumb_path = await extract_thumbnail(rendered_path, output_thumb, time_sec=2.0)

    # Determine actual rendered duration
    raw_duration = config.get("duration")
    duration: float | None = None
    if raw_duration is not None:
        try:
            duration = float(raw_duration) or None
        except (ValueError, TypeError):
            logger.warning("Invalid duration in config: %s", raw_duration)

    return {
        "file_path": rendered_path,
        "thumbnail_path": thumb_path,
        "duration_secs": duration,
        "metadata": {
            "render_method": "video_compose",
            "clip_path": clip_path,
            "background_path": bg_path,
            "canvas": {
                "width": CANVAS_WIDTH,
                "height": CANVAS_HEIGHT,
                "fps": CANVAS_FPS,
            },
        },
    }
