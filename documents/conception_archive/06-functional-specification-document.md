# Flux — Functional Specification Document (FSD)

The FSD translates PRD requirements into precise technical logic: data models, API contracts, algorithms, and error-handling protocols.

---

## 1. Plugin Interface Specification

Flux is built around a **plugin-first architecture**. The core engine knows nothing about Quran verses — it only knows about pipelines, ingredients, renders, and posts. The Quran logic lives entirely in a plugin.

### 1.1 Plugin Manifest (`plugin.yaml`)

```yaml
plugin:
  name: quran_shorts
  display_name: "Quran Shorts"
  version: "1.0.0"
  api_version: "1"
  author: "flux-core"
  description: "Automated Quran verse short-form video pipeline"
  
  hooks:
    - fetch
    - render
    - build_caption
    - identify_content
    
  ingredient_types:
    - quran_clip
    - bg_image
    - bg_video
    
  config_schema:
    - name: source_channels
      type: list[str]
      required: true
    - name: safe_keywords
      type: list[str]
      default: ["nature", "clouds", "ocean"]
    - name: blocklist_keywords
      type: list[str]
      default: ["people", "face", "portrait"]
    - name: timing_sets
      type: json
      default: { ... }
```

### 1.2 Python Plugin Class Interface

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class RenderResult:
    """Standardized output from any plugin's render() method."""
    file_path: Optional[str] = None       # Path to produced file (MP4, JPG, PNG)
    thumbnail_path: Optional[str] = None  # Preview image
    caption: str = ""                     # Default caption text
    metadata: Dict[str, Any] = None       # Plugin-defined post metadata (e.g., verse_ref, review_flag)
    attachments: List[str] = None         # Additional files (e.g., carousel images)

class ContentPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier."""
        pass

    @abstractmethod
    async def fetch(self, pipeline_id: str, config: Dict[str, Any]) -> List[Dict]:
        """
        Fetch new ingredients from external sources.
        Returns list of ingredient metadata dicts to be inserted into DB.
        Each dict must contain: type, file_path, source_url, metadata_json.
        """
        pass

    @abstractmethod
    async def render(self, pipeline_id: str, ingredient_ids: List[str], 
                     config: Dict[str, Any]) -> RenderResult:
        """
        Compose final content from approved ingredients.
        Returns: RenderResult
        """
        pass

    @abstractmethod
    async def build_caption(self, pipeline_id: str, produced_content_id: str,
                            config: Dict[str, Any], worker_config: Dict[str, Any]) -> str:
        """
        Generate the final text caption for a specific platform worker.
        Returns: caption string (already truncated to platform limits if needed).
        """
        pass

    @abstractmethod
    async def identify_content(self, pipeline_id: str, produced_content_id: str,
                               config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Identify the semantic content of a produced item (e.g., verse reference).
        May set review flags in metadata (e.g., {"review_flag": True, "reason": "verse_unknown"}).
        Returns: dict with identification data, or None if unknown.
        """
        pass
