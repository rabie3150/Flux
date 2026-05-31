"""Configuration backed by JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


DEFAULT_THEMES = [
    "greetings",
    "food",
    "travel",
    "family",
    "numbers",
    "colors",
    "emotions",
    "daily routines",
    "shopping",
    "directions",
    "weather",
    "time",
]

LANG_NAMES: dict[str, str] = {
    "en": "English",
    "it": "Italian",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "ar": "Arabic",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ru": "Russian",
    "nl": "Dutch",
    "tr": "Turkish",
    "hi": "Hindi",
    "sv": "Swedish",
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
    source_font_size: int = 140
    target_font_size: int = 140
    countdown_font_size: int = 140
    phonetic_font_size: int = 64
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
    show_logs: bool = False
    use_gpu: bool = False
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
    """Return path to config.json — prefers project root."""
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
