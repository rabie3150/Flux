# Flux — Data Strategy & Content Pipeline Design

This document defines how data and content flow through Flux, with explicit future-proofing for additional content types, media formats, and publishing paradigms.

---

## 1. Guiding Principles

1. **Content is typed by plugin, not by file extension.** A "Hadith" plugin may produce images; a "News" plugin may produce text threads.
2. **The pipeline is the unit of work.** Everything — scheduling, stock levels, render queues, post history — is scoped to a pipeline.
3. **Ingredients are generic containers.** The core engine stores file paths and metadata; the plugin interprets meaning.
4. **Render is optional.** Not all content needs video rendering. The pipeline must support pass-through (e.g., image + caption direct to Telegram).
5. **Platform workers are content-agnostic.** A YouTube worker receives a file path and caption; it does not know whether the content is Quran or Motivation.

---

## 2. Content Model: The 4-Layer Stack

```
Layer 4: PUBLISHED POST
         The immutable record of what was sent to a platform.
         Contains: platform ID, URL, timestamp, caption used, status.

Layer 3: PRODUCED CONTENT
         The artifact ready for publishing.
         Contains: file path(s), thumbnail, caption text, metadata.
         Status: rendering → rendered → ready → published / failed.

Layer 2: INGREDIENTS
         Raw, approved source materials.
         Contains: file path, source URL, type (plugin-defined), metadata.
         Status: pending → approved → rejected.

Layer 1: SOURCES
         External origins configured per pipeline.
         Examples: YouTube channel, Pexels keyword, RSS feed, API endpoint.
```

**Rule:** A pipeline moves data upward through layers. Lower layers are plugin-specific; upper layers are increasingly generic.

---

## 3. Ingredient System Design

### 3.1 Generic Ingredient Schema

The core `ingredients` table is intentionally schema-light. Plugin-specific metadata lives in `metadata_json`. The core `produced_content` table is similarly generic.

```sql
CREATE TABLE ingredients (
    id              TEXT PRIMARY KEY,
    pipeline_id     TEXT NOT NULL REFERENCES pipelines(id),
    type            TEXT NOT NULL,      -- plugin namespace: quran_clip, hadith_bg, news_img
    file_path       TEXT,               -- NULL if purely text-based ingredient
    source_url      TEXT,
    metadata_json   TEXT,               -- plugin-defined structure
    status          TEXT CHECK(status IN ('pending','approved','rejected')),
    file_size_bytes INTEGER,
    duration_secs   REAL,               -- NULL for images/text
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 Ingredient Types by Plugin (Examples)

| Plugin | Type | File | Metadata Example |
|--------|------|------|------------------|
| Quran | `quran_clip` | MP4 | `{"channel": "...", "yt_id": "..."}` |
| Quran | `bg_image` | JPG/PNG | `{"pexels_id": 12345, "photographer": "..."}` |
| Quran | `bg_video` | MP4 | `{"duration": 15.0, "source": "pexels"}` |
| Hadith | `hadith_text` | NULL | `{"source": "Bukhari", "book": 1, "hadith": 2}` |
| Hadith | `hadith_bg` | JPG | `{"color_palette": ["#1a1a1a", "#ffffff"]}` |
| News | `news_article` | NULL | `{"headline": "...", "source": "RSS", "url": "..."}` |
| News | `news_image` | JPG | `{"caption": "..."}` |

---

## 4. Pipeline Configuration Schema

Each pipeline stores its configuration as JSON. The core engine validates against the plugin's declared schema.

### 4.1 Quran Pipeline Config Example

```json
{
  "source_channels": [
    "https://www.youtube.com/@QuranShortsChannel",
    "https://www.youtube.com/@AnotherChannel"
  ],
  "fetch_schedule": "0 */6 * * *",
  "render_schedule": "0 2 * * *",
  "bg_sources": {
    "pexels_keywords": ["nature", "clouds", "ocean", "mountains", "islamic architecture"],
    "unsplash_keywords": ["abstract", "light", "space"],
    "blocklist": ["people", "face", "portrait", "woman", "man"]
  },
  "production": {
    "canvas": {"width": 1080, "height": 1920, "fps": 30},
    "bg_mode": "random", // "image_slideshow" | "video" | "random"
    "timing_sets": [
      {"name": "fast", "durations": [1.5, 2, 1, 2.5]},
      {"name": "slow", "durations": [6, 7, 8, 6]}
    ],
    "ken_burns": true,
    "lower_third_gradient": true
  },
  "caption": {
    "template_components": ["verse_ref", "arabic", "translation", "hashtags"],
    "translation_edition": "en.sahih",
    "include_tafseer": false
  },
  "verse_identification": {
    "primary_method": "yt_metadata_regex",
    "fallback_method": "whisper_fuzzy_match",
    "manual_review_required": false
  }
}
```

### 4.2 Future Hadith Pipeline Config Example

```json
{
  "source_api": "https://api.sunnah.com/v1/hadiths",
  "api_key": "${SUNNAH_API_KEY}",
  "fetch_schedule": "0 6 * * *",
  "render_mode": "image_card", // no video; generate image with text overlay
  "image_template": "./templates/hadith_card_1080x1080.png",
  "text_layout": {
    "arabic_font": "Amiri",
    "english_font": "Inter",
    "max_lines": 10
  },
  "caption": {
    "template_components": ["hadith_ref", "narrator", "english_text", "source_link"]
  }
}
```

**Key insight:** The same `pipelines` table and `PipelineOrchestrator` can handle both without modification.

---

## 5. Render Pipeline Abstraction

Not all pipelines produce video. The render step is plugin-defined.

### 5.1 Render Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `video_compose` | FFmpeg-based multi-layer video | Quran shorts |
| `image_compose` | Pillow-based image with text overlay | Hadith cards, quotes |
| `image_collage` | Multi-image grid | Photo galleries |
| `text_only` | No file production; caption only | News summaries on Telegram/X |
| `passthrough` | Use ingredient file directly with no processing | Curated image posts |

### 5.2 Render Output Schema

Regardless of mode, the plugin returns a standardized result:

```python
class RenderResult:
    file_path: Optional[str]       # Path to produced file (MP4, JPG, PNG)
    thumbnail_path: Optional[str]  # Preview image
    caption: str                   # Default caption text
    metadata: dict                 # Plugin-defined post metadata
    attachments: List[str]         # Additional files (e.g., carousel images)
