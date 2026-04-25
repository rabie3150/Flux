# Flux — API & Integration Strategy

This document defines how Flux integrates with external services and how its internal APIs are structured for future extensibility.

---

## 1. Integration Philosophy

1. **Official APIs first.** Always prefer official, documented APIs. Unofficial methods are last-resort fallbacks.
2. **Graceful degradation.** If an API is down or rate-limited, the system pauses and retries — it does not crash.
3. **Credential isolation.** Each integration manages its own authentication; the core engine never handles raw passwords.
4. **Plugin-scoped integrations.** Content-source APIs (Quran, Pexels) are called by plugins. Platform APIs (YouTube, Telegram) are called by workers.

---

## 2. Internal API Design (FastAPI)

### 2.1 Design Principles

- **RESTful** resources with predictable URLs.
- **JSON** request/response bodies.
- **HTTP status codes** used semantically.
- **Pagination** via `?offset=` and `?limit=` (default limit 50, max 200).
- **Filtering** via query parameters.
- **Async** endpoints where I/O is involved (DB, file system, external APIs).

### 2.2 Error Response Format

```json
{
  "error": {
    "code": "WORKER_AUTHENTICATION_FAILED",
    "message": "Instagram session expired. Please re-authenticate.",
    "field": null,
    "retryable": true,
    "documentation_url": "https://flux.local/docs/errors/WORKER_AUTHENTICATION_FAILED"
  }
}
```

### 2.3 Versioning Strategy

- **URL versioning:** `/api/v1/...` reserved for future breaking changes.
- **v1 is implicit:** All current endpoints are `/api/...` and considered v1.
- When v2 is introduced, v1 remains supported for 6 months.

### 2.4 Authentication

| Context | Method |
|---------|--------|
| Admin panel (browser) | None — localhost-only; access via SSH port-forward |
| Internal service calls | None — same process |
| External scripts / API clients | Optional API key header `X-Flux-Key` (future) |

---

## 3. Content Source Integrations

### 3.1 quran.com API v4 (Primary)

| Detail | Value |
|--------|-------|
| **Base URL** | `https://api.quran.com/api/v4/` |
| **Auth** | None required |
| **Rate limit** | Generous (no documented hard limit) |
| **Endpoints used** | `GET /verses/by_key/{chapter}:{verse}`, `GET /resources/translations` |
| **Fallback** | alquran.cloud API |
| **Caching** | SQLite `verse_cache` table; cache forever (Quran text is immutable) |

```python
# Pseudo-client
async def fetch_verse(surah: int, ayah: int, translation: str = "en.sahih") -> dict:
    cache_key = (surah, ayah)
    if cached := db.verse_cache.get(cache_key):
        return cached
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.quran.com/api/v4/verses/by_key/{surah}:{ayah}",
            params={"translations": translation, "fields": "text_uthmani"}
        )
        resp.raise_for_status()
        data = resp.json()
        db.verse_cache.set(cache_key, data)
        return data
```

### 3.2 alquran.cloud API (Fallback)

| Detail | Value |
|--------|-------|
| **Base URL** | `https://api.alquran.cloud/v1/` |
| **Auth** | None |
| **Use case** | Fallback if quran.com is down; alternative translations |

### 3.3 Pexels API

| Detail | Value |
|--------|-------|
| **Base URL** | `https://api.pexels.com/v1/` (images), `/videos/` |
| **Auth** | `Authorization: {PEXELS_API_KEY}` |
| **Rate limit** | 200 requests/hour |
| **Endpoints** | `GET /search`, `GET /videos/search` |
| **Parameters** | `query`, `orientation=portrait`, `size=large`, `safe_search=true` |
| **Download** | Direct URL from response; no hotlinking (save locally) |

### 3.4 Unsplash API

| Detail | Value |
|--------|-------|
| **Base URL** | `https://api.unsplash.com/` |
| **Auth** | `Authorization: Client-ID {UNSPLASH_ACCESS_KEY}` |
| **Rate limit** | 50 requests/hour |
| **Endpoints** | `GET /search/photos` |
| **Parameters** | `query`, `orientation=portrait`, `content_filter=high` |

### 3.5 YouTube (Data API v3 — for uploads, not fetching)

| Detail | Value |
|--------|-------|
| **Auth** | OAuth 2.0 (refresh token flow) |
| **Scopes** | `https://www.googleapis.com/auth/youtube.upload` |
| **Rate limit** | 10,000 units/day |
| **Upload cost** | ~1,600 units |
| **Library** | `google-api-python-client` |

---

## 4. Platform Worker Integrations

### 4.1 Integration Matrix

