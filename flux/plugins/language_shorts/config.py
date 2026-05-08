"""
Language Shorts plugin configuration defaults and JSONSchema.
"""

from __future__ import annotations

DEFAULT_CONFIG: dict = {
    "source_lang": "en",
    "target_lang": "it",
    "words_per_video": 5,
    "difficulty": "beginner",
    "themes": [
        "greetings", "food", "travel", "family",
        "numbers", "colors", "emotions", "daily routines",
        "shopping", "directions", "weather", "time",
    ],
    "tts": {
        "provider": "inworld",
        "source_voice": "en-US-JennyNeural",  # Example, can be configured
        "target_voice": "Orietta",          # Inworld Italian voice
        "model": "inworld-tts-2",
        "speaking_rate": 0.9,
    },
    "canvas": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
    },
    "timing": {
        "intro_duration": 3.0,
        "en_display_secs": 2.0,
        "countdown_secs": 3.0,
        "reveal_hold_secs": 3.0,
        "pause_between_secs": 1.5,
        "outro_duration": 3.0,
    },
    "bg_sources": {
        "pexels_keywords": ["gradient", "abstract", "pastel", "minimal"],
        "unsplash_keywords": ["texture", "pattern", "soft light"],
        "blocklist": ["people", "face", "portrait"],
    },
    "hashtags": [
        "LanguageLearning", "Vocabulary", "LearnLanguages", "Education",
    ],
    "caption_templates": {
        "default": (
            "Learn {{ target_lang_name }} — {{ theme }} vocabulary!\n\n"
            "{% for w in words %}"
            "{{ w.source }} → {{ w.target }}\n"
            "{% endfor %}\n"
            "{{ hashtags }}"
        ),
        "youtube": (
            "Learn {{ target_lang_name }} Vocabulary — {{ theme | title }}\n\n"
            "Words in this video:\n"
            "{% for w in words %}"
            "{{ loop.index }}. {{ w.source }} → {{ w.target }}\n"
            "{% endfor %}\n"
            "{{ hashtags }}"
        ),
        "x": "Learn {{ target_lang_name }}: {{ words[0].source }} = {{ words[0].target }} {{ hashtags }}",
    },
}

CONFIG_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "source_lang": {"type": "string", "default": "en"},
        "target_lang": {"type": "string", "default": "it"},
        "words_per_video": {"type": "integer", "default": 5, "minimum": 1, "maximum": 15},
        "difficulty": {"type": "string", "enum": ["beginner", "intermediate", "advanced"], "default": "beginner"},
        "themes": {
            "type": "array",
            "items": {"type": "string"}
        },
        "tts": {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "default": "inworld"},
                "source_voice": {"type": "string"},
                "target_voice": {"type": "string"},
                "model": {"type": "string", "default": "inworld-tts-2"},
                "speaking_rate": {"type": "number", "default": 0.9},
            }
        },
        "canvas": {
            "type": "object",
            "properties": {
                "width": {"type": "integer", "default": 1080},
                "height": {"type": "integer", "default": 1920},
                "fps": {"type": "integer", "default": 30},
            }
        },
        "timing": {
            "type": "object",
            "properties": {
                "intro_duration": {"type": "number", "default": 3.0},
                "en_display_secs": {"type": "number", "default": 2.0},
                "countdown_secs": {"type": "number", "default": 3.0},
                "reveal_hold_secs": {"type": "number", "default": 3.0},
                "pause_between_secs": {"type": "number", "default": 1.5},
                "outro_duration": {"type": "number", "default": 3.0},
            }
        },
        "bg_sources": {
            "type": "object",
            "properties": {
                "pexels_keywords": {"type": "array", "items": {"type": "string"}},
                "unsplash_keywords": {"type": "array", "items": {"type": "string"}},
                "blocklist": {"type": "array", "items": {"type": "string"}},
            }
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"}
        },
        "caption_templates": {
            "type": "object",
            "properties": {
                "default": {"type": "string"},
                "youtube": {"type": "string"},
                "instagram": {"type": "string"},
                "tiktok": {"type": "string"},
                "x": {"type": "string"},
            }
        }
    },
    "required": ["source_lang", "target_lang", "themes"]
}
