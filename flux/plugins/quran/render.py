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
import uuid
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
        # Standard async way (requires ProactorEventLoop on Windows)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
    except NotImplementedError:
        # WINDOWS FALLBACK: If create_subprocess_exec is not implemented,
        # run it in a thread using standard subprocess.run.
        logger.warning("asyncio.create_subprocess_exec not supported (likely not ProactorEventLoop). Using thread fallback.")
        import subprocess
        
        def _sync_run():
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            return p.returncode, p.stdout, p.stderr

        try:
            return await asyncio.to_thread(_sync_run)
        except subprocess.TimeoutExpired:
            return -1, "", "FFmpeg timed out (sync fallback)"
        except Exception as e:
            return -1, "", f"FFmpeg sync fallback failed: {e}"
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


def _build_colorkey_filter() -> str:
    """Build the FFmpeg colorkey filter string for black background removal."""
    return (
        f"colorkey={COLORKEY_COLOR}:"
        f"{COLORKEY_SIMILARITY}:"
        f"{COLORKEY_BLEND}"
    )


def _build_scale_filter(width: int, height: int) -> str:
    """Build FFmpeg scale filter maintaining aspect ratio, fitting inside box.
    Ensures dimensions are divisible by 2 for encoder compatibility.
    """
    return (
        f"scale='if(gt(iw/ih,{width}/{height}),{width},-2)':'if(gt(iw/ih,{width}/{height}),-2,{height})'"
    )


def _build_liven_up_filter(width: int, height: int) -> str:
    """Build a smooth panning effect using crop and scale.
    Guaranteed to work on all FFmpeg versions.
    """
    # Scale up by 20% to give room for movement without black edges
    sw, sh = int(width * 1.2), int(height * 1.2)
    # Ensure dimensions are divisible by 2 for the encoder
    sw, sh = (sw // 2) * 2, (sh // 2) * 2
    
    # x/y coordinates oscillate slowly over frame count (n)
    # Amplitude increased to be clearly visible
    x_expr = f"(iw-ow)/2 + (iw/15)*sin(n/45)"
    y_expr = f"(ih-oh)/2 + (ih/15)*cos(n/60)"
    
    return (
        f"scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},"
        f"crop={width}:{height}:{x_expr}:{y_expr}"
    )


async def render_video(
    clip_path: str,
    background_paths: list[str],
    output_path: str,
    duration: float | None = None,
    image_duration: float = 5.0,
    ken_burns: bool = True,
) -> str:
    """Render a Quran clip composited over a background.

    Args:
        clip_path: Path to the Quran clip MP4 (black background).
        background_paths: List of paths to background images or videos.
        output_path: Where to write the rendered MP4.
        duration: Optional duration limit in seconds (trims output).
        image_duration: Duration to show each image in a slideshow.
        ken_burns: Whether to apply zoom/pan to images.

    Returns:
        Absolute path to the rendered MP4.

    Raises:
        RuntimeError: If FFmpeg fails or output is not created.
    """
    if isinstance(background_paths, str):
        background_paths = [background_paths]
    elif not isinstance(background_paths, list):
        background_paths = list(background_paths)
    
    # Robust check for character list trap
    if background_paths and all(isinstance(x, str) and len(x) == 1 for x in background_paths):
        background_paths = ["".join(background_paths)]

    if not background_paths:
        raise ValueError("At least one background is required")
        
    for bg in background_paths:
        if not Path(bg).exists():
            raise FileNotFoundError(f"Background not found: {bg}")

    if not Path(clip_path).exists():
        raise FileNotFoundError(f"Clip not found: {clip_path}")


    is_video_bg = any(Path(p).suffix.lower() in (".mp4", ".mov", ".webm", ".mkv") for p in background_paths)

    # Build filtergraph
    colorkey = _build_colorkey_filter()
    scale = _build_scale_filter(CANVAS_WIDTH, CANVAS_HEIGHT)
    
    if is_video_bg or not ken_burns:
        bg_filter = f"{scale},setsar=1,fps={CANVAS_FPS}"
    else:
        bg_filter = f"{_build_liven_up_filter(CANVAS_WIDTH, CANVAS_HEIGHT)},setsar=1,fps={CANVAS_FPS}"

    # Inputs:
    #   0 = background (image or video)
    #   1 = Quran clip
    # Fix: Move format=yuv420p to the very end to prevent alpha stripping
    filter_complex = (
        f"[0:v]{bg_filter}[bg];"
        f"[1:v]{colorkey},{scale},format=yuva420p[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,format=yuv420p[video]"
    )

    args: list[str] = []
    concat_path = None

    if is_video_bg:
        # For video background, loop indefinitely; overlay=shortest=1 will trim it.
        args.extend(["-stream_loop", "-1", "-i", background_paths[0]])
    else:
        if len(background_paths) == 1:
            # Loop static image to match clip duration
            args.extend(["-loop", "1", "-i", background_paths[0]])
        else:
            # Slideshow using concat demuxer with unique temp filename
            temp_id = uuid.uuid4().hex[:8]
            concat_path = Path(output_path).with_suffix(f".{temp_id}.concat.txt")
            lines = ["ffconcat version 1.0"]
            for bg in background_paths:
                safe_path = str(Path(bg).absolute()).replace('\\', '/')
                lines.append(f"file '{safe_path}'")
                lines.append(f"duration {image_duration}")
            # Add the last file again without duration to ensure proper playback of last frame
            last_safe_path = str(Path(background_paths[-1]).absolute()).replace('\\', '/')
            lines.append(f"file '{last_safe_path}'")
            concat_path.write_text("\n".join(lines))
            
            args.extend(["-stream_loop", "-1", "-f", "concat", "-safe", "0", "-i", str(concat_path)])

    args.extend([
        "-i", clip_path,
        "-filter_complex", filter_complex,
        "-map", "[video]",
        "-map", "1:a?",  # Map audio from the Quran clip
        "-c:v", "libx264",
        "-preset", ENCODE_PRESET,
        "-crf", str(ENCODE_CRF),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
    ])

    if duration:
        args.extend(["-t", str(duration)])

    args.append(output_path)

    try:
        returncode, stdout, stderr = await _run_ffmpeg(*args)
    finally:
        if concat_path and concat_path.exists():
            concat_path.unlink()

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
        
    if isinstance(background_paths, str):
        background_paths = [background_paths]
    elif not isinstance(background_paths, (list, tuple)):
        # Fallback for other iterables, but we already handled str
        background_paths = list(background_paths)

    prod_dir = _production_dir()
    thumb_dir = _thumbnails_dir()
    prod_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique output filenames based on clip basename
    clip_name = Path(clip_path).stem
    output_video = str(prod_dir / f"{clip_name}_rendered.mp4")
    output_thumb = str(thumb_dir / f"{clip_name}_thumb.jpg")

    # Determine render settings from config
    ken_burns = config.get("ken_burns", True)
    image_duration = config.get("image_duration", 5.0)

    # Render using the list of background paths (supports single or slideshow)
    rendered_path = await render_video(
        clip_path, 
        background_paths, 
        output_video, 
        image_duration=image_duration,
        ken_burns=ken_burns
    )

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
            "background_path": background_paths[0] if background_paths else None,
            "canvas": {
                "width": CANVAS_WIDTH,
                "height": CANVAS_HEIGHT,
                "fps": CANVAS_FPS,
            },
        },
    }
