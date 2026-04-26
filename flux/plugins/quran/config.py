"""Quran plugin configuration defaults and JSONSchema."""

from __future__ import annotations

DEFAULT_CONFIG: dict = {
    "source_channels": [],
    "bg_sources": {
        "pexels_keywords": ["nature", "clouds", "ocean", "mountains", "sky"],
        "unsplash_keywords": ["abstract", "light", "space", "gradient"],
        "blocklist": ["people", "face", "portrait", "woman", "man", "nude"],
    },
    "max_clips_per_fetch": 10,
    "max_backgrounds_per_fetch": 20,
    "canvas": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
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