| Platform | Method | Library | Auth | Rate Limit Strategy |
|----------|--------|---------|------|---------------------|
| **YouTube** | Official Data API v3 | `google-api-python-client` | OAuth refresh token | Quota tracking in DB; alert at 70% |
| **Telegram** | Official Bot API | `python-telegram-bot` | Bot token | None needed; batch sends |
| **Instagram** | Unofficial (Instagrapi) | `instagrapi` | Session JSON | 1 post/day; random delays; session reuse |
| **TikTok** | Unofficial API | `TikTokApi` | Session cookies | 1 post/week; fallback to manual. **No Selenium on Termux.** |
| **X / Twitter** | API v2 free tier | `tweepy` | Bearer token | API first; text-only fallback if media upload fails. **No Selenium on Termux.** |

### 4.2 Platform Worker Interface

All workers implement:

```python
class PlatformWorker(ABC):
    platform: str
    
    @abstractmethod
    async def authenticate(self, credentials: dict) -> bool:
        """Validate credentials without posting."""
        pass
    
    @abstractmethod
    async def post(self, file_path: str, caption: str, 
                   thumbnail_path: Optional[str] = None) -> Tuple[str, str]:
        """
        Publish content.
        Returns: (platform_post_id, platform_url)
        Raises: TransientError or PermanentError
        """
        pass
    
    @abstractmethod
    async def get_quota(self) -> Optional[dict]:
        """Return quota info if applicable (YouTube)."""
        pass
```

### 4.3 Error Translation Layer

Each platform adapter normalizes errors into the core engine's classification:

```python
class TransientError(Exception):
    """Retry with backoff."""
    pass

class PermanentError(Exception):
    """Do not retry; flag worker."""
    pass

# Example: YouTube adapter
if response.status == 403 and "quotaExceeded" in response.text:
    raise TransientError("Quota exceeded — retry tomorrow")
if response.status == 401:
    raise PermanentError("OAuth token invalid — re-authenticate")
```

---

## 5. Webhook & Callback Strategy

### 5.1 Inbound Webhooks

Flux does not need inbound webhooks for v1. Future expansions may include:

- **YouTube upload status callbacks** (optional polling is sufficient).
- **GitHub repository dispatch** (for remote triggers via GitHub Actions).

### 5.2 GitHub Actions Remote Trigger

GitHub Actions reaches Flux via its public URL (Cloudflare Tunnel or DDNS):

```yaml
# .github/workflows/remote-command.yml
name: Remote Command
on:
  workflow_dispatch:
    inputs:
      command:
        description: 'Command'
        required: true
        default: 'status'
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: |
          curl -fsS -X POST "${{ secrets.FLUX_PUBLIC_URL }}/api/system/remote" \
            -H "Authorization: Bearer ${{ secrets.FLUX_REMOTE_KEY }}" \
            -d "{\"command\":\"${{ github.event.inputs.command }}\"}"
```

Flux endpoint validates bearer token and executes whitelisted commands (`status`, `restart`, `trigger_pipeline`). Admin panel (`/admin/*`) is NOT exposed on the public URL.

---

## 6. API Rate Limit Budget (Daily)

| API | Limit | Flux Usage | Headroom |
|-----|-------|------------|----------|
| quran.com | ~unlimited | 1–30 calls/day (verse fetches) | Massive |
| Pexels | 200/hr | ~10 calls/day | Massive |
| Unsplash | 50/hr | ~5 calls/day | Massive |
| YouTube Data API | 10,000 units/day | ~1,600 per upload × 2 channels = 3,200 | 68% |
| Telegram Bot API | Effectively unlimited | 1–5 calls/day | Massive |
| Instagram (Instagrapi) | Undocumented | 1 post/day | Unknown — conservative |
| TikTok | Undocumented | 1 post/week | Unknown — very conservative |

**YouTube is the only API with a meaningful quota constraint.** Dashboard must display quota consumption.

---

## 7. Future API Expansion

| Integration | Purpose | When |
|-------------|---------|------|
| **Meta Graph API** | Facebook Reels / Pages | v1.3+ |
| **Pinterest API v5** | Video pins | v1.3+ |
| **WhatsApp Business API** | Channel posting | v1.3+ |
| **OpenAI API** | AI-generated captions or thumbnails | v2.0 (optional, cloud) |
| **Cloudflare R2 / S3** | Backup storage for media | v2.0 (optional, cloud) |
| **Stripe API** | If selling premium plugins | v2.0+ |

---

## 8. API Documentation

FastAPI auto-generates OpenAPI docs:

- **Swagger UI:** `http://phone-ip:8000/docs`
- **ReDoc:** `http://phone-ip:8000/redoc`

These are available on the LAN for operator reference. No additional documentation maintenance required for the API layer.
