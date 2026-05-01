"""Quran plugin configuration defaults and JSONSchema."""

from __future__ import annotations

DEFAULT_CONFIG: dict = {
    "source_channels": [
        # Black-ground Quran chroma — ideal for colorkey removal
        "https://www.youtube.com/@Am9li9/shorts",
    ],
    "bg_sources": {
        "pexels_keywords": ["nature", "clouds", "ocean", "mountains", "sky", "islamic architecture"],
        "unsplash_keywords": ["abstract", "light", "space", "gradient", "galaxy"],
        "blocklist": ["people", "face", "portrait", "woman", "man", "nude", "bikini"],
    },
    "max_clips_per_fetch": 10,
    "max_backgrounds_per_fetch": 20,
    "canvas": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
    },
    "ken_burns": True,
    "image_duration": 5.0,
    "hashtags": ["Quran", "Islam", "Reminder", "Faith", "Peace"],
    "caption_templates": {
        "default": (
            "📖 {{ surah_name }} ({{ verse_ref }})\n\n"
            "{{ arabic_text }}\n\n"
            "{{ translation }}\n\n"
            "{{ hashtags }}"
        ),
        "youtube": (
            "📖 {{ surah_name }} | {{ verse_ref }}\n\n"
            "{{ translation }}\n\n"
            "{{ hashtags }}"
        ),
        "telegram": (
            "📖 {{ surah_name }} ({{ verse_ref }})\n\n"
            "{{ arabic_text }}\n\n"
            "{{ translation }}\n\n"
            "{{ hashtags }}"
        ),
        "instagram": (
            "📖 {{ surah_name }} ({{ verse_ref }})\n\n"
            "{{ translation }}\n\n"
            "{{ hashtags }}"
        ),
        "x": (
            "📖 {{ surah_name }} ({{ verse_ref }})\n\n"
            "{{ translation }}\n\n"
            "{{ hashtags }}"
        ),
        "generic": (
            "Beautiful Quranic recitation 🎧\n\n"
            "{{ hashtags }}"
        ),
        "x_generic": "Beautiful Quranic recitation 🎧 {{ hashtags }}",
    },
}

CONFIG_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "source_channels": {
            "type": "array",
            "items": {"type": "string", "format": "uri"},
            "description": "YouTube channel URLs to monitor for Shorts",
        },
        "bg_sources": {
            "type": "object",
            "properties": {
                "pexels_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "unsplash_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "blocklist": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        "max_clips_per_fetch": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "default": 10,
        },
        "max_backgrounds_per_fetch": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "default": 20,
        },
        "ken_burns": {
            "type": "boolean",
            "default": True,
            "description": "Apply Ken Burns effect (zoom/pan) to background images",
        },
        "image_duration": {
            "type": "number",
            "default": 5.0,
            "description": "Duration to show each background image in seconds",
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "default": ["Quran", "Islam", "Reminder", "Faith", "Peace"],
        },
        "caption_templates": {
            "type": "object",
            "properties": {
                "default": {"type": "string"},
                "youtube": {"type": "string"},
                "instagram": {"type": "string"},
                "telegram": {"type": "string"},
                "x": {"type": "string"},
            },
        },
        "canvas": {
            "type": "object",
            "properties": {
                "width": {"type": "integer", "default": 1080},
                "height": {"type": "integer", "default": 1920},
                "fps": {"type": "integer", "default": 30},
            },
        },
    },
    "required": ["source_channels"],
}