```

---

## 2. Data Model (SQLAlchemy / SQLite)

### 2.1 Core Tables (Engine-Owned)

```sql
-- Plugins registry
CREATE TABLE plugins (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL,
    version         TEXT NOT NULL,
    api_version     TEXT NOT NULL,
    module_path     TEXT NOT NULL,
    enabled         BOOLEAN DEFAULT 1,
    config_schema   TEXT,  -- JSONSchema
    installed_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Automation pipelines
CREATE TABLE pipelines (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    plugin_id       TEXT NOT NULL REFERENCES plugins(id),
    enabled         BOOLEAN DEFAULT 1,
    config_json     TEXT NOT NULL,  -- plugin-specific config
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Many-to-many: pipelines <-> platform_workers
CREATE TABLE pipeline_workers (
    pipeline_id     TEXT NOT NULL REFERENCES pipelines(id),
    worker_id       TEXT NOT NULL REFERENCES platform_workers(id),
    PRIMARY KEY (pipeline_id, worker_id)
);

-- Platform workers (social accounts)
CREATE TABLE platform_workers (
    id                  TEXT PRIMARY KEY,
    platform            TEXT NOT NULL,  -- validated in app code: youtube, instagram, tiktok, x, telegram, etc.
    display_name        TEXT NOT NULL,
    credentials_json    TEXT NOT NULL,  -- encrypted
    schedule_cron       TEXT,
    caption_template_override TEXT,
    hashtags_json       TEXT,
    enabled             BOOLEAN DEFAULT 1,
    last_posted_at      DATETIME,
    last_error_at       DATETIME,
    last_error_message  TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Posts (audit trail)
CREATE TABLE post_records (
    id                  TEXT PRIMARY KEY,
    produced_content_id TEXT NOT NULL REFERENCES produced_content(id),
    worker_id           TEXT NOT NULL REFERENCES platform_workers(id),
    status              TEXT NOT NULL CHECK(status IN ('pending','published','failed')),
    platform_post_id    TEXT,
    platform_url        TEXT,
    caption_used        TEXT,
    error_log           TEXT,
    attempt_count       INTEGER DEFAULT 0,
    published_at        DATETIME,
    UNIQUE(produced_content_id, worker_id)  -- CRITICAL: no duplicates
);

-- System activity log
CREATE TABLE activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
    level       TEXT CHECK(level IN ('info','warn','error','critical')),
    pipeline_id TEXT,
    worker_id   TEXT,
    event_type  TEXT NOT NULL,
    message     TEXT NOT NULL,
    metadata_json TEXT
);

-- System settings (key-value)
CREATE TABLE settings (
    key         TEXT PRIMARY KEY,
    value_json  TEXT NOT NULL,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Plugin-Owned Tables (Quran Plugin)

```sql
-- Ingredient library (generic enough for any plugin)
CREATE TABLE ingredients (
    id              TEXT PRIMARY KEY,
    pipeline_id     TEXT NOT NULL REFERENCES pipelines(id),
    type            TEXT NOT NULL,  -- plugin-defined (quran_clip, bg_image, bg_video)
    file_path       TEXT NOT NULL,
    source_url      TEXT,
    metadata_json   TEXT,
    status          TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
    approved_at     DATETIME,
    file_size_bytes INTEGER,
    duration_secs   REAL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Produced content (generic — not just videos)
CREATE TABLE produced_content (
    id                  TEXT PRIMARY KEY,
    pipeline_id         TEXT NOT NULL REFERENCES pipelines(id),
    ingredient_ids_json TEXT NOT NULL,  -- list of ingredient IDs used
    render_method       TEXT,           -- plugin-defined: video_compose, image_compose, text_only, passthrough
    file_path           TEXT,           -- NULL for text-only content
    thumbnail_path      TEXT,
    content_meta_json   TEXT,           -- plugin-defined metadata (verse ref, approval status, etc.)
    caption_text        TEXT,
    status              TEXT NOT NULL CHECK(status IN ('rendering','rendered','ready','published','failed')),
    render_log          TEXT,
    rendered_at         DATETIME,
    ready_at            DATETIME
);

-- content_meta_json examples by plugin:
-- Quran: {"verse_ref": "2:255", "surah": 2, "ayah": 255, "review_flag": false}
-- Quran (unknown): {"review_flag": true, "reason": "verse_unknown", "whisper_confidence": 0.42}
-- Hadith: {"source": "Bukhari", "book": 1, "hadith": 2, "narrator": "Abu Huraira"}

-- Quran-specific: verse cache (avoids repeated API calls)
CREATE TABLE verse_cache (
    surah_number    INTEGER NOT NULL,
    ayah_number     INTEGER NOT NULL,
    arabic_text     TEXT,
    translations_json TEXT,  -- {translator_id: text}
    tafseer_json    TEXT,
    fetched_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (surah_number, ayah_number)
);
```

---

## 3. API Endpoints (FastAPI)

### 3.1 System

```
GET    /api/health                 → {status, uptime, version, plugins_loaded}
GET    /api/dashboard              → aggregated stats for dashboard
GET    /api/settings               → all settings
PUT    /api/settings               → update settings (partial)
GET    /api/activity               → activity log with pagination
```

### 3.2 Pipelines

```
GET    /api/pipelines              → list all pipelines
POST   /api/pipelines              → create pipeline {name, plugin_id, config_json}
GET    /api/pipelines/{id}         → pipeline detail
PUT    /api/pipelines/{id}         → update config / name / enabled
DELETE /api/pipelines/{id}         → delete pipeline + confirm data loss
POST   /api/pipelines/{id}/trigger → manually trigger fetch/render/post
GET    /api/pipelines/{id}/stats   → queue depth, stock levels, last runs
```

### 3.3 Ingredients (Pipeline-Scoped)

```
GET    /api/pipelines/{id}/ingredients         → list with filters (type, status, source)
POST   /api/pipelines/{id}/ingredients/approve → {ingredient_ids}
POST   /api/pipelines/{id}/ingredients/reject  → {ingredient_ids}
DELETE /api/pipelines/{id}/ingredients         → {ingredient_ids} (physical delete)
GET    /api/pipelines/{id}/ingredients/{iid}   → detail + preview URL
```

### 3.4 Production Queue

```
GET    /api/pipelines/{id}/production          → list with status filter
GET    /api/pipelines/{id}/production/{cid}    → detail + stream URL
POST   /api/pipelines/{id}/production/{cid}/update_meta
                                               → {key, value} (plugin-specific, e.g. assign verse)
POST   /api/pipelines/{id}/production/{cid}/requeue
                                               → {worker_ids}
DELETE /api/pipelines/{id}/production/{cid}     → delete rendered content + file
```

### 3.5 Workers

```
GET    /api/workers                → list all workers
POST   /api/workers                → create worker
GET    /api/workers/{id}           → worker detail
PUT    /api/workers/{id}           → update schedule, caption, hashtags, enabled
DELETE /api/workers/{id}           → delete worker
POST   /api/workers/{id}/test      → test credentials (attempt login)
POST   /api/workers/{id}/post_now  → manually trigger post with next ready video
```

### 3.6 Posts

```
GET    /api/posts                  → list with filters (platform, pipeline, date, status)
GET    /api/posts/{id}             → post detail including error logs
```

---

## 4. Scheduling & Job Logic

### 4.1 Job Types

| Job | Trigger | Frequency | Locking |
|-----|---------|-----------|---------|
| `fetch_ingredients` | Cron per pipeline | Every 6 hours | Single fetch per pipeline at a time |
| `render_video` | Post-fetch or manual | On demand | Global render lock (1 FFmpeg) |
| `publish_post` | Cron per worker | Per worker schedule | Per-worker lock |
| `cleanup` | Cron global | Daily at 03:00 | — |
| `health_ping` | Interval | Every 5 minutes | — |

### 4.2 Render Lock Algorithm

```python
# Pseudo-code for render coordination
async def render_next(pipeline_id: str):
    # 1. Acquire global render lock (file-based POSIX lock on /tmp/flux-render.lock)
    if not acquire_lock("render", timeout=0):
        log.info("Render already in progress, skipping")
        return
    
    try:
        # 2. Pick next renderable item
        item = await select_next_for_render(pipeline_id)
        if not item:
            return
            
        # 3. Mark rendering
        await update_status(item.id, "rendering")
        
        # 4. Call plugin render
        result = await plugin.render(pipeline_id, item.ingredient_ids, config)
        
        # 5. Update DB
        await update_produced_content(item.id, file_path=result.path, status="rendered")
        
        # 6. Trigger post-render identification
        await schedule_job("identify_content", item.id, delay=0)
        
    except Exception as e:
        await update_status(item.id, "failed", error=str(e))
        raise
    finally:
        release_lock("render")
```

### 4.3 Post Publishing Algorithm

```python
async def publish_for_worker(worker_id: str):
    worker = await get_worker(worker_id)
    if not worker.enabled:
        return
        
    # 1. Find next ready, unpublished video for any pipeline attached to this worker
    content = await select_next_ready_content(worker_id)
    if not video:
        log.info(f"No ready videos for worker {worker_id}")
        return
        
    # 2. Build caption via plugin
    pipeline = await get_pipeline(video.pipeline_id)
    plugin = get_plugin(pipeline.plugin_id)
    caption = await plugin.build_caption(
        pipeline.id, content.id, pipeline.config, worker.config
    )
    
    # 3. Truncate to platform limit
    caption = truncate_to_platform_limit(caption, worker.platform)
    
    # 4. Attempt post with retry
    for attempt in range(1, 4):
        try:
            platform = get_platform_impl(worker.platform)
            post_id, url = await platform.post(
                worker.credentials, content.file_path, caption, content.thumbnail_path
            )
            await record_post(content.id, worker_id, "published", post_id, url, caption)
            return
        except TransientError as e:
            await asyncio.sleep(2 ** attempt * 30)  # 60s, 120s, 240s
        except PermanentError as e:
            await record_post(content.id, worker_id, "failed", error=str(e))
            await flag_worker_error(worker_id, str(e))
            return
            
    # All retries exhausted
    await record_post(content.id, worker_id, "failed", error="Max retries exceeded")
    await flag_worker_error(worker_id, "Max retries exceeded")
```

---

## 5. Error Handling Protocols

### 5.1 Error Classification

| Category | Examples | Action |
|----------|----------|--------|
| **Transient** | Network timeout, API rate limit, 503 | Retry with backoff |
| **Permanent** | Invalid credentials, account banned, 401/403 | Flag worker, notify admin, pause worker |
| **Content** | Verse unknown, inappropriate image | Move to manual review queue, notify admin |
| **Resource** | Disk full, thermal throttle | Pause affected jobs, notify admin, auto-resume when cleared |
| **Bug** | Unexpected exception, None reference | Log full traceback, notify admin, do not retry blindly |

### 5.2 Notification Matrix

| Event | Channel | Urgency |
|-------|---------|---------|
| Post published | Telegram | Info |
| Fetch completed (N items) | Telegram | Info |
| Render completed | Telegram | Info |
| Worker failed (permanent) | Telegram | Warning |
| Storage >= 80% | Telegram | Warning |
| Storage >= 95% | Telegram | Critical |
| Render failed 3× consecutive | Telegram | Critical |
| Verse unknown backlog > 5 | Telegram | Warning |
| Daemon restarted after crash | Telegram | Warning |
| GitHub Actions watchdog detects silence | Telegram + Email | Critical |

---

## 6. Caption Template Engine

### 6.1 Global Template Variables (Quran Plugin)

```jinja2
{{ verse_ref }}           → "Surah Al-Baqarah — 2:255"
{{ arabic_text }}         → Full Arabic verse
{{ translation }}         → Configured translation
{{ tafseer_excerpt }}     → Short tafseer summary
{{ custom_closing }}      → Configurable closing line
{{ hashtags }}            → Space-separated hashtags
{{ date }}                → Current date
```

### 6.2 Platform-Specific Overrides

- **X/Twitter:** Hard truncate to 280 chars. If truncated, append "..." + link to full post on Telegram/YouTube.
- **Instagram:** Max 2,200 chars. Auto-add line breaks for readability.
- **YouTube:** Description field allows 5,000 chars. Hashtags auto-linked by platform.
- **Telegram:** No limit. Full caption with formatting (Markdown supported).

### 6.3 Template Builder UI Logic

- Components are reordered via up/down arrows (or SortableJS if frontend complexity allows).
- Each block can be toggled on/off.
- Per-platform override checkbox: "Use custom template for this worker."
- Live preview renders template with sample data.
