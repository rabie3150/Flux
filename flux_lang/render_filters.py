"""Language Shorts render filters for FFmpeg.

Provides drawtext filter primitives and word-block filter construction.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from flux_lang.utils import get_logger

logger = get_logger(__name__)

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
CANVAS_FPS = 30


def _even(n: float) -> int:
    """Return the nearest even integer >= *n* (required by many encoders)."""
    return int(n) + (int(n) % 2)


def _resolve_font_path(config: dict[str, Any], weight: str = "Bold") -> str:
    """Resolve a usable font file path across platforms.

    Priority:
    1. Explicit ``config["style"]["fontfile"]`` override
    2. Bundled font in project root or package ``assets/fonts/``
    3. Platform-detected system font
    """
    # 1. Config override
    style = config.get("style", {})
    explicit = style.get("fontfile")
    if explicit and Path(explicit).exists():
        return explicit.replace("\\", "/").replace(":", "\\:")

    # 2. Bundled font (project-local / package-local candidates)
    candidates_bundled = [
        Path(__file__).resolve().parent / "assets" / "fonts" / f"Roboto-{weight}.ttf",
        Path(__file__).resolve().parent / "assets" / "fonts" / "Roboto-Bold.ttf",
        Path(__file__).resolve().parent / "assets" / "fonts" / "Roboto-Medium.ttf",
        Path(__file__).resolve().parent / "assets" / "fonts" / "Inter-Bold.ttf",
        Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Inter-Bold.ttf",
    ]
    for bundled in candidates_bundled:
        if bundled.exists():
            return str(bundled).replace("\\", "/").replace(":", "\\:")

    # 3. Platform detection

    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        candidates = [
            os.path.join(windir, "Fonts", "arial.ttf"),
            os.path.join(windir, "Fonts", "segoeui.ttf"),
        ]
    else:
        # Linux / macOS
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]

    for path in candidates:
        if os.path.exists(path):
            return path.replace("\\", "/").replace(":", "\\:")

    # Final fallback — let FFmpeg use its built-in default
    logger.warning("No font file found; FFmpeg will use its built-in default")
    return ""


def escape_text(text: str) -> str:
    """Escape text for use in FFmpeg drawtext filter."""
    if not text:
        return ""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    return text


def build_liven_up_filter(
    width: int,
    height: int,
    *,
    speed: float = 0.3,
    zoom_pct: float = 25.0,
) -> str:
    """Ken Burns-style slow pan + zoom using ``scale`` + ``crop``."""
    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be positive, got {width}x{height}")
    if zoom_pct <= 0 or speed <= 0:
        return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"

    scale = 1.0 + zoom_pct / 100.0
    sw, sh = _even(width * scale), _even(height * scale)

    x_expr = f"trunc((iw-ow)/2+(iw/12)*sin(t*{0.18 * speed}))"
    y_expr = f"trunc((ih-oh)/2+(ih/16)*cos(t*{0.12 * speed}))"

    return (
        f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}:{x_expr}:{y_expr}"
    )


def build_dim_overlay_filter(opacity: float = 0.35) -> str:
    """Return a drawbox filter that applies a semi-transparent black overlay."""
    if not 0.0 <= opacity <= 1.0:
        opacity = 0.35
    return f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{opacity:.2f}:t=fill"


def build_drawtext(
    text: str,
    start_time: float,
    end_time: float,
    y_pos: int | str,
    config: dict[str, Any],
    fontsize: int = 64,
    fontcolor: str = "white",
    shadow: bool = True,
    alpha: str | None = None,
    weight: str = "Bold",
) -> str:
    """Build a drawtext filter string for a timed overlay."""
    escaped = escape_text(text)
    font_path = _resolve_font_path(config, weight=weight)

    font_clause = f"fontfile='{font_path}':" if font_path else ""

    filter_str = (
        f"drawtext={font_clause}"
        f"text='{escaped}':"
        f"enable='between(t,{start_time:.2f},{end_time:.2f})':"
        f"fontsize={fontsize}:"
        f"fontcolor={fontcolor}:"
        f"x=(w-tw)/2:"
        f"y={y_pos}"
    )

    if shadow:
        filter_str += ":shadowcolor=black@0.6:shadowx=4:shadowy=4"

    if alpha:
        filter_str += f":alpha='{alpha}'"

    return filter_str


def _alpha_fade_expr(start_time: float, end_time: float, fade_in: float, fade_out: float) -> str:
    """Build an FFmpeg alpha expression for smooth fade in / out."""
    fade_in = max(fade_in, 0.05)
    fade_out = max(fade_out, 0.05)

    fade_in_end = min(start_time + fade_in, end_time - 0.05)
    fade_out_start = max(end_time - fade_out, fade_in_end + 0.05)

    return (
        f"if(lt(t,{fade_in_end}),"
        f"(t-{start_time})/{fade_in_end - start_time},"
        f"if(lt(t,{fade_out_start}),1,"
        f"({end_time}-t)/{end_time - fade_out_start}))"
    )


def build_animated_text(
    text: str,
    start_time: float,
    end_time: float,
    y_pos: int | str,
    config: dict[str, Any],
    fontsize: int = 64,
    fontcolor: str = "white",
    shadow: bool = True,
    fade_in: float = 0.4,
    fade_out: float = 0.3,
    weight: str = "Bold",
) -> str:
    """Build a drawtext filter with alpha-based fade in/out animation."""
    alpha = _alpha_fade_expr(start_time, end_time, fade_in, fade_out)
    return build_drawtext(
        text, start_time, end_time, y_pos, config,
        fontsize=fontsize, fontcolor=fontcolor, shadow=shadow, alpha=alpha,
        weight=weight,
    )


def build_intro_filters(
    word_count: int,
    lang_name: str,
    theme: str,
    intro_duration: float,
    config: dict[str, Any],
) -> list[str]:
    """Build animated intro text filters designed to hook viewers."""
    style = config.get("style", {})
    accent = style.get("accent_color", "#FFD700")
    text_color = style.get("text_color", "#FFFFFF")
    canvas = config.get("canvas", {})
    canvas_h = canvas.get("height", 1920)

    filters = []

    line1 = f"{word_count} {lang_name} {theme.title()} Words"
    filters.append(
        build_animated_text(
            line1,
            start_time=0.0,
            end_time=intro_duration,
            y_pos=int(canvas_h * 0.40625),
            config=config,
            fontsize=84,
            fontcolor=text_color,
            fade_in=0.35,
            fade_out=0.3,
        )
    )

    filters.append(
        build_animated_text(
            "You Need to Know",
            start_time=0.45,
            end_time=intro_duration,
            y_pos=int(canvas_h * 0.47917),
            config=config,
            fontsize=64,
            fontcolor=accent,
            fade_in=0.35,
            fade_out=0.3,
        )
    )

    filters.append(
        build_animated_text(
            "Watch to the end",
            start_time=1.8,
            end_time=intro_duration,
            y_pos=int(canvas_h * 0.54688),
            config=config,
            fontsize=42,
            fontcolor="#DDDDDD",
            shadow=True,
            fade_in=0.3,
            fade_out=0.2,
        )
    )

    return filters


def build_outro_filters(
    outro_start: float,
    outro_end: float,
    config: dict[str, Any],
) -> list[str]:
    """Build animated outro text filters."""
    style = config.get("style", {})
    text_color = style.get("text_color", "#FFFFFF")
    accent = style.get("accent_color", "#FFD700")
    canvas = config.get("canvas", {})
    canvas_h = canvas.get("height", 1920)

    return [
        build_animated_text(
            "Follow for more",
            start_time=outro_start,
            end_time=outro_end,
            y_pos=int(canvas_h * 0.42708),
            config=config,
            fontsize=80,
            fontcolor=text_color,
            fade_in=0.4,
            fade_out=0.3,
        ),
        build_animated_text(
            "Drop a comment if you learned something new",
            start_time=outro_start + 0.6,
            end_time=outro_end,
            y_pos=int(canvas_h * 0.48958),
            config=config,
            fontsize=44,
            fontcolor=accent,
            fade_in=0.4,
            fade_out=0.3,
        ),
    ]


def _highlight_word(text: str, word: str, color: str = "#FFD700") -> str:
    """Wrap first occurrence of *word* in FFmpeg drawtext color markup."""
    import re
    if not word or not text:
        return text
    pattern = re.compile(rf"\b({re.escape(word)})\b", re.IGNORECASE)
    return pattern.sub(rf"{{\\c{color}}}\1{{\\c}}", text, count=1)


def wrap_text(text: str, max_chars: int = 18) -> str:
    """Wrap text to multiple lines by inserting newlines at word boundaries."""
    if not text or len(text) <= max_chars:
        return text
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for w in words:
        if current_length + len(w) + (1 if current_line else 0) > max_chars:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w]
            current_length = len(w)
        else:
            current_line.append(w)
            current_length += len(w) + (1 if current_line else 0)
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)


def build_word_block_filters(
    word_index: int,
    total_words: int,
    start_time: float,
    source_text: str,
    target_text: str,
    phonetic_text: str,
    config: dict[str, Any],
    example_sentence: str = "",
) -> list[str]:
    """Build all drawtext filters for a single word pair."""
    timing = config.get("timing", {})
    style = config.get("style", {})
    canvas = config.get("canvas", {})
    canvas_h = canvas.get("height", 1920)

    en_display = timing.get("en_display_secs", 2.5)
    reveal = timing.get("reveal_hold_secs", 3.0)
    reveal_transition = timing.get("reveal_transition_secs", 0.5)

    sentence_display = timing.get("sentence_display_secs", 0.0)
    block_end = start_time + en_display + reveal + sentence_display
    filters = []

    text_color = style.get("text_color", "#FFFFFF")
    accent = style.get("accent_color", "#FFD700")
    phonetic_color = style.get("phonetic_color", "#AAAAAA")

    # Card layout geometry (centered single card of height 800)
    card_height = int(canvas_h * 0.4167)  # 800 pixels
    (canvas_h - card_height) // 2  # 560

    # 1. Source text (centered inside the top card section)
    # The divider line is at 44% of card height (relative coordinate y = 30 + 325 = 355)
    # Absolute divider coordinate = 560 + 355 = 915.
    # Center of upper section = 590 + (915 - 590)/2 = 752.
    top_center_y = 752
    source_font_size = style.get("source_font_size", 140)
    source_y_pos = f"{top_center_y}-th/2"

    wrapped_source = wrap_text(source_text, max_chars=12)

    filters.append(
        build_drawtext(
            wrapped_source,
            start_time,
            block_end,
            y_pos=source_y_pos,
            config=config,
            fontsize=source_font_size,
            fontcolor=text_color,
        )
    )

    # 2. Target text and Phonetic text (centered inside the bottom card section)
    # Center of lower section = 915 + (1330 - 915)/2 = 1122.
    bottom_center_y = 1122
    target_font_size = style.get("target_font_size", 140)
    phonetic_font_size = style.get("phonetic_font_size", 64)
    difficulty = config.get("difficulty", "beginner")

    show_phonetic = bool(phonetic_text and difficulty == "beginner")

    wrapped_target = wrap_text(target_text, max_chars=12)

    if show_phonetic:
        # Separate y positions centered around their respective midpoints to allow wrapping
        target_y_pos = "1070-th/2"
        phonetic_y_pos = "1200-th/2"
    else:
        target_y_pos = f"{bottom_center_y}-th/2"
        phonetic_y_pos = ""

    target_start = start_time + en_display
    filters.append(
        build_animated_text(
            wrapped_target,
            start_time=target_start,
            end_time=block_end,
            y_pos=target_y_pos,
            config=config,
            fontsize=target_font_size,
            fontcolor=accent,  # Highlight target language in different color based on theory (gold/yellow accent)
            fade_in=reveal_transition,
            fade_out=0.3,
        )
    )

    if show_phonetic:
        # Remove any existing enclosing brackets/slashes/parentheses and wrap in square brackets
        cleaned = phonetic_text.strip()
        while len(cleaned) >= 2 and cleaned[0] in "[(/" and cleaned[-1] in ")]/":
            cleaned = cleaned[1:-1].strip()
        cleaned_phonetic = f"[{cleaned.lower()}]"


        wrapped_phonetic = wrap_text(cleaned_phonetic, max_chars=16)
        filters.append(
            build_animated_text(
                wrapped_phonetic,
                start_time=target_start,
                end_time=block_end,
                y_pos=phonetic_y_pos,
                config=config,
                fontsize=phonetic_font_size,
                fontcolor=phonetic_color,
                fade_in=reveal_transition,
                fade_out=0.2,
                weight="Medium",  # Lighter weight for phonetics
            )
        )

    # 3. Example sentence (below target text, inside card)
    if example_sentence:
        sentence_start = start_time + en_display + reveal
        sentence_end = sentence_start + sentence_display
        sentence_font_size = 48
        sentence_color = "#DDDDDD"
        wrapped_sentence = wrap_text(example_sentence, max_chars=24)
        highlighted = _highlight_word(wrapped_sentence, target_text)

        if show_phonetic:
            sentence_y_pos = "1240-th/2"
        else:
            sentence_y_pos = "1280-th/2"

        filters.append(
            build_animated_text(
                wrapped_sentence,
                start_time=sentence_start,
                end_time=sentence_end,
                y_pos=sentence_y_pos,
                config=config,
                fontsize=sentence_font_size,
                fontcolor=sentence_color,
                fade_in=0.3,
                fade_out=0.2,
                weight="Regular",
            )
        )

    return filters

