# Database Documentation

## What This System Does

Flux uses **SQLite** with **WAL mode** as its single database. All data — pipelines, ingredients, produced content, post history, activity logs, and settings — lives in one file (`app.db`). The schema is designed to be generic: the core engine owns the tables, and plugin-specific metadata lives in JSON columns.

## Current Status

| Component | Status | Phase |
|-----------|--------|-------|
| Async SQLAlchemy engine | ✅ Implemented | 0 |
| WAL mode + foreign keys | ✅ Implemented | 0 |
| Session dependency (`get_db`) | ✅ Implemented | 0 |
| Core models (all tables) | ✅ Implemented | 1 |
| `init_db()` table creation | ✅ Implemented | 1 |
| Alembic migrations | 🚧 Pending | 2 |
| `verse_cache` (Quran plugin) | 🚧 Pending | 2 |

## Technology Choices

| Choice | Rationale |
|--------|-----------|
| SQLite | Single-node deployment; no separate DB server needed |
| WAL mode | Concurrent reads during writes; better performance on Android |
| aiosqlite | Async-compatible SQLite driver for FastAPI |
| SQLAlchemy 2.0 | Modern async ORM; type hints; declarative models |
| JSON columns | Plugin extensibility without schema migrations |

## Connection Setup

```python
# flux/db.py
engine = create_async_engine("sqlite+aiosqlite:///~/flux/app.db")
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

WAL mode and foreign keys are enabled on every connection via SQLAlchemy event listener:

```python
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

## Schema Overview

### Core Tables (Engine-Owned)

| Table | Purpose |
|-------|---------|
| `plugins` | Registered plugins with manifest metadata |
| `pipelines` | Automation pipelines (one per content type) |
| `platform_workers` | Social media accounts and their schedules |
| `pipeline_workers` | Many-to-many: which workers serve which pipelines |
| `ingredients` | Raw, approved source materials |
| `produced_content` | Rendered artifacts ready for publishing |
| `post_records` | Immutable audit trail of every post attempt |
| `activity_log` | System events with timestamps |
| `settings` | Key-value runtime configuration |

### Plugin Tables

| Table | Plugin | Purpose |
|-------|--------|---------|
| `verse_cache` | Quran | Cached verse text from quran.com API |

## Generic Schema Design

The core tables use JSON columns for plugin-specific data:

- `pipelines.config_json` — plugin-defined configuration (source channels, keywords, etc.)
- `ingredients.metadata_json` — plugin-defined metadata (channel, photographer, etc.)
- `produced_content.content_meta_json` — plugin-defined content metadata (verse ref, review flags, etc.)
- `produced_content.ingredient_ids_json` — list of ingredient IDs used in render

This means **adding a new plugin never requires a core schema migration**.

### Example: Quran vs Hadith in the Same Schema

```python
# Quran pipeline produces video
produced_content {
    pipeline_id: "pipeline_quran_001",
    render_method: "video_compose",
    file_path: "/storage/.../video_001.mp4",
    content_meta_json: '{"verse_ref": "2:255", "surah": 2, "ayah": 255}'
}

# Hadith pipeline produces image
produced_content {
    pipeline_id: "pipeline_hadith_001",
    render_method: "image_compose",
    file_path: "/storage/.../hadith_001.png",
    content_meta_json: '{"source": "Bukhari", "book": 1, "hadith": 2}'
}
```

## State Machines

### Ingredient States

```
pending → approved → eligible for render
      → rejected → auto-delete after 7 days
```

### Produced Content States

```
rendering → rendered → ready → published
    |          |
    v          v
  failed   (identify content)
             |
        verse known? ──Yes──> ready
            |
            No
            |
        needs_review (admin notified)
```

## Conception References

- Full schema SQL: `conception_archive/06-functional-specification-document.md` (Section 2)
- Data flow design: `conception_archive/09-data-strategy-and-content-pipeline-design.md`
