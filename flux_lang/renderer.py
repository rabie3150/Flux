"""Language Shorts render pipeline — FFmpeg video composition from TTS + drawtext."""

from __future__ import annotations

import asyncio
import random
import subprocess
import tempfile
from pathlib import Path
from typing import Any


from flux_lang.config import AppConfig
from flux_lang.render_cards import generate_card_overlay, generate_card_mask
from flux_lang.render_filters import (
    build_word_block_filters,
    build_intro_filters,
    build_outro_filters,
    build_liven_up_filter,
    build_dim_overlay_filter,
    CANVAS_FPS,
)
from flux_lang.tts import synthesize
from flux_lang.utils import get_logger, run_ffmpeg

logger = get_logger(__name__)

_OUTRO_TTS_VARIANTS = [
    "Drop a like and tell me in the comments — how many did you get right?",
    "Subscribe if you learned at least one new word today!",
    "Write your favorite word from this video in the comments!",
    "Challenge a friend who needs to see this!",
    "Save this video and watch it again before bed!",
    "Comment below which word surprised you the most!",
]


def _config_dict(cfg: AppConfig) -> dict[str, Any]:
    """Convert AppConfig to plain dict for render_filters compatibility."""
    return cfg.model_dump()


async def _generate_audio_assets(
    words: list[dict[str, Any]],
    config: AppConfig,
    temp_dir: Path,
    on_progress: Any = None,
) -> tuple[list[dict[str, Any]], str | None, str | None, str | None]:
    """Generate TTS audio for intro + all words + outro concurrently."""
    tts_cfg = config.tts
    provider = tts_cfg.provider

    source_voice = tts_cfg.source_voice
    source_voice_fallback = tts_cfg.source_voice_fallback

    target_voice = tts_cfg.target_voice
    target_voice_fallback = tts_cfg.target_voice_fallback

    speaking_rate = tts_cfg.speaking_rate
    tts_params = {"speaking_rate": speaking_rate}

    def _report(step: str, detail: str = "") -> None:
        if on_progress:
            on_progress(step, detail)

    completed = 0
    total_audios = len(words) * 2 + 2  # source + target for each word, plus intro + outro

    async def _synthesize_with_fallback(text: str, voice: str, fallback: str, path: Path) -> None:
        nonlocal completed
        try:
            audio = await synthesize(text, voice_id=voice, provider=provider, params=tts_params)
        except Exception as e:
            logger.warning("Voice %s failed for '%s': %s. Trying fallback %s", voice, text, e, fallback)
            try:
                audio = await synthesize(text, voice_id=fallback, provider=provider, params=tts_params)
            except Exception as fe:
                raise RuntimeError(f"TTS synthesis failed for text '{text}': {fe}") from fe
        path.write_bytes(audio)
        completed += 1
        _report("tts", f"Synthesized {completed}/{total_audios} voiceovers")

    async def _synthesize_optional(text: str, voice: str, path: Path) -> bool:
        nonlocal completed
        try:
            audio = await synthesize(text, voice_id=voice, provider=provider, params=tts_params)
            path.write_bytes(audio)
            completed += 1
            _report("tts", f"Synthesized {completed}/{total_audios} voiceovers")
            return True
        except Exception as e:
            logger.warning("Optional TTS failed for '%s': %s", text, e)
            completed += 1
            _report("tts", f"Synthesized {completed}/{total_audios} voiceovers")
            return False

    intro_path_obj = temp_dir / "intro.wav"
    outro_path_obj = temp_dir / "outro.wav"

    lang_name = config.target_lang_name
    theme = words[0].get("theme", "vocabulary") if words else "vocabulary"
    intro_text = f"[hype] {len(words)} {lang_name} {theme} words you need to know."
    outro_text = random.choice(_OUTRO_TTS_VARIANTS)


    # 1. Intro task
    intro_task = asyncio.create_task(_synthesize_optional(intro_text, source_voice, intro_path_obj))

    # 2. Outro task
    outro_task = asyncio.create_task(_synthesize_optional(outro_text, source_voice, outro_path_obj))

    # 3. Word task lists
    enriched = []
    word_tasks = []
    for i, w in enumerate(words):
        s_path = temp_dir / f"word_{i}_source.wav"
        t_path = temp_dir / f"word_{i}_target.wav"

        word_tasks.append(
            _synthesize_with_fallback(w["source_text"], source_voice, source_voice_fallback, s_path)
        )
        word_tasks.append(
            _synthesize_with_fallback(w["target_text"], target_voice, target_voice_fallback, t_path)
        )

        enriched.append({
            **w,
            "source_audio_path": str(s_path),
            "target_audio_path": str(t_path),
        })

    _report("tts", f"Starting parallel synthesis of {total_audios} voiceovers...")

    # Gather everything
    results = await asyncio.gather(
        intro_task,
        outro_task,
        *word_tasks
    )

    intro_ok = results[0]
    outro_ok = results[1]

    intro_path = str(intro_path_obj) if intro_ok else None
    outro_path = str(outro_path_obj) if outro_ok else None

    # Ding sound effect
    _report("tts", "Generating ding sound effect...")
    ding_path = None
    try:
        ding_wav = temp_dir / "ding.wav"
        ding_cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi",
            "-i", "aevalsrc=0.25*sin(880*2*PI*t)*exp(-5*t):s=48000:c=mono,d=0.4",
            "-acodec", "pcm_s16le",
            "-ar", "48000",
            "-ac", "1",
            str(ding_wav),
        ]
        result = subprocess.run(ding_cmd, capture_output=True, text=True)
        if result.returncode == 0 and ding_wav.exists():
            ding_path = str(ding_wav)
    except Exception as e:
        logger.warning("Ding sound generation failed: %s", e)

    return enriched, intro_path, outro_path, ding_path


