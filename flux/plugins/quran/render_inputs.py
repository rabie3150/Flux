"""FFmpeg input assembly and filter-graph construction.

This module knows **nothing** about running FFmpeg — it only builds the
``-i`` argument list and the ``-filter_complex`` string.  That makes it
easy to test offline (just inspect strings).
"""

from __future__ import annotations

import math
from pathlib import Path

from flux.plugins.quran.render_filters import (
    CANVAS_FPS,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    build_fg_filter,
    build_liven_up_filter,
    build_static_bg_filter,
    build_overlay_filter,
)

__all__ = ["assemble_inputs_and_filtergraph", "resolve_durations"]

# Valid text-shadow modes (soft is default)
_SHADOW_MODES = {"none", "hard", "soft", "center_strip", "vignette"}


def _is_video(path: str) -> bool:
    """Return True if *path* points to a video file."""
    return Path(path).suffix.lower() in (".mp4", ".mov", ".webm", ".mkv")


def resolve_durations(
    backgrounds: list[str],
    clip_duration: float,
    image_duration: float = 5.0,
    timing_set: list[float] | None = None,
) -> list[float]:
    """Return a per-image duration list that covers at least *clip_duration*.

    If *timing_set* is provided, its values are cycled.  Otherwise every
    image uses *image_duration*.

    The list is truncated so ``sum(durations) >= clip_duration`` but
    never exceeds 60 segments (FFmpeg input safety cap).
    """
    if timing_set:
        base = list(timing_set)
    else:
        base = [image_duration]

    if not base or any(d <= 0 for d in base):
        raise ValueError("timing_set/image_duration must contain positive values")

    durations: list[float] = []
    idx = 0
    while sum(durations) < clip_duration and len(durations) < 60:
        durations.append(base[idx % len(base)])
        idx += 1

    return durations


def _repeat_backgrounds(
    backgrounds: list[str],
    durations: list[float],
) -> list[str]:
    """Duplicate *backgrounds* so we have one entry per *duration* slot."""
    needed = len(durations)
    repeated: list[str] = []
    while len(repeated) < needed:
        repeated.extend(backgrounds)
    return repeated[:needed]