```

The core engine stores this in `produced_content`.

---

## 6. Content Lifecycle State Machine

### 6.1 Ingredient States

```
[DOWNLOADED] ──> pending
     |
     v
[ADMIN REVIEW] ──approve──> [APPROVED] ──> eligible for render
     |
     reject
     |
     v
[REJECTED] ──> auto-delete or manual cleanup
```

### 6.2 Produced Content States

```
[RENDERING] ──success──> [RENDERED]
     |                       |
     fail                    |
     |                       v
     v                 [IDENTIFYING]
[FAILED]                    |
                            v
                    [VERSE KNOWN?]
                            |
                    +-------+-------+
                    |               |
                    Yes             No
                    |               |
                    v               v
                [READY]      [VERSE_UNKNOWN]
                    |               |
                    |           admin fixes or as ai to identify it via api give it the link to the youtube video and ask it to id it, if it failed give it the whole video 
                    |               |
                    +-------+-------+
                            |
                            v
                    [PUBLISHING]
                            |
                    +-------+-------+
                    |               |
                 success         fail (after retries)
                    |               |
                    v               v
               [PUBLISHED]     [FAILED]
```

---

## 7. Stock Management Strategy

Each pipeline monitors its ingredient stock independently.

### 7.1 Stock Levels

```python
@dataclass
class StockLevel:
    ingredient_type: str
    count_approved: int
    count_pending: int
    count_rejected: int
    min_threshold: int
    max_threshold: int
    fetch_triggered: bool
```

### 7.2 Auto-Fetch Logic

```python
async def evaluate_stock(pipeline_id: str):
    config = await get_pipeline_config(pipeline_id)
    for ing_type in config.ingredient_types:
        approved = await count_ingredients(pipeline_id, ing_type, "approved")
        if approved < config.min_stock:
            if not await is_fetch_job_queued(pipeline_id, ing_type):
                await schedule_fetch(pipeline_id, ing_type)
        elif approved > config.max_stock:
            await pause_fetch_jobs(pipeline_id, ing_type)
```

---

## 8. Data Retention & Archival

| Data Type | Retention | Cleanup Action |
|-----------|-----------|----------------|
| Approved ingredients | Until used in production | Delete after content published to all platforms |
| Rejected ingredients | 7 days | Auto-delete file + DB row |
| Published videos (MP4) | Configurable (default: delete after publish) | Delete file, keep metadata |
| Thumbnails | Forever (small) | None |
| Post records | Forever (audit) | None |
| Activity log | 30 days | Auto-truncate |
| Verse cache | Forever (small text) | None |
| Render logs | 7 days | Auto-truncate |

---

## 9. Multi-Pipeline Isolation

| Resource | Isolation Strategy |
|----------|-------------------|
| Ingredients | `pipeline_id` foreign key; UI filters by pipeline |
| Production queue | `pipeline_id` foreign key |
| Stock thresholds | Stored per pipeline in `config_json` |
| Platform workers | Many-to-many: one worker can serve multiple pipelines |
| Storage budget | Global setting; each pipeline's usage is tracked and summed |
| Render lock | Global file lock (`/tmp/flux-render.lock`): only one render across all pipelines at a time (CPU limit) |
| Fetch jobs | Per-pipeline: multiple pipelines can fetch simultaneously (I/O bound) |

---

## 10. Future Data Evolution

### 10.1 Adding a New Content Type (Checklist)

1. Define `plugin.yaml` with `ingredient_types`, `hooks`, and `config_schema`.
2. Implement `ContentPlugin` interface.
3. Decide render mode: `video_compose`, `image_compose`, `text_only`, etc.
4. Define ingredient `metadata_json` schema (documented in plugin README).
5. Add pipeline via admin UI; configure sources and thresholds.
6. Attach existing or new platform workers.
7. No core database migrations needed (generic schema).

### 10.2 Adding a New Platform

1. Implement `PlatformWorker` interface.
2. Add platform enum value (requires code change in v1; future: dynamic registry).
3. Add credential form fields to worker creation UI.
4. No plugin changes needed.

### 10.3 Adding Carousel / Multi-Image Posts

1. `RenderResult.attachments` list already supports multiple files.
2. Platform worker checks `len(attachments)` and uses carousel endpoint if available.
3. Instagram and Telegram already support multi-image natively.