async def _generate_card_pngs(
    words: list[dict[str, Any]],
    config: AppConfig,
    temp_dir: Path,
    on_progress: Any = None,
) -> tuple[list[str], str]:
    """Generate rounded-corner card PNGs (one per word) with progress dots, and their common mask."""
    style = config.style
    canvas_w = config.canvas.width
    canvas_h = config.canvas.height

    card_width = int(canvas_w * 0.8889)
    card_height = int(canvas_h * 0.4167)  # 800 pixels

    card_fill = tuple(style.card_fill_rgba)
    card_border = tuple(style.card_border_rgba)
    card_radius = style.card_corner_radius
    card_border_w = style.card_border_width
    padding = 30

    def _report(step: str, detail: str = "") -> None:
        if on_progress:
            on_progress(step, detail)

    _report("cards", f"Generating {len(words)} card overlays and masks...")

    card_paths = []
    for i in range(len(words)):
        card_path = str(temp_dir / f"card_{i}.png")
        generate_card_overlay(
            width=card_width,
            height=card_height,
            output_path=card_path,
            fill_color=card_fill,
            border_color=card_border,
            border_width=card_border_w,
            corner_radius=card_radius,
            divider=True,
            progress_dots=style.progress_dots,
            dot_count=len(words),
            active_dot=i,
            dot_color_active=style.accent_color,
            dot_color_inactive=style.phonetic_color,
        )
        card_paths.append(card_path)

    # Visual card dimensions (excluding shadow padding)
    vis_w = card_width - 2 * padding
    vis_h = card_height - 2 * padding
    mask_path = str(temp_dir / "card_mask.png")
    generate_card_mask(
        width=vis_w,
        height=vis_h,
        output_path=mask_path,
        corner_radius=card_radius,
    )

    return card_paths, mask_path



