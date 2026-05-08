# Language Learning Shorts Plugin

The `language_shorts` plugin is a self-contained generative content pipeline for Flux. It autonomously generates educational vocabulary videos (Shorts format) utilizing Gemini Flash, Asynchronous TTS (Inworld / EdgeTTS), and pure FFmpeg composition.

## 1. Flow Overview

Unlike plugins that fetch existing media (e.g., Quran clips from YouTube), this plugin generates all content from scratch.

### Fetch Phase (`generate.py` & `backgrounds.py`)
1. **Deduplication Check**: Fetches previously generated `word_batch` ingredients from the database to avoid repeating words.
2. **Vocabulary Generation**: Uses Gemini Flash to generate a JSON array of word pairs (source text, target text, phonetic pronunciation, difficulty).
3. **Background Fetch**: Uses the shared `flux.plugins.quran.backgrounds` fetcher to grab abstract/gradient portrait images from Pexels and Unsplash.
4. **Storage**: Both the vocabulary list and background images are stored as `ingredients`.

### Render Phase (`render.py` & `render_filters.py`)
1. **TTS Audio Generation**: Iterates through the generated word pairs. Invokes the asynchronous `flux.tts.service` to synthesize audio for both the source (English) and target (Italian) strings. Audio is cached temporarily as `.wav` files.
2. **FFmpeg Composition**: Constructs a complex `filter_complex` graph using FFmpeg:
   - **Visuals**: Applies sequenced `drawtext` filters with `enable='between(t, start, end)'` to orchestrate text appearances, 3-2-1 countdowns, phonetic overlays, and progress dots on top of the fetched background image.
   - **Audio**: Defers audio tracks to match visual timing using `adelay` and mixes them together with `amix`.
3. **Export**: Outputs a rendered MP4 video and extracts a thumbnail.

### Caption Phase (`plugin.py`)
Uses Jinja2 templates (configurable per platform) to format a structured caption detailing the theme, the vocabulary list, and relevant hashtags.

## 2. TTS Architecture (`flux/tts/`)

The TTS system was refactored from legacy synchronous scripts into a proper async Flux service:
* `base.py`: Defines the `TTSAgent` interface.
* `service.py`: Provides the `TTSService` singleton for easy API access (`synthesize()`, `get_voices()`).
* `inworld.py`: Implements Inworld AI using async `httpx` and `deliveryMode="DEFAULT"` for instant base64 encoded linear audio.
* `edge_tts.py`: Implements Microsoft Edge TTS fallback.

## 3. Configuration (Pipeline Setup)

The plugin exposes an extensive configuration schema in `config.py`.

```json
{
    "source_lang": "en",
    "target_lang": "it",
    "words_per_video": 5,
    "difficulty": "beginner",
    "themes": ["greetings", "food", "travel"],
    "tts": {
        "provider": "inworld",
        "source_voice": "en-US-JennyNeural",
        "source_provider": "edge_tts",
        "target_voice": "Orietta",
        "target_provider": "inworld"
    },
    "timing": {
        "intro_duration": 3.0,
        "en_display_secs": 2.0,
        "countdown_secs": 3.0,
        "reveal_hold_secs": 3.0,
        "pause_between_secs": 1.5,
        "outro_duration": 3.0
    }
}
```

### Key Behaviors:
- **Difficulty Toggle**: If `difficulty` is set to anything other than `beginner`, the phonetic pronunciation overlay is automatically skipped.
- **Provider Routing**: Voice agents can be configured individually via `source_provider` and `target_provider`.

## 4. Execution Rules
* **No MoviePy**: Relies purely on `ffmpeg` subprocesses to remain compatible with low-resource environments (ARM/Termux).
* **Async IO**: Network calls (Gemini, TTS, Image downloads) utilize `httpx` for non-blocking Event Loop execution.
