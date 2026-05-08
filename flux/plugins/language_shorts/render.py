"""
Language Shorts render pipeline.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from flux.config import settings
from flux.logger import get_logger
from flux.plugins.language_shorts.render_filters import build_word_block_filters, build_drawtext
from flux.tts import synthesize

logger = get_logger(__name__)

async def _run_ffmpeg(
    *args: str,
    timeout: float = 600.0,
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
        import subprocess
        def _sync_run():
            p = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
            )
            return p.returncode, p.stdout, p.stderr
        try:
            return await asyncio.to_thread(_sync_run)
        except Exception as e:
            return -1, "", f"FFmpeg sync fallback failed: {e}"
    except Exception as e:
        return -1, "", f"FFmpeg execution failed: {e}"

async def _generate_audio_assets(words: list[dict], config: dict, temp_dir: Path) -> list[dict]:
    """Generate TTS audio for all words and return enriched list with file paths."""
    tts_cfg = config.get("tts", {})
    provider = tts_cfg.get("provider", "inworld")
    source_voice = tts_cfg.get("source_voice", "en-US-JennyNeural")
    target_voice = tts_cfg.get("target_voice", "Orietta")
    
    # We'll use EdgeTTS for English and Inworld for Italian based on the config.
    # Wait, let's just respect the config. If it's EdgeTTS voice, use edge_tts, else inworld.
    # A simple heuristic: if it contains '-', it's likely EdgeTTS. Otherwise, default provider.
    def _guess_agent(voice_id: str) -> str:
        if "-" in voice_id and provider == "inworld":
            return "edge_tts" # fallback
        return provider

    enriched = []
    for i, w in enumerate(words):
        # Source
        s_text = w["source"]
        s_agent = _guess_agent(source_voice)
        s_audio = await synthesize(s_text, voice_id=source_voice, agent_id=s_agent)
        s_path = temp_dir / f"word_{i}_source.wav"
        s_path.write_bytes(s_audio)
        
        # Target
        t_text = w["target"]
        t_agent = _guess_agent(target_voice)
        t_audio = await synthesize(t_text, voice_id=target_voice, agent_id=t_agent)
        t_path = temp_dir / f"word_{i}_target.wav"
        t_path.write_bytes(t_audio)
        
        enriched.append({
            **w,
            "source_audio_path": str(s_path),
            "target_audio_path": str(t_path)
        })
        
    return enriched

async def render_video(
    word_batch: dict,
    background_paths: list[str],
    output_path: str,
    config: dict
) -> str:
    """Render the full composite video."""
    
    timing = config.get("timing", {})
    intro_dur = timing.get("intro_duration", 3.0)
    en_display = timing.get("en_display_secs", 2.0)
    countdown = timing.get("countdown_secs", 3.0)
    reveal = timing.get("reveal_hold_secs", 3.0)
    pause = timing.get("pause_between_secs", 1.5)
    outro_dur = timing.get("outro_duration", 3.0)
    
    block_dur = en_display + countdown + reveal + pause
    
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        
        # 1. Generate Audio
        words = await _generate_audio_assets(word_batch["words"], config, temp_dir)
        
        total_duration = intro_dur + (len(words) * block_dur) + outro_dur
        
        # 2. Build inputs
        # Background image (looping)
        bg = background_paths[0] # Just use the first one for simplicity
        
        input_args = [
            "-loop", "1",
            "-t", str(total_duration),
            "-i", bg
        ]
        
        # Audio inputs
        audio_filters = []
        for i, w in enumerate(words):
            input_args.extend(["-i", w["source_audio_path"]])
            s_idx = len(input_args) // 2 - 1
            
            input_args.extend(["-i", w["target_audio_path"]])
            t_idx = len(input_args) // 2 - 1
            
            block_start = intro_dur + (i * block_dur)
            
            # Delay audio to match visual timeline
            # Source audio plays 0.5s after text appears
            s_delay_ms = int((block_start + 0.5) * 1000)
            # Target audio plays 0.5s after translation appears
            t_delay_ms = int((block_start + en_display + countdown + 0.5) * 1000)
            
            audio_filters.append(f"[{s_idx}:a]adelay={s_delay_ms}|{s_delay_ms}[a{i}s]")
            audio_filters.append(f"[{t_idx}:a]adelay={t_delay_ms}|{t_delay_ms}[a{i}t]")
            
        # 3. Build Video Filtergraph
        v_filters = []
        
        # Scale & Crop background
        v_filters.append(f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p[bg]")
        
        # Intro
        lang_name = config.get("target_lang_name", "Italian")
        theme = word_batch.get("theme", "vocabulary").title()
        v_filters.append(
            build_drawtext(f"Learn {lang_name}", 0, intro_dur, y_pos=800, fontsize=90, fontcolor="white")
        )
        v_filters.append(
            build_drawtext(theme, 0, intro_dur, y_pos=950, fontsize=60, fontcolor="yellow")
        )
        
        # Words
        for i, w in enumerate(words):
            block_start = intro_dur + (i * block_dur)
            w_filters = build_word_block_filters(
                word_index=i,
                start_time=block_start,
                source_text=w["source"],
                target_text=w["target"],
                phonetic_text=w.get("phonetic", ""),
                config=config
            )
            v_filters.extend(w_filters)
            
        # Outro
        outro_start = intro_dur + (len(words) * block_dur)
        v_filters.append(
            build_drawtext("Follow for more!", outro_start, total_duration, y_pos=900, fontsize=80)
        )
        
        # Chain video filters
        # For simplicity, we just apply drawtexts sequentially on the [bg] stream
        # FFMPEG allows multiple drawtexts separated by commas on the same stream!
        v_chain = "[bg]" + ",".join(v_filters) + "[v_out]"
        
        # Chain audio filters
        # Mix all delayed audio streams
        a_mix_inputs = "".join([f"[a{i}s][a{i}t]" for i in range(len(words))])
        a_mix = f"{a_mix_inputs}amix=inputs={len(words)*2}:dropout_transition=2:normalize=0[a_out]"
        
        filter_complex = ";".join(audio_filters + [v_chain, a_mix])
        
        # 4. Run FFmpeg
        args = input_args + [
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "26",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path
        ]
        
        returncode, stdout, stderr = await _run_ffmpeg(*args)
        
        if returncode != 0:
            raise RuntimeError(f"FFmpeg render failed (code {returncode}): {stderr[:1000]}")
            
        return output_path
