# Flux Language Shorts Generator — Cleanup & Simplification Design

> **Date:** 2026-05-31  
> **Scope:** Strip Flux down to a single-purpose PC-native TUI app for generating vocabulary translation videos.

## Goals

1. Remove everything not needed for local video generation (web UI, DB, scheduling, publishing, Termux)
2. Keep and refactor the `language_shorts` render pipeline
3. Build a `rich`-based TUI for interactive configuration and live progress
4. Output clean MP4 files to a local folder
5. Ensure it works on Windows without Termux workarounds

## Architecture

```
flux_lang/
├── __init__.py
├── __main__.py          # Entry point
├── tui.py               # Rich TUI (menu, progress, settings editor)
├── config.py            # Pydantic settings backed by JSON file
├── generator.py         # Gemini vocabulary generation
├── renderer.py          # FFmpeg video composition
├── render_filters.py    # FFmpeg drawtext filters (ported from existing)
├── render_cards.py      # PIL card overlays (ported from existing)
├── tts.py               # TTS dispatcher (edge-tts + inworld)
├── assets.py            # Background image fetching (pexels/unsplash/local)
└── utils.py             # Logging, FFmpeg runner, path helpers
```

## What Gets Removed

| Component | Reason |
|-----------|--------|
| FastAPI / Uvicorn / CORS | No web server needed |
| SQLAlchemy / Alembic / aiosqlite | No database needed |
| APScheduler | No scheduling needed |
| All API routers (`flux/api/`) | No HTTP API |
| Static admin panel | TUI replaces it |
| Platform publishers (YouTube, IG, TikTok, X) | No publishing |
| Telegram notifications | Local tool |
| `scripts/start.sh`, `harden_ssh.sh`, etc. | Termux-only |
| `flux/core/*` (pipeline, ingredients, production, publish, workers, scheduler_jobs, lock, storage, hardening, crypto, notifications) | Engine layer no longer needed |
| `flux/models.py` | No ORM |
| `flux/db.py` | No DB |
| `flux/scheduler.py` | No scheduler |
| `flux/plugins/base.py`, `loader.py` | Plugin system no longer needed |
| `flux/plugins/quran/` | Out of scope |
| `tests/` for removed code | Not needed |

## What Gets Kept (Refactored)

| Source | Destination | Notes |
|--------|-------------|-------|
| `flux/plugins/language_shorts/generate.py` | `flux_lang/generator.py` | Strip DB refs, keep Gemini vocab gen |
| `flux/plugins/language_shorts/render.py` | `flux_lang/renderer.py` | Strip DB/config refs, pass config dict |
| `flux/plugins/language_shorts/render_filters.py` | `flux_lang/render_filters.py` | Remove Termux font paths, `flux.logger` |
| `flux/plugins/language_shorts/render_cards.py` | `flux_lang/render_cards.py` | Unchanged |
| `flux/plugins/language_shorts/config.py` | `flux_lang/config.py` | Convert to Pydantic model + JSON persistence |
| `flux/tts/edge_tts.py` | `flux_lang/tts.py` (EdgeTTS class) | Inline, no `flux.logger` |
| `flux/tts/inworld.py` | `flux_lang/tts.py` (Inworld class) | Inline, no `flux.logger` |
| `flux/services/render_utils.py` | `flux_lang/utils.py` | `run_ffmpeg`, `extract_thumbnail` |
| `flux/services/backgrounds.py` | `flux_lang/assets.py` | Strip DB refs |

## TUI Design

### Main Menu
```
┌─────────────────────────────────────────┐
│     Flux Language Shorts Generator      │
├─────────────────────────────────────────┤
│  [1] Generate Video                     │
│  [2] Settings                           │
│  [3] Open Output Folder                 │
│  [4] Quit                               │
└─────────────────────────────────────────┘
```

### Generate Screen (Live)
```
Generating: 5 Italian Food Words
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

Words:
• Hello → Ciao
• Thank you → Grazie
• Delicious → Delizioso
• Water → Acqua
• Bread → Pane

Status: Rendering video with FFmpeg...  [spinner]
Output: C:\Users\...\output\lang_food_1234567890.mp4
```

### Settings Screen
Editable fields:
- Source language (dropdown)
- Target language (dropdown)
- Word count per video (1-15)
- Difficulty (beginner/intermediate/advanced)
- Theme (or random)
- TTS provider (edge-tts / inworld)
- Voice IDs
- Output directory
- Background source (pexels / unsplash / local folder)

## Config Storage

Single `config.json` in the project root. Loaded at startup, saved on change. Pydantic model validates on load/save.

## Dependencies (Slimmed requirements.txt)

```
httpx>=0.27.0
Pillow>=10.0.0
pydantic>=2.5.0
rich>=13.0.0
edge-tts>=6.0.0
```

FFmpeg must be installed system-wide and available on PATH.

## Success Criteria

- [ ] `python -m flux_lang` launches TUI
- [ ] Generate flow produces valid 1080×1920 MP4
- [ ] No database, no web server, no scheduler processes
- [ ] Works on Windows with standard FFmpeg installation
- [ ] Clean project root — old files removed or archived
