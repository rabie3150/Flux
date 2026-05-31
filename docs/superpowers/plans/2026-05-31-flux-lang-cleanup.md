# Flux Language Shorts Generator — Cleanup Implementation Plan

> **For agentic workers:** Execute tasks in order using inline execution. Steps use checkbox syntax.

**Goal:** Strip Flux to a standalone TUI app that generates vocabulary translation videos.

**Architecture:** Single-package Python app (`flux_lang/`) with Rich TUI, no DB, no web server.

**Tech Stack:** Python 3.11+, Rich, Pydantic, Pillow, httpx, edge-tts

---

### Task 1: Create the new package skeleton and config module

**Files:**
- Create: `flux_lang/__init__.py`
- Create: `flux_lang/config.py`
- Create: `flux_lang/utils.py`

- [ ] **Step 1: Write `flux_lang/__init__.py`**

```python
"""Flux Language Shorts Generator — Standalone vocabulary video generator."""

__version__ = "2.0.0"
```

- [ ] **Step 2: Write `flux_lang/config.py`**

```python
"""Configuration backed by JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


DEFAULT_THEMES = [
    "greetings", "food", "travel", "family",
    "numbers", "colors", "emotions", "daily routines",
    "shopping", "directions", "weather", "time",
]

LANG_NAMES: dict[str, str] = {
    "en": "English", "it": "Italian", "fr": "French",
    "de": "German", "es": "Spanish", "pt": "Portuguese",
    "ar": "Arabic", "ja": "Japanese", "ko": "Korean",
    "zh": "Chinese", "ru": "Russian", "nl": "Dutch",
    "tr": "Turkish", "hi": "Hindi", "sv": "Swedish",
    "pl": "Polish",
}


class TTSConfig(BaseModel):
    provider: str = "edge_tts"
    source_voice: str = "en-US-AriaNeural"
    source_voice_fallback: str = "en-US-GuyNeural"
    target_voice: str = "it-IT-ElsaNeural"
    target_voice_fallback: str = "it-IT-IsabellaNeural"
    speaking_rate: float = 0.9


class CanvasConfig(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30


class TimingConfig(BaseModel):
    intro_duration: float = 3.5
    en_display_secs: float = 2.5
    reveal_transition_secs: float = 0.5
    reveal_hold_secs: float = 3.0
    pause_between_secs: float = 1.0
    outro_duration: float = 3.0


class StyleConfig(BaseModel):
    source_font_size: int = 72
    target_font_size: int = 72
    countdown_font_size: int = 140
    phonetic_font_size: int = 40
    text_color: str = "#FFFFFF"
    accent_color: str = "#FFD700"
    countdown_color: str = "#FFD700"
    phonetic_color: str = "#AAAAAA"
    progress_dots: bool = True
    fontfile: str | None = None
    bg_dim_opacity: float = 0.35
    ken_burns_speed: float = 0.3
    card_fill_rgba: list[int] = [25, 25, 35, 170]
    card_border_rgba: list[int] = [255, 255, 255, 70]
    card_corner_radius: int = 36
    card_border_width: int = 2


class BGConfig(BaseModel):
    pexels_keywords: list[str] = ["gradient", "abstract", "pastel", "minimal"]
    unsplash_keywords: list[str] = ["texture", "pattern", "soft light"]
    blocklist: list[str] = ["people", "face", "portrait"]
    local_folder: str | None = None


class AppConfig(BaseModel):
    source_lang: str = "en"
    target_lang: str = "it"
    words_per_video: int = 5
    difficulty: str = "beginner"
    themes: list[str] = Field(default_factory=list)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    canvas: CanvasConfig = Field(default_factory=CanvasConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)
    bg: BGConfig = Field(default_factory=BGConfig)
    output_dir: str = "./output"
    gemini_api_keys: list[str] = Field(default_factory=list)
    pexels_api_key: str = ""
    unsplash_access_key: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.themes:
            self.themes = DEFAULT_THEMES.copy()

    @property
    def target_lang_name(self) -> str:
        return LANG_NAMES.get(self.target_lang, self.target_lang.upper())

    @property
    def source_lang_name(self) -> str:
        return LANG_NAMES.get(self.source_lang, self.source_lang.upper())


def config_path() -> Path:
    """Return path to config.json — prefers project root, falls back to cwd."""
    root = Path(__file__).resolve().parent.parent
    return root / "config.json"


def load_config() -> AppConfig:
    path = config_path()
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AppConfig.model_validate(data)
    return AppConfig()


def save_config(cfg: AppConfig) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg.model_dump(mode="json"), f, indent=2)
```

