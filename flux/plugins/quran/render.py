"""Quran Shorts render pipeline — FFmpeg-based video composition.

Public API
----------
- ``render_video`` – low-level FFmpeg orchestrator.
- ``extract_thumbnail`` – frame extraction for previews.
- ``render_from_ingredients`` – high-level wrapper used by the plugin.

Internal helpers live in sibling modules so they can be imported and
unit-tested in isolation:

* ``render_filters`` – FFmpeg filter-string primitives.
* ``render_inputs``   – input-list + filter-graph assembler.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from flux.config import settings
from flux.logger import get_logger
from flux.plugins.quran.render_filters import CANVAS_FPS, CANVAS_HEIGHT, CANVAS_WIDTH
from flux.plugins.quran.render_inputs import assemble_inputs_and_filtergraph

logger = get_logger(__name__)

__all__ = ["render_video", "extract_thumbnail", "render_from_ingredients"]

# Encoding presets (mobile-friendly)
_ENCODE_PRESET = "fast"
_ENCODE_CRF = 26


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _production_dir() -> Path:
    return Path(settings.storage_path) / "library" / "production"


def _thumbnails_dir() -> Path:
    return Path(settings.storage_path) / "thumbnails"


# ---------------------------------------------------------------------------
# Input normalisation
# ---------------------------------------------------------------------------

def _normalize_backgrounds(background_paths: str | list[str] | tuple[str, ...]) -> list[str]:
    """Coerce *background_paths* into a list of strings.

    Guards against the common bug where a single string is treated as
    an iterable of characters.
    """
    if isinstance(background_paths, str):
        return [background_paths]

    result = list(background_paths)

    # If every element is a single character, we probably got a string
    # that was iterated character-by-character.
    if result and all(isinstance(x, str) and len(x) == 1 for x in result):
        return ["".join(result)]

    return result


# ---------------------------------------------------------------------------
# Low-level FFmpeg runner
# ---------------------------------------------------------------------------

async def _run_ffmpeg(
    *args: str,
    timeout: float = 300.0,
) -> tuple[int, str, str]:
    """Run FFmpeg. Returns ``(returncode, stdout, stderr)``."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + list(args)
    logger.debug("FFmpeg cmd: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
    except NotImplementedError:
        logger.warning("asyncio.create_subprocess_exec not supported; using sync fallback.")
        import subprocess

        def _sync_run():
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
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
            logger.debug("Failed to kill timed-out FFmpeg: %s", e)
        return -1, "", f"FFmpeg timed out after {timeout}s"
    except FileNotFoundError:
        logger.error("FFmpeg not found in PATH")
        return -1, "", "FFmpeg not found in PATH"


async def _probe_duration(path: str) -> float:
    """Return media duration in seconds using ffprobe.

    Falls back to *30.0* if the file cannot be probed.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        return float(stdout.decode("utf-8", errors="replace").strip())
    except NotImplementedError:
        logger.warning("asyncio subprocess not supported; using sync fallback for ffprobe.")
        import subprocess

        def _sync_probe():
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30.0,
            )
            return p.stdout.strip()

        try:
            stdout_text = await asyncio.to_thread(_sync_probe)
            return float(stdout_text)
        except (ValueError, TypeError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Sync ffprobe fallback failed for %s: %s", path, exc)
            return 30.0
    except (ValueError, TypeError, asyncio.TimeoutError, OSError) as exc:
        logger.warning("Failed to probe duration for %s: %s", path, exc)
        return 30.0


# ---------------------------------------------------------------------------
# Public render API
# ---------------------------------------------------------------------------

async def render_video(
    clip_path: str,
    background_paths: str | list[str],
    output_path: str,
    *,
    duration: float | None = None,
    image_duration: float = 5.0,
    ken_burns: bool = True,
    timing_set: list[float] | None = None,
    text_shadow: str = "soft",
) -> str:
    """Render a Quran clip composited over a background.

    Args:
        clip_path: Path to the Quran clip MP4 (black background).
        background_paths: One or more background images / videos.
        output_path: Where to write the rendered MP4.
        duration: Optional duration limit in seconds (trims output).
        image_duration: Seconds each image is shown in a slideshow.
        ken_burns: Whether to apply slow pan/zoom to images.
        timing_set: Optional list of per-image durations.  Cycled as
            needed to cover the clip length.
        text_shadow: Contrast helper for white text on bright
            backgrounds.  One of ``"none"``, ``"hard"``, ``"soft"``,
            ``"center_strip"``, ``"vignette"``.  Default ``"soft"``.

    Returns:
        Absolute path to the rendered MP4.

    Raises:
        ValueError: On invalid arguments (missing backgrounds, etc.).
        RuntimeError: If FFmpeg fails or output is not created.
    """
    backgrounds = _normalize_backgrounds(background_paths)

    if not backgrounds:
        raise ValueError("At least one background is required")

    for bg in backgrounds:
        if not Path(bg).exists():
            raise FileNotFoundError(f"Background not found: {bg}")
    if not Path(clip_path).exists():
        raise FileNotFoundError(f"Clip not found: {clip_path}")

    # Probe clip so the slideshow can be sized to match
    clip_duration = await _probe_duration(clip_path)
    if duration is not None:
        clip_duration = min(clip_duration, duration)

    # Build inputs + filtergraph
    input_args, filter_complex = assemble_inputs_and_filtergraph(
        clip_path,
        backgrounds,
        clip_duration=clip_duration,
        image_duration=image_duration,
        ken_burns=ken_burns,
        timing_set=timing_set,
        text_shadow=text_shadow,
    )

    args = input_args + [
        "-filter_complex",
        filter_complex,
        "-map",
        "[video]",
        "-map",
        "0:a?",  # clip is always input 0
        "-c:v",
        "libx264",
        "-preset",
        _ENCODE_PRESET,
        "-crf",
        str(_ENCODE_CRF),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
    ]

    if duration is not None:
        args.extend(["-t", str(duration)])

    args.append(output_path)

    returncode, _stdout, stderr = await _run_ffmpeg(*args)

    if returncode != 0:
        raise RuntimeError(
            f"FFmpeg render failed for {Path(clip_path).name} "
            f"(code {returncode}): {stderr[:500]}"
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
    *,
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
        "-ss",
        str(time_sec),
        "-i",
        video_path,
        "-vframes",
        "1",
        "-q:v",
        "2",
        "-vf",
        f"scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}:force_original_aspect_ratio=decrease",
        output_path,
    ]

    returncode, _stdout, stderr = await _run_ffmpeg(*args)
    if returncode != 0:
        raise RuntimeError(
            f"Thumbnail extraction failed for {Path(video_path).name} "
            f"(code {returncode}): {stderr[:500]}"
        )
    if not Path(output_path).exists():
        raise RuntimeError(f"Thumbnail missing after extraction: {output_path}")

    logger.info("Extracted thumbnail: %s", output_path)
    return output_path


async def render_from_ingredients(
    clip_path: str,
    background_paths: str | list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    """High-level render orchestrator for the Quran plugin.

    Args:
        clip_path: Path to approved Quran clip.
        background_paths: List of approved background image/video paths.
        config: Pipeline config (may include timing_sets, canvas, etc.).

    Returns:
        Dict with keys: file_path, thumbnail_path, duration, metadata.
    """
    backgrounds = _normalize_backgrounds(background_paths)
    if not backgrounds:
        raise ValueError("At least one background is required for rendering")

    prod_dir = _production_dir()
    thumb_dir = _thumbnails_dir()
    prod_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)

    clip_name = Path(clip_path).stem
    output_video = str(prod_dir / f"{clip_name}_rendered.mp4")
    output_thumb = str(thumb_dir / f"{clip_name}_thumb.jpg")

    # Extract render settings from pipeline config
    production_cfg = config.get("production", {})
    ken_burns = production_cfg.get("ken_burns", config.get("ken_burns", True))
    image_duration = production_cfg.get("image_duration", config.get("image_duration", 5.0))

    # Resolve timing set (if configured)
    timing_set: list[float] | None = None
    raw_timing_sets = production_cfg.get("timing_sets") or config.get("timing_sets")
    if raw_timing_sets:
        # timing_sets is a list of {"name": str, "durations": list[float]}
        selected_name = production_cfg.get("timing_set") or config.get("timing_set")
        for ts in raw_timing_sets:
            if isinstance(ts, dict) and ts.get("durations"):
                if selected_name is None or ts.get("name") == selected_name:
                    timing_set = [float(d) for d in ts["durations"]]
                    break

    # Allow top-level config to override duration
    duration: float | None = None
    raw_duration = config.get("duration")
    if raw_duration is not None:
        try:
            duration = float(raw_duration) or None
        except (ValueError, TypeError):
            logger.warning("Invalid duration in config: %s", raw_duration)

    text_shadow = production_cfg.get("text_shadow", config.get("text_shadow", "soft"))

    rendered_path = await render_video(
        clip_path,
        backgrounds,
        output_video,
        duration=duration,
        image_duration=float(image_duration),
        ken_burns=bool(ken_burns),
        timing_set=timing_set,
        text_shadow=str(text_shadow),
    )

    thumb_path = await extract_thumbnail(rendered_path, output_thumb, time_sec=2.0)

    return {
        "file_path": rendered_path,
        "thumbnail_path": thumb_path,
        "duration_secs": duration,
        "metadata": {
            "render_method": "video_compose",
            "clip_path": clip_path,
            "background_paths": backgrounds,
            "canvas": {
                "width": CANVAS_WIDTH,
                "height": CANVAS_HEIGHT,
                "fps": CANVAS_FPS,
            },
            "ken_burns": ken_burns,
            "timing_set": timing_set,
            "text_shadow": text_shadow,
        },
    }
