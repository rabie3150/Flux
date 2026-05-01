"""FFmpeg filter primitives for the Quran render pipeline.

Each function returns a filter *string* suitable for FFmpeg's
``-filter_complex`` graph.  They are intentionally small, stateless,
and easy to unit-test in isolation.

Example::

    >>> from flux.plugins.quran.render_filters import build_liven_up_filter
    >>> build_liven_up_filter(1080, 1920, speed=0.5)
    "scale=1350:2400:force_original_aspect_ratio=increase,..."
"""

from __future__ import annotations

__all__ = [
    "CANVAS_WIDTH",
    "CANVAS_HEIGHT",
    "CANVAS_FPS",
    "build_scale_filter",
    "build_liven_up_filter",
    "build_static_bg_filter",
    "build_fg_filter",
    "build_overlay_filter",
]

# ---------------------------------------------------------------------------
# Canvas constants
# ---------------------------------------------------------------------------

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
CANVAS_FPS = 30

# Colorkey defaults for black-background Quran clips
_COLORKEY_COLOR = "0x000000"
_COLORKEY_SIMILARITY = 0.3
_COLORKEY_BLEND = 0.1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _even(n: float) -> int:
    """Return the nearest even integer >= *n* (required by many encoders)."""
    return int(n) + (int(n) % 2)


# ---------------------------------------------------------------------------
# Background effects
# ---------------------------------------------------------------------------

def build_scale_filter(width: int, height: int) -> str:
    """Scale maintaining aspect ratio, fitting inside the given box.

    Ensures output dimensions are divisible by 2 for encoder compatibility.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be positive, got {width}x{height}")
    return (
        f"scale='if(gt(iw/ih,{width}/{height}),{width},-2)':"
        f"'if(gt(iw/ih,{width}/{height}),-2,{height})'"
    )


def build_liven_up_filter(
    width: int,
    height: int,
    *,
    speed: float = 1.0,
    zoom_pct: float = 25.0,
    phase_offset: float = 0.0,
) -> str:
    """Ken Burns-style slow pan + zoom using ``scale`` + ``crop``.

    The crop centre oscillates very slowly (periods ~35 s / ~52 s by
    default).  ``speed`` is a multiplier on those frequencies — use
    ``0.5`` for half speed, ``2.0`` for double.

    ``zoom_pct`` controls how much the image is scaled up before
    cropping (e.g. ``25`` means 1.25×).

    ``phase_offset`` (radians) shifts the starting phase so multiple
    slideshow images don't move in lock-step.

    The ``crop`` coordinates are wrapped with ``trunc()`` so FFmpeg
    never receives a fractional pixel value.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be positive, got {width}x{height}")
    if zoom_pct <= 0:
        raise ValueError("zoom_pct must be positive")

    scale = 1.0 + zoom_pct / 100.0
    sw, sh = _even(width * scale), _even(height * scale)

    # trunc() guarantees integer coordinates for the crop filter
    x_expr = f"trunc((iw-ow)/2+(iw/12)*sin(t*{0.18 * speed}+{phase_offset}))"
    y_expr = f"trunc((ih-oh)/2+(ih/16)*cos(t*{0.12 * speed}+{phase_offset}))"

    return (
        f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}:{x_expr}:{y_expr}"
    )


def build_static_bg_filter(width: int, height: int, fps: int = CANVAS_FPS) -> str:
    """No motion — just scale to canvas and normalise frame-rate."""
    return f"{build_scale_filter(width, height)},setsar=1,fps={fps}"


# ---------------------------------------------------------------------------
# Foreground (Quran clip) effects
# ---------------------------------------------------------------------------

def build_colorkey_filter(
    color: str = _COLORKEY_COLOR,
    similarity: float = _COLORKEY_SIMILARITY,
    blend: float = _COLORKEY_BLEND,
) -> str:
    """Remove black background from Quran clips."""
    return f"colorkey={color}:{similarity}:{blend}"


def build_fg_filter(width: int, height: int) -> str:
    """Colourkey + scale + add alpha channel for overlay."""
    return (
        f"{build_colorkey_filter()},"
        f"{build_scale_filter(width, height)},"
        f"format=yuva420p"
    )


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

def build_overlay_filter(
    bg_label: str = "bg",
    fg_label: str = "fg",
    output_label: str = "video",
) -> str:
    """Overlay foreground centred on background, trim to shortest."""
    return (
        f"[{bg_label}][{fg_label}]"
        f"overlay=(W-w)/2:(H-h)/2:shortest=1,"
        f"format=yuv420p[{output_label}]"
    )
