# Quran Plugin Documentation

## Overview
The Quran plugin is the reference implementation for the Flux plugin system. it automates the creation of "Quran Shorts" by downloading clips from YouTube, pairing them with stock backgrounds (images/videos), and identifying the specific verse to generate translations and captions.

## Files
| File | Purpose |
|------|---------|
| `flux/plugins/quran/plugin.py` | Main plugin class implementation |
| `flux/plugins/quran/fetch.py` | YouTube Shorts downloading via `yt-dlp` |
| `flux/plugins/quran/backgrounds.py` | Stock media fetching from Pexels and Unsplash |
| `flux/plugins/quran/config.py` | Pydantic configuration models for the plugin |

## Key Concepts
- **Shorts Whitelist:** The plugin monitors specific YouTube channels configured in the pipeline.
- **Stock Rotation:** Backgrounds are fetched using religious/nature-themed keywords (e.g., "Makkah", "Desert", "Mountains").
- **Ingredient Types:**
    - `quran_clip`: The source video containing the Quranic text.
    - `bg_image`: Background image for the render.
    - `bg_video`: Background video loop (muted).

## Configuration
Relevant settings in `flux/config.py` or `.env`:
- `PEXELS_API_KEY`: Required for background image/video fetching.
- `UNSPLASH_ACCESS_KEY`: Fallback for background images.

## Common Tasks
### Adding a Source Channel
Update the `source_channels` list in the pipeline configuration via the Admin UI.

### Adjusting Background Keywords
Update `pexels_keywords` or `unsplash_keywords` in the pipeline configuration to change the visual theme of the generated videos.