- [ ] **Step 3: Write `flux_lang/utils.py`**

```python
"""Logging and FFmpeg utilities."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


async def run_ffmpeg(*args: str, timeout: float = 300.0) -> tuple[int, str, str]:
    """Run FFmpeg. Returns (returncode, stdout, stderr)."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + list(args)
    logger = get_logger("ffmpeg")
    logger.debug("cmd: %s", " ".join(cmd))

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
    except asyncio.TimeoutError:
        logger.error("FFmpeg timed out after %.0fs", timeout)
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return -1, "", f"FFmpeg timed out after {timeout}s"
    except FileNotFoundError:
        logger.error("FFmpeg not found in PATH")
        return -1, "", "FFmpeg not found in PATH"


async def extract_thumbnail(
    video_path: str,
    output_path: str,
    *,
    time_sec: float = 2.0,
    width: int = 1080,
    height: int = 1920,
) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    args = [
        "-ss", str(time_sec),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        output_path,
    ]
    code, _stdout, stderr = await run_ffmpeg(*args)
    if code != 0:
        raise RuntimeError(f"Thumbnail extraction failed: {stderr[:500]}")
    if not Path(output_path).exists():
        raise RuntimeError(f"Thumbnail missing: {output_path}")
    return output_path
```

- [ ] **Step 4: Verify config module loads**

Run: `python -c "from flux_lang.config import load_config, save_config, AppConfig; c=load_config(); print(c.target_lang_name); save_config(c)"`

---

### Task 2: Port TTS module

**Files:**
- Create: `flux_lang/tts.py`

- [ ] **Step 1: Write `flux_lang/tts.py`**

```python
"""TTS dispatcher — Edge TTS (free) and Inworld AI."""

from __future__ import annotations

import base64
import uuid
from abc import ABC, abstractmethod
from typing import Any

import httpx

from flux_lang.utils import get_logger

logger = get_logger(__name__)


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, params: dict[str, Any] | None = None) -> bytes:
        ...


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge TTS — free, no API key."""

    async def synthesize(self, text: str, voice_id: str, params: dict[str, Any] | None = None) -> bytes:
        try:
            import edge_tts
        except ImportError as exc:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts") from exc

        params = params or {}
        rate = params.get("rate", "+0%")
        pitch = params.get("pitch", "+0Hz")
        volume = params.get("volume", "+0%")

        communicate = edge_tts.Communicate(text, voice=voice_id, rate=rate, pitch=pitch, volume=volume)
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio


class InworldTTSProvider(TTSProvider):
    """Inworld AI TTS — free web API."""

    async def synthesize(self, text: str, voice_id: str, params: dict[str, Any] | None = None) -> bytes:
        params = params or {}
        model_id = params.get("modelId", "inworld-tts-2")
        url = "https://inworld.ai/api/create-speech"
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://inworld.ai",
            "referer": "https://inworld.ai/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/148.0.0.0 Safari/537.36",
        }
        cookies = {"inworld_uid": str(uuid.uuid4())}
        payload = {
            "text": text,
            "voiceId": voice_id,
            "modelId": model_id,
            "deliveryMode": "DEFAULT",
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 48000},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, cookies=cookies, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            b64 = data.get("result", {}).get("audioContent")
            if not b64:
                raise RuntimeError("Inworld returned no audioContent")
            return base64.b64decode(b64)


_PROVIDERS: dict[str, TTSProvider] = {
    "edge_tts": EdgeTTSProvider(),
    "inworld": InworldTTSProvider(),
}


async def synthesize(text: str, voice_id: str, provider: str, params: dict[str, Any] | None = None) -> bytes:
    """Synthesize text to audio bytes."""
    p = _PROVIDERS.get(provider)
    if not p:
        raise ValueError(f"Unknown TTS provider: {provider}")
    return await p.synthesize(text, voice_id, params)
```