async def render_video(
    words: list[dict[str, Any]],
    background_paths: list[str],
    output_path: str,
    config: AppConfig,
    on_progress: Any = None,
) -> str:
    """Render the full composite video from word pair data + backgrounds.

    Args:
        words: List of word dicts with source_text, target_text, phonetic keys.
        background_paths: List of background image/video file paths.
        output_path: Where to write the rendered MP4.
        config: AppConfig instance.

    Returns:
        Absolute path to the rendered MP4.
    """
    cfg_dict = _config_dict(config)
    timing = config.timing
    canvas = config.canvas
    style = config.style
    canvas_w = canvas.width
    canvas_h = canvas.height

    intro_dur = timing.intro_duration
    en_display = timing.en_display_secs
    reveal = timing.reveal_hold_secs
    pause = timing.pause_between_secs
    outro_dur = timing.outro_duration
    extra_padding = 1.0

    block_dur = en_display + reveal + pause

    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)

        def _report(step: str, detail: str = "") -> None:
            if on_progress:
                on_progress(step, detail)

        # 1. Generate TTS Audio
        _report("tts", "Starting TTS synthesis...")
        enriched_words, intro_audio_path, outro_audio_path, ding_path = await _generate_audio_assets(
            words, config, temp_dir, on_progress=on_progress
        )
        _report("tts", "TTS complete")

        # 2. Generate card PNGs
        _report("cards", "Generating card overlays and masks...")
        card_paths, card_mask_path = await _generate_card_pngs(enriched_words, config, temp_dir, on_progress=on_progress)
        _report("cards", "Cards and masks complete")

        total_duration = intro_dur + (len(enriched_words) * block_dur) + outro_dur + extra_padding

        # 3. Build FFmpeg inputs
        if not background_paths:
            raise RuntimeError("Cannot render video: background_paths list is empty.")
        bg = background_paths[0]
        if not Path(bg).exists():
            raise FileNotFoundError(f"Background asset not found: {bg}")

        is_video = Path(bg).suffix.lower() in [".mp4", ".mov", ".webm", ".mkv", ".m4v"]

        input_args = []
        if is_video:
            input_args.extend(["-stream_loop", "-1"])
        else:
            input_args.extend(["-loop", "1"])

        input_args.extend(["-t", str(total_duration), "-i", bg])

        # Card overlay inputs (one per word, starting at input index 1)
        card_input_idxs = []
        for card_path in card_paths:
            input_args.extend(["-loop", "1", "-t", str(total_duration), "-i", card_path])
            card_input_idxs.append(len(card_input_idxs) + 1)

        # Card mask input (after all card inputs)
        input_args.extend(["-loop", "1", "-t", str(total_duration), "-i", card_mask_path])

        mask_input_idx = len(card_input_idxs) + 1
        current_input_idx = mask_input_idx + 1

        # Audio inputs + delay filters
        audio_filters = []

        if intro_audio_path:
            input_args.extend(["-i", intro_audio_path])
            intro_idx = current_input_idx
            current_input_idx += 1
            intro_delay_ms = 150
            audio_filters.append(
                f"[{intro_idx}:a]adelay={intro_delay_ms}|{intro_delay_ms},volume=1.2[aintro]"
            )

        for i, w in enumerate(enriched_words):
            input_args.extend(["-i", w["source_audio_path"]])
            s_idx = current_input_idx
            current_input_idx += 1

            input_args.extend(["-i", w["target_audio_path"]])
            t_idx = current_input_idx
            current_input_idx += 1

            block_start = intro_dur + (i * block_dur)

            s_delay_ms = int((block_start + 0.5) * 1000)
            t_delay_ms = int((block_start + en_display + 0.5) * 1000)

            audio_filters.append(f"[{s_idx}:a]adelay={s_delay_ms}|{s_delay_ms}[a{i}s]")
            audio_filters.append(f"[{t_idx}:a]adelay={t_delay_ms}|{t_delay_ms}[a{i}t]")

        if outro_audio_path:
            input_args.extend(["-i", outro_audio_path])
            outro_idx = current_input_idx
            current_input_idx += 1
            outro_start = intro_dur + (len(enriched_words) * block_dur)
            outro_delay_ms = int((outro_start + 0.3) * 1000)
            audio_filters.append(
                f"[{outro_idx}:a]adelay={outro_delay_ms}|{outro_delay_ms},volume=1.1[aoutro]"
            )

        if ding_path:
            input_args.extend(["-i", ding_path])
            ding_idx = current_input_idx
            current_input_idx += 1
            outro_start = intro_dur + (len(enriched_words) * block_dur)
            ding_delay_ms = int((outro_start + 0.1) * 1000)
            audio_filters.append(
                f"[{ding_idx}:a]adelay={ding_delay_ms}|{ding_delay_ms},volume=0.6[ading]"
            )

        # 4. Build video filter chain
        ken_speed = style.ken_burns_speed
        bg_dim = style.bg_dim_opacity

        if ken_speed > 0 and not is_video:
            liven = build_liven_up_filter(canvas_w, canvas_h, speed=ken_speed)
            bg_filter = (
                f"[0:v]{liven},setsar=1,fps={CANVAS_FPS}[bg_raw];"
                f"[bg_raw]{build_dim_overlay_filter(bg_dim)}[bg]"
            )
        else:
            bg_filter = (
                f"[0:v]scale={canvas_w}:{canvas_h}:"
                f"force_original_aspect_ratio=increase,crop={canvas_w}:{canvas_h},"
                f"setsar=1,fps={CANVAS_FPS}[bg_raw];"
                f"[bg_raw]{build_dim_overlay_filter(bg_dim)}[bg]"
            )

        filter_parts = [bg_filter]
        last_label = "bg"

        # Intro text overlays
        lang_name = config.target_lang_name
        theme = words[0].get("theme", "vocabulary") if words else "vocabulary"
        intro_filters = build_intro_filters(
            word_count=len(enriched_words),
            lang_name=lang_name,
            theme=theme,
            intro_duration=intro_dur,
            config=cfg_dict,
        )
        if intro_filters:
            intro_chain = f"[{last_label}]" + ",".join(intro_filters) + "[v_intro]"
            filter_parts.append(intro_chain)
            last_label = "v_intro"

        # Word blocks: overlay cards then drawtexts
        # Word blocks: overlay card then drawtexts
        card_width = int(canvas_w * 0.8889)
        card_x = (canvas_w - card_width) // 2
        card_height = int(canvas_h * 0.4167)  # 800 pixels
        card_y = (canvas_h - card_height) // 2  # Centered vertically (560)

        padding = 30
        vis_x0 = card_x + padding
        vis_y0 = card_y + padding
        vis_w = card_width - 2 * padding
        vis_h = card_height - 2 * padding

        for i, w in enumerate(enriched_words):
            block_start = intro_dur + (i * block_dur)
            block_end = block_start + en_display + reveal

            # 1. Backdrop blur: split video, crop card area (exact size), blur, apply rounded mask, and overlay back
            filter_parts.append(
                f"[{last_label}]split[v_main{i}][v_crop{i}];"
                f"[v_crop{i}]crop={vis_w}:{vis_h}:{vis_x0}:{vis_y0},"
                f"boxblur=40:3[v_blur_raw{i}];"
                f"[v_blur_raw{i}][{mask_input_idx}:v]alphamerge[v_blur{i}];"
                f"[v_main{i}][v_blur{i}]overlay={vis_x0}:{vis_y0}:enable='between(t,{block_start:.2f},{block_end:.2f})'"
                f"[v_after_blur{i}]"
            )
            last_label = f"v_after_blur{i}"

            # 2. Overlay specific card for this word block (includes progress dots)
            filter_parts.append(
                f"[{last_label}][{card_input_idxs[i]}:v]"
                f"overlay={card_x}:{card_y}:enable='between(t,{block_start:.2f},{block_end:.2f})'"
                f"[v_after_card{i}]"
            )
            last_label = f"v_after_card{i}"

            w_filters = build_word_block_filters(
                word_index=i,
                total_words=len(enriched_words),
                start_time=block_start,
                source_text=w["source_text"],
                target_text=w["target_text"],
                phonetic_text=w.get("phonetic", ""),
                config=cfg_dict,
            )
            if w_filters:
                w_chain = f"[{last_label}]" + ",".join(w_filters) + f"[v_word{i}]"
                filter_parts.append(w_chain)
                last_label = f"v_word{i}"

        # Outro
        outro_start = intro_dur + (len(enriched_words) * block_dur)
        outro_filters = build_outro_filters(
            outro_start=outro_start,
            outro_end=total_duration,
            config=cfg_dict,
        )
        if outro_filters:
            outro_chain = f"[{last_label}]" + ",".join(outro_filters) + "[v_out]"
            filter_parts.append(outro_chain)
            last_label = "v_out"
        else:
            filter_parts.append(f"[{last_label}]format=yuv420p[v_out]")

        # Chain audio filters
        word_audio_labels = "".join([f"[a{i}s][a{i}t]" for i in range(len(enriched_words))])
        intro_label = "[aintro]" if intro_audio_path else ""
        outro_label = "[aoutro]" if outro_audio_path else ""
        ding_label = "[ading]" if ding_path else ""
        total_audio_inputs = (
            len(enriched_words) * 2
            + (1 if intro_audio_path else 0)
            + (1 if outro_audio_path else 0)
            + (1 if ding_path else 0)
        )

        a_mix = (
            f"{word_audio_labels}{intro_label}{outro_label}{ding_label}"
            f"amix=inputs={total_audio_inputs}:dropout_transition=2:normalize=0[a_out]"
        )

        filter_complex = ";".join(filter_parts + audio_filters + [a_mix])

        # 5. Run FFmpeg
        _report("ffmpeg", "Running FFmpeg...")
        if config.use_gpu:
            video_args = [
                "-c:v", "h264_nvenc",
                "-preset", "fast",
                "-cq", "28",
                "-pix_fmt", "yuv420p",
            ]
            hw_note = "GPU (NVENC)"
        else:
            video_args = [
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "28",
                "-threads", "0",
                "-pix_fmt", "yuv420p",
            ]
            hw_note = "CPU (libx264)"

        # Progress callback: FFmpeg writes key=value pairs to pipe:2 (stderr)
        progress_fields: dict[str, str] = {}
        last_report = ""

        def _on_ffmpeg_stderr(line: str) -> None:
            nonlocal last_report
            if "=" in line:
                k, v = line.split("=", 1)
                progress_fields[k.strip()] = v.strip()
                if k.strip() == "progress":
                    parts = []
                    if "frame" in progress_fields:
                        parts.append(f"frame={progress_fields['frame']}")
                    if "fps" in progress_fields:
                        parts.append(f"fps={progress_fields['fps']}")
                    if "out_time" in progress_fields:
                        parts.append(f"time={progress_fields['out_time'][:8]}")
                    if "speed" in progress_fields:
                        parts.append(f"speed={progress_fields['speed']}")
                    if parts:
                        report = "  ".join(parts)
                        if report != last_report:
                            last_report = report
                            _report("ffmpeg", report)

        args = input_args + [
            "-progress", "pipe:2",
            "-filter_complex", filter_complex,
            "-map", f"[{last_label}]",
            "-map", "[a_out]",
            *video_args,
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]

        total_inputs = 2 + (len(enriched_words) * 2) + (1 if intro_audio_path else 0) + (1 if outro_audio_path else 0) + (1 if ding_path else 0)
        cmd_str = " ".join(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + [str(a) for a in args])
        logger.info("FFmpeg inputs=%d filter_chars=%d cmd=%s", total_inputs, len(filter_complex), cmd_str[:500])
        _report("ffmpeg", f"Encoding {total_inputs} inputs ({hw_note})...")

        returncode, _stdout, stderr = await run_ffmpeg(*args, timeout=1800.0, on_stderr=_on_ffmpeg_stderr)

        if returncode != 0:
            raise RuntimeError(f"FFmpeg render failed (code {returncode}): {stderr[:2000]}")

        _report("ffmpeg", "FFmpeg complete")
        return output_path
