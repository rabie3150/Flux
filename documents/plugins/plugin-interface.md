# Plugin Interface Documentation

## Overview
Flux uses a **Strategy-based Plugin Architecture**. The core engine is agnostic to content types (Quran, Hadith, News, etc.) and delegates all content-specific logic — fetching, rendering, identification, and captioning — to plugins.

## Files
| File | Purpose |
|------|---------|
| `flux/plugins/base.py` | Abstract base class `ContentPlugin` and `RenderResult` dataclass |
| `flux/plugins/loader.py` | Plugin discovery, dynamic importing, and DB synchronization |

## Key Concepts
- **`ContentPlugin` (ABC):** All plugins must inherit from this class and implement its abstract methods.
- **`RenderResult`:** A standardized container for the output of a render operation, including file paths, captions, and metadata.
- **Dynamic Loading:** Plugins are discovered by scanning the `flux/plugins/` directory. Each plugin must be a Python package containing a subclass of `ContentPlugin`.

## API / Interface

### `ContentPlugin` Abstract Methods

#### `fetch(pipeline_id: str, config: dict[str, Any]) -> list[dict[str, Any]]`
Downloads raw materials (ingredients) from external sources.
- **Input:** `pipeline_id` and the pipeline's configuration dictionary.
- **Output:** List of ingredient dictionaries ready for insertion into the `ingredients` table with `status='pending'`.

#### `render(pipeline_id: str, ingredient_ids: list[str], config: dict[str, Any]) -> RenderResult`
Combines approved ingredients into a final piece of content (e.g., composites a video).
- **Input:** `pipeline_id`, list of approved `ingredient_ids`, and pipeline configuration.
- **Output:** `RenderResult` object containing file paths and metadata.

#### `identify_content(pipeline_id: str, produced_content_id: str, config: dict[str, Any]) -> dict[str, Any] | None`
Performs semantic analysis (e.g., OCR, Speech-to-Text, or Regex) to identify exactly what was produced (e.g., identifying Surah/Ayah).
- **Input:** `pipeline_id`, `produced_content_id`, and configuration.
- **Output:** Identification metadata or `None`.

#### `build_caption(pipeline_id: str, produced_content_id: str, config: dict[str, Any], worker_config: dict[str, Any]) -> str`
Generates the platform-specific text caption.
- **Input:** Pipeline and worker configurations, plus the produced content ID.
- **Output:** Final caption string.

#### `get_config_schema() -> dict[str, Any]`
Returns a JSONSchema describing the configuration options available for this plugin. This is used by the Admin UI to render dynamic forms.

## Common Tasks

### How to Create a New Plugin
1. Create a new directory in `flux/plugins/` (e.g., `flux/plugins/my_plugin/`).
2. Implement a class inheriting from `ContentPlugin`.
3. Export the class in `flux/plugins/my_plugin/__init__.py`.
4. Restart the Flux daemon. The core engine will automatically detect the plugin and sync it to the `plugins` table.