---

### Task 3: Port vocabulary generator

**Files:**
- Create: `flux_lang/generator.py`

- [ ] **Step 1: Write `flux_lang/generator.py`**

```python
"""Gemini Flash vocabulary generator."""

from __future__ import annotations

import json
from typing import Any

import httpx

from flux_lang.utils import get_logger

logger = get_logger(__name__)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

PROMPT = """You are an expert language teacher. Generate exactly {count} vocabulary items for learning {target_lang} from {source_lang}.

Theme: {theme}
Difficulty: {difficulty}
Avoid these previously taught words:
{avoid_words}

For each item, provide:
1. source — word/sentence in {source_lang}
2. target — exact translation in {target_lang}
3. phonetic — pronunciation guide for target
4. difficulty — {difficulty}
5. category — e.g. "greetings", "food", "numbers"

Return ONLY a valid JSON array without markdown. Example:
[
  {"source": "Hello", "target": "Ciao", "phonetic": "CHOW", "difficulty": "beginner", "category": "greetings"}
]"""


class GeminiGenerator:
    def __init__(self, api_keys: list[str]):
        self.api_keys = [k.strip() for k in api_keys if k.strip()]
        self._idx = 0

    @property
    def current_key(self) -> str:
        if not self.api_keys:
            raise ValueError("No Gemini API keys configured.")
        return self.api_keys[self._idx]

    def rotate(self) -> None:
        if self.api_keys:
            self._idx = (self._idx + 1) % len(self.api_keys)

    async def generate(
        self,
        source_lang: str,
        target_lang: str,
        theme: str,
        count: int = 5,
        difficulty: str = "beginner",
        avoid_words: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.api_keys:
            logger.error("No Gemini API keys")
            return []

        avoid = ", ".join(avoid_words) if avoid_words else "None"
        prompt = PROMPT.format(
            count=count,
            source_lang=source_lang,
            target_lang=target_lang,
            theme=theme,
            difficulty=difficulty,
            avoid_words=avoid,
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(len(self.api_keys)):
                try:
                    url = f"{GEMINI_URL}?key={self.current_key}"
                    resp = await client.post(url, json=payload)
                    if resp.status_code in (429, 401):
                        logger.warning("Gemini %d, rotating key", resp.status_code)
                        self.rotate()
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]

                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0]

                    result = json.loads(text.strip())
                    if isinstance(result, list):
                        return [
                            {
                                "source_text": str(item["source"]),
                                "target_text": str(item["target"]),
                                "phonetic": str(item.get("phonetic", "")),
                                "difficulty": str(item.get("difficulty", difficulty)),
                                "category": str(item.get("category", theme)),
                                "theme": theme,
                            }
                            for item in result
                            if "source" in item and "target" in item
                        ]
                    return []
                except httpx.HTTPStatusError as e:
                    logger.error("Gemini HTTP %d: %s", e.response.status_code, e.response.text[:200])
                    self.rotate()
                except json.JSONDecodeError as e:
                    logger.error("Gemini bad JSON: %s", e)
                except Exception as e:
                    logger.error("Gemini error: %s", e)
                    self.rotate()
        return []
```

---

### Task 4: Port render filters and cards

**Files:**
- Create: `flux_lang/render_filters.py`
- Create: `flux_lang/render_cards.py`

- [ ] **Step 1: Port `render_filters.py` from existing**

Copy `flux/plugins/language_shorts/render_filters.py` to `flux_lang/render_filters.py`.
Changes:
- Remove `flux.logger` import, use `flux_lang.utils.get_logger`
- Remove Termux font paths from `_resolve_font_path` (lines 55-62)

- [ ] **Step 2: Port `render_cards.py` from existing**

Copy `flux/plugins/language_shorts/render_cards.py` to `flux_lang/render_cards.py` with no changes.

---

### Task 5: Port renderer

**Files:**
- Create: `flux_lang/renderer.py`

- [ ] **Step 1: Write `flux_lang/renderer.py`**

