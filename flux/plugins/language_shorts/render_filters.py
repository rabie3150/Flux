"""
Language Shorts render filters for FFmpeg.
"""

from __future__ import annotations

import shlex

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
CANVAS_FPS = 30

def escape_text(text: str) -> str:
    """Escape text for use in FFmpeg drawtext filter."""
    if not text:
        return ""
    # drawtext requires very specific escaping:
    # First escape backslashes, then single quotes, then colons
    text = text.replace('\\', '\\\\')
    text = text.replace("'", "\\'")
    text = text.replace(':', '\\:')
    return text

def build_drawtext(
    text: str,
    start_time: float,
    end_time: float,
    y_pos: int,
    fontsize: int = 64,
    fontcolor: str = "white",
    shadow: bool = True
) -> str:
    """Build a drawtext filter string for a timed overlay."""
    escaped = escape_text(text)
    
    # Using Arial or standard font if Inter is not embedded. 
    # For Termux/Linux, we might want to pass a specific fontfile.
    # We'll use a standard font that usually exists or let ffmpeg fallback.
    filter_str = (
        f"drawtext=text='{escaped}':"
        f"enable='between(t,{start_time:.2f},{end_time:.2f})':"
        f"fontsize={fontsize}:"
        f"fontcolor={fontcolor}:"
        f"x=(w-tw)/2:"
        f"y={y_pos}"
    )
    
    if shadow:
        filter_str += ":shadowcolor=black@0.6:shadowx=3:shadowy=3"
        
    return filter_str

def build_word_block_filters(
    word_index: int,
    start_time: float,
    source_text: str,
    target_text: str,
    phonetic_text: str,
    config: dict
) -> list[str]:
    """Build all drawtext filters for a single word pair."""
    timing = config.get("timing", {})
    style = config.get("style", {})
    
    en_display = timing.get("en_display_secs", 2.0)
    countdown = timing.get("countdown_secs", 3.0)
    reveal = timing.get("reveal_hold_secs", 3.0)
    
    block_end = start_time + en_display + countdown + reveal
    filters = []
    
    # 1. Source text (English) appears and stays
    filters.append(
        build_drawtext(
            source_text,
            start_time,
            block_end,
            y_pos=600,
            fontsize=style.get("source_font_size", 64)
        )
    )
    
    # 2. Countdown 3, 2, 1
    countdown_y = 1000
    countdown_size = style.get("countdown_font_size", 120)
    countdown_color = style.get("countdown_color", "yellow")
    
    for i in range(int(countdown)):
        c_start = start_time + en_display + i
        c_end = c_start + 1.0
        num = str(int(countdown) - i)
        filters.append(
            build_drawtext(
                num, c_start, c_end, countdown_y, 
                fontsize=countdown_size, fontcolor=countdown_color
            )
        )
        
    # 3. Target text (Italian) appears
    target_start = start_time + en_display + countdown
    filters.append(
        build_drawtext(
            target_text,
            target_start,
            block_end,
            y_pos=1000,
            fontsize=style.get("target_font_size", 64)
        )
    )
    
    # 4. Phonetic
    if phonetic_text:
        filters.append(
            build_drawtext(
                phonetic_text,
                target_start,
                block_end,
                y_pos=1150,
                fontsize=style.get("phonetic_font_size", 36),
                fontcolor="gray"
            )
        )
        
    # 5. Progress dots (e.g. word 1 of 5)
    total_words = config.get("words_per_video", 5)
    dots = " ".join(["●" if j == word_index else "○" for j in range(total_words)])
    filters.append(
        build_drawtext(
            dots,
            start_time,
            block_end,
            y_pos=1700,
            fontsize=40,
            fontcolor="white",
            shadow=False
        )
    )
    
    return filters
