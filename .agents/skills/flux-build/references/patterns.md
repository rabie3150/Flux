# Flux Project Patterns Reference

Load this file when implementing new features to understand existing conventions.

## Project Structure

```
flux/
├── main.py              # FastAPI entrypoint
├── config.py            # Pydantic Settings (all env vars)
├── db.py                # SQLAlchemy engine, session, Base
├── scheduler.py         # APScheduler setup
├── lock.py              # File-based render lock
├── storage.py           # Storage budget tracker
├── notifications.py     # Telegram bot wrapper
├── core/                # Business logic services
│   ├── pipeline.py
│   ├── ingredients.py
│   ├── production.py
│   └── workers.py
├── api/                 # FastAPI routers
│   ├── system.py
│   ├── pipelines.py
│   ├── ingredients.py
│   ├── production.py
│   ├── workers.py
│   └── posts.py
├── platforms/           # Social media adapters
│   ├── base.py          # PlatformWorker ABC
│   ├── youtube.py
│   ├── telegram.py
│   ├── instagram.py
│   ├── tiktok.py
│   └── x.py
├── plugins/             # Content type plugins
│   ├── base.py          # ContentPlugin ABC + RenderResult
│   └── quran/           # Reference plugin
│       ├── plugin.py
│       ├── fetch.py
│       ├── render.py
│       ├── identify.py
│       └── caption.py
└── static/admin/        # HTML + Alpine.js + CSS
    ├── index.html
    ├── css/
    │   ├── vars.css     # All colors, fonts, spacing tokens
    │   └── app.css
    └── js/
        └── app.js
```

## Database Conventions

- Table names: plural, snake_case (`produced_content`, `platform_workers`)
- Column names: snake_case
- Primary keys: `TEXT` UUIDs (not integers)
- JSON fields: named `_json` suffix (`metadata_json`, `hashtags_json`)
- Timestamps: `created_at`, `updated_at`, `rendered_at`
- Status enums: stored as `TEXT` in DB, validated in Python (no CHECK constraints)

## API Conventions

- Base path: `/api/...`
- Admin panel: `/admin/*` (static files)
- Health: `/api/health`
- Metrics: `/api/metrics`
- Error format: `{"error": {"code": "...", "message": "...", "retryable": bool}}`
- Pagination: `?offset=&limit=` (default 50, max 200)

## Frontend Conventions

- CSS variables in `vars.css`:
  ```css
  :root {
    --color-bg: #f9f8f5;
    --color-surface: #ffffff;
    --color-accent: #185FA5;
    --color-text: #1a1917;
    --color-muted: #6b6960;
    --radius: 8px;
    --font-base: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  ```
- Alpine.js directives preferred over custom JS.
- No inline `style=` attributes. Use utility classes or CSS vars.
- Touch-friendly: min 44px tap targets.

## Plugin Interface

```python
@dataclass
class RenderResult:
    file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    caption: str = ""
    metadata: Dict[str, Any] = None
    attachments: List[str] = None

class ContentPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def fetch(self, pipeline_id: str, config: Dict) -> List[Dict]: ...

    @abstractmethod
    async def render(self, pipeline_id: str, ingredient_ids: List[str],
                     config: Dict) -> RenderResult: ...

    @abstractmethod
    async def build_caption(self, pipeline_id: str, produced_content_id: str,
                            config: Dict, worker_config: Dict) -> str: ...

    @abstractmethod
    async def identify_content(self, pipeline_id: str, produced_content_id: str,
                               config: Dict) -> Optional[Dict]: ...
```

## Configuration Access

```python
from flux.config import settings

# Never os.getenv directly in business logic
storage_path = settings.STORAGE_PATH
bot_token = settings.TELEGRAM_BOT_TOKEN
```

## Async Patterns

- All I/O is async: `async def`, `await`.
- Database: use `async_session` from `flux.db`.
- External APIs: use `httpx.AsyncClient`.
- FFmpeg/subprocess: use `asyncio.create_subprocess_exec`.