def _validate_shadow(text_shadow: str) -> str:
    """Return a valid shadow mode, falling back to ``"soft"``."""
    import logging
    logging.getLogger(__name__).info("SHADOW_CODE_VERSION: 2026-05-01-v2, input=%r", text_shadow)
    if text_shadow in _SHADOW_MODES:
        return text_shadow
    return "soft"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assemble_inputs_and_filtergraph(
    clip_path: str,
    background_paths: list[str],
    *,
    clip_duration: float,
    image_duration: float = 5.0,
    ken_burns: bool = True,
    timing_set: list[float] | None = None,
    text_shadow: str = "soft",
) -> tuple[list[str], str]:
    """Build FFmpeg ``-i`` args and the ``-filter_complex`` string.

    Args:
        clip_path: Path to the Quran clip.
        background_paths: One or more background images / videos.
        clip_duration: Duration of the clip in seconds (used to size
            the slideshow).
        image_duration: Seconds each image is shown when no timing_set
            is provided.
        ken_burns: Whether to apply slow pan/zoom to images.
        timing_set: Optional list of per-image durations (cycled as
            needed).  E.g. ``[6.0, 7.0, 8.0]`` for a slow set.
        text_shadow: Contrast helper for white text on bright
            backgrounds.  One of ``"none"``, ``"hard"``, ``"soft"``,
            ``"center_strip"``, ``"vignette"``.  Default is ``"soft"``.

    Returns:
        ``(ffmpeg_input_args, filter_complex_string)``

    Input layout
    ------------
    Input 0 is **always** the clip.  Backgrounds are inputs 1..N.
    Audio is therefore always ``-map 0:a?``.
    """
    if not background_paths:
        raise ValueError("background_paths must not be empty")

    text_shadow = _validate_shadow(text_shadow)

    args: list[str] = ["-i", clip_path]
    filter_parts: list[str] = []

    # ------------------------------------------------------------------
    # Background branch
    # ------------------------------------------------------------------
    if _is_video(background_paths[0]):
        # Video background — single file only, loop and mute it
        args.extend(["-stream_loop", "-1", "-an", "-i", background_paths[0]])
        bg_filter = build_static_bg_filter(CANVAS_WIDTH, CANVAS_HEIGHT)
        filter_parts.append(f"[1:v]{bg_filter}[bg]")

    elif len(background_paths) == 1:
        # Single static image — loop indefinitely
        args.extend(["-loop", "1", "-i", background_paths[0]])
        bg_filter = (
            build_liven_up_filter(CANVAS_WIDTH, CANVAS_HEIGHT)
            if ken_burns
            else build_static_bg_filter(CANVAS_WIDTH, CANVAS_HEIGHT)
        )
        filter_parts.append(f"[1:v]{bg_filter},setsar=1,fps={CANVAS_FPS}[bg]")

    else:
        # Slideshow — compute per-image durations, repeat backgrounds
        durations = resolve_durations(
            background_paths, clip_duration, image_duration, timing_set
        )
        repeated = _repeat_backgrounds(background_paths, durations)

        seg_labels: list[str] = []
        for idx, (bg, dur) in enumerate(zip(repeated, durations)):
            args.extend(["-loop", "1", "-i", bg])
            in_label = idx + 1  # clip is input 0
            seg_label = f"seg{idx}"
            seg_labels.append(f"[{seg_label}]")
            liven = (
                build_liven_up_filter(CANVAS_WIDTH, CANVAS_HEIGHT, phase_offset=idx * 1.5)
                if ken_burns
                else build_static_bg_filter(CANVAS_WIDTH, CANVAS_HEIGHT)
            )
            filter_parts.append(
                f"[{in_label}:v]{liven},"
                f"trim=duration={dur:.3f},"
                f"setsar=1,fps={CANVAS_FPS}[{seg_label}]"
            )

        concat_str = "".join(seg_labels)
        filter_parts.append(
            f"{concat_str}concat=n={len(repeated)}:v=1:a=0[bg]"
        )

    # ------------------------------------------------------------------
    # Foreground (clip) — colorkey + scale + alpha
    # ------------------------------------------------------------------
    fg_filter = build_fg_filter(CANVAS_WIDTH, CANVAS_HEIGHT)
    filter_parts.append(f"[0:v]{fg_filter}[fg]")

    # ------------------------------------------------------------------
    # Text shadow / contrast treatments
    # ------------------------------------------------------------------
    if text_shadow == "none":
        filter_parts.append(
            build_overlay_filter("bg", "fg", "video")
        )

    elif text_shadow in ("hard", "soft"):
        # Duplicate the clip, turn it black, blur if soft, offset behind
        blur = ",boxblur=3:3" if text_shadow == "soft" else ""
        filter_parts.append(
            f"[fg]split[fg_orig][shadow];"
            f"[shadow]colorchannelmixer="
            f"0:0:0:0:0:0:0:0:0:0:0:0:0:0:0:1"
            f"{blur}[shadow_out];"
            f"[bg][shadow_out]overlay=(W-w)/2+3:(H-h)/2+3[bg_shadow];"
            f"[bg_shadow][fg_orig]overlay=(W-w)/2:(H-h)/2:shortest=1,"
            f"format=yuv420p[video]"
        )

    elif text_shadow == "center_strip":
        # Semi-transparent black bar across the text region
        filter_parts.append(
            f"[bg]drawbox=x=0:y=(ih-400)/2:w=iw:h=400:"
            f"color=black@0.5:t=fill[bg_box];"
            f"[bg_box][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,"
            f"format=yuv420p[video]"
        )

    elif text_shadow == "vignette":
        # Subtle full-frame dimming + contrast boost
        filter_parts.append(
            f"[bg]eq=brightness=-0.15:contrast=1.1[bg_dim];"
            f"[bg_dim][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,"
            f"format=yuv420p[video]"
        )

    return args, ";".join(filter_parts)