Port `flux/plugins/language_shorts/render.py` to `flux_lang/renderer.py`.
Key changes:
- Replace `flux.config.settings` with output_dir param
- Replace `flux.logger` with `flux_lang.utils.get_logger`
- Replace `flux.plugins.language_shorts.render_cards` → `flux_lang.render_cards`
- Replace `flux.plugins.language_shorts.render_filters` → `flux_lang.render_filters`
- Replace `flux.services.render_utils` → `flux_lang.utils`
- Replace `flux.tts` → `flux_lang.tts`
- Remove DB/async session imports
- `render_video()` takes `output_dir: Path` instead of using settings.storage_path
- Remove `_generate_card_pngs` — inline it or keep as-is (it already doesn't use DB)

The function signature should be:
```python
async def render_video(
    words: list[dict[str, Any]],
    background_paths: list[str],
    output_path: str,
    config: AppConfig,
) -> str:
    ...
```

Where `config` is `AppConfig` from `flux_lang.config`.

---

### Task 6: Port background asset fetching

**Files:**
- Create: `flux_lang/assets.py`

- [ ] **Step 1: Write `flux_lang/assets.py`**

Port from `flux/services/backgrounds.py` (if exists) or write minimal version:
- Fetch from Pexels API
- Fetch from Unsplash API
- Fallback to local folder
- Return list of file paths

If `flux/services/backgrounds.py` doesn't exist, write a minimal version that:
- Tries Pexels with API key
- Tries Unsplash with API key
- Falls back to solid-color PNG generation if no keys and no local folder

---

### Task 7: Build the TUI

**Files:**
- Create: `flux_lang/tui.py`

- [ ] **Step 1: Write `flux_lang/tui.py`**

Rich-based TUI with:
- `Live` display for progress during generation
- `Panel` / `Table` for word preview
- `Progress` bar for overall status
- Menu using `Prompt.ask`

Main loop:
1. Show menu
2. If Generate:
   - Prompt for source/target lang (or use config)
   - Prompt for theme (or random)
   - Prompt for word count
   - Show live progress dashboard
   - Run `generator.generate()` → show words in table
   - Run `renderer.render_video()` → show FFmpeg progress (spinner)
   - Show success panel with output path
3. If Settings:
   - Show current config as JSON or interactive fields
   - Save on change
4. If Open Output Folder:
   - `os.startfile()` on Windows, `xdg-open` on Linux, `open` on macOS

---

### Task 8: Entry point

**Files:**
- Create: `flux_lang/__main__.py`

- [ ] **Step 1: Write `flux_lang/__main__.py`**

```python
"""Entry point: python -m flux_lang"""

from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from flux_lang.tui import main

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Task 9: Cleanup old code

**Files:**
- Delete/move: `flux/`, `tests/`, `scripts/` (except keep what we need)
- Modify: `requirements.txt`
- Modify: `pyproject.toml` (remove web/DB deps, update package name)

- [ ] **Step 1: Backup then remove old code**

Move to `archive/` or delete:
- `flux/api/`
- `flux/core/`
- `flux/platforms/`
- `flux/plugins/quran/`
- `flux/services/`
- `flux/static/`
- `flux/tts/` (old version)
- `flux/main.py`
- `flux/db.py`
- `flux/models.py`
- `flux/scheduler.py`
- `flux/logger.py` (replaced by utils)
- `scripts/`
- `tests/`
- `.github/workflows/`

Keep for now until verified working:
- `flux/plugins/language_shorts/` (reference until port is complete)

- [ ] **Step 2: Update `requirements.txt`**

```
httpx>=0.27.0
Pillow>=10.0.0
pydantic>=2.5.0
rich>=13.0.0
edge-tts>=6.0.0
```

- [ ] **Step 3: Update `pyproject.toml`**

Update package name, remove FastAPI/DB dependencies from project config.

---

### Task 10: Final verification

- [ ] **Step 1: Install dependencies**

`pip install -r requirements.txt`

- [ ] **Step 2: Test config load/save**

`python -c "from flux_lang.config import load_config; print(load_config().model_dump_json(indent=2))"`

- [ ] **Step 3: Launch TUI**

`python -m flux_lang`

- [ ] **Step 4: Test generation (if API keys available)**

Run generate flow and verify MP4 output.
