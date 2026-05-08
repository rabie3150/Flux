# Flux — Conception Archive Audit: Done vs Not Done

> **Methodology**: Every feature, component, and system mentioned in documents `01-prd` through `16-build-plan` was cross-referenced against the actual codebase at `d:\Projects\Flux`. Items are marked:
> - `[x]` — **Done** (code exists and appears functional)
> - `[/]` — **In Progress** (partial implementation / stubs only)
> - `[ ]` — **Not Started** (no code found)

---

## 1. Build Plan Phases (doc: `16-build-plan`)

### Phase 0: Foundation Spike ✅
- [x] Project skeleton — `main.py` runs, FastAPI serves `/api/health`
- [x] Bootstrap script — `scripts/bootstrap.sh`
- [x] SQLite + WAL — `flux/db.py`
- [x] Plugin loader — `flux/plugins/loader.py`
- [x] FFmpeg spike — validated on Galaxy S21
- [x] Start script — `scripts/start.sh`

### Phase 1: Core Engine ✅
- [x] Database schema — all core tables in `flux/models.py`
- [x] Pipeline CRUD — `flux/api/pipelines.py`
- [x] Ingredient service — `flux/core/ingredients.py` + `flux/api/ingredients.py`
- [x] APScheduler — `flux/scheduler.py`
- [x] File lock — `flux/core/lock.py`
- [x] Minimal admin UI — `flux/static/admin/`
- [x] Settings — `.env` loaded via `flux/config.py` (Pydantic)

### Phase 2: Quran Plugin — Fetch ✅
- [x] yt-dlp fetch — `flux/plugins/quran/fetch.py`
- [x] Pexels fetch — `flux/plugins/quran/backgrounds.py`
- [x] Unsplash fallback — in `backgrounds.py`
- [x] Approval gate — bulk approve/reject in `flux/api/ingredients.py`
- [x] Stock monitoring — fetch triggers on low stock
- [ ] **Telegram notify** — "N clips pending approval" with deep link (moved to Phase 5, but still not implemented)

### Phase 3: Render Pipeline ✅
- [x] Colorkey filter — `flux/plugins/quran/render_filters.py`
- [x] Overlay — FFmpeg compositing in `render.py`
- [x] Image slideshow — in `render_inputs.py`
- [x] Video background — in `render_inputs.py`
- [x] Text contrast — soft glow/shadow in `render_filters.py`
- [x] Thumbnail extraction — in `render.py`
- [x] Render queue — DB schema + lock mechanism
- [x] Render preview — API endpoint for streaming MP4

### Phase 4: Content ID & Captions ✅
- [x] Metadata regex — `flux/plugins/quran/identify.py`
- [x] Gemini AI fallback — `flux/plugins/quran/ai.py`
- [x] Manual assignment — Admin modal in pipeline production tab
- [x] quran.com API — `flux/plugins/quran/api.py`
- [x] Caption template — Jinja2 per-platform templates in `plugin.py`
- [x] Platform overrides — smart truncation for X, no Arabic for IG

### Phase 5: Platform Workers & Publishing 🚧
- [x] Multi-strategy architecture — `flux/platforms/publisher.py` with registry
- [x] Publisher framework — `PlatformPublisher` base class + factory
- [x] Publishing orchestrator — `flux/core/publish.py` (scheduler-driven)
- [x] Deduplication — `uq_post_dedup` unique constraint on `PostRecord`
- [x] Post log — `PostRecord` model with full tracking
- [x] Auto-delete — `_maybe_auto_delete()` in `publish.py`
- [x] Manual trigger — `POST /api/workers/{id}/post` endpoint
- [x] Scheduler integration — `flux/core/scheduler_jobs.py`
- [x] **YouTube upload** — implemented via Data API v3 (OAuth2)
- [ ] **TikTok post** — stub returns `not yet implemented`
- [ ] **Instagram post** — stub returns `not yet implemented` (all 3 strategies: official, unofficial, third-party)
- [ ] **X/Twitter post** — stub returns `not yet implemented`
- [ ] **Telegram publisher** — **no Telegram platform worker exists at all** (not even a stub file)

### Phase 6: Admin Panel Polish ⏳
- [ ] **Alpine.js UI** — no Alpine.js; current UI is vanilla JS (`app.js`, `ui.js`)
- [/] Dashboard — API endpoint exists (`/api/system/dashboard`), basic UI exists, but no visual bars/charts
- [ ] **Real-time updates** — no polling or SSE/WebSocket for live render progress
- [ ] **Pipeline config form** — no form generated from plugin `config_schema`
- [ ] **Worker config** — no cron builder, no caption override editor, no hashtag editor, no test button
- [ ] **Mobile layout** — `responsive.css` exists (1.6KB) but is minimal; not touch-optimized per wireframes

### Phase 7: Watchdog, Remote Access & Hardening ✅
- [x] **Cloudflare Tunnel** — setup script `scripts/setup_cloudflare_tunnel.sh` with restricted ingress
- [x] **GitHub Actions watchdog** — `.github/workflows/watchdog.yml` (30-min health ping + Telegram alert)
- [x] **Remote restart** — `.github/workflows/remote-command.yml` with `workflow_dispatch`
- [x] **Backup cron** — APScheduler daily job at 04:00 UTC with 7-day rotation (`flux/core/hardening.py`)
- [x] **SSH hardening** — `scripts/harden_ssh.sh` (key-only auth enforcement)
- [x] **Log rotation** — `RotatingFileHandler` 5MB × 5 backups in `logger.py` (was already correct)
- [x] **Thermal guard** — CPU temp check via sysfs before renders in `lock.py` → blocks at ≥65°C

---

## 2. Core Engine Features (docs: `01-prd`, `06-fsd`, `08-sad`)

### F-01 to F-05: Core Automation
- [x] F-01: Persistent daemon — `start.sh` with restart loop
- [/] F-02: Survive reboots — APScheduler persists; Termux:Boot integration in `bootstrap.sh` but **no interrupted-render recovery**
- [x] F-03: Multiple independent pipelines — DB schema supports it
- [x] F-04: Each pipeline associated with one plugin — `pipeline.plugin_id` FK
- [x] F-05: Each pipeline publishes to one or more workers — `pipeline_workers` junction table

### F-06 to F-07: Admin & Notifications
- [x] F-06: Web admin panel on `:8000/admin` — mounted as static files
- [ ] **F-07: Telegram notifications** for critical events — `config.py` has `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` fields, `logger.py` references Telegram, but **no actual notification service module** (`notifications.py` does not exist)

### Missing Modules (planned in `08-sad` / `16-build-plan`)
- [x] **`storage.py`** — Storage budget tracker (`flux/core/storage.py`)
- [ ] **`notifications.py`** — Telegram bot notification service (no file exists)

---

## 3. Quran Plugin Features (docs: `01-prd`, `06-fsd`, `09-data-strategy`)

### F-10 to F-18: Quran Content Pipeline
- [x] F-10: Monitor & download clips from YouTube — `fetch.py`
- [x] F-11: Pending approval state — all ingredients default to `pending`
- [x] F-12: Background images/videos from Pexels/Unsplash — `backgrounds.py`
- [x] F-13: Compose rendered videos — `render.py` + `render_filters.py` + `render_inputs.py`
- [x] F-14: Verse identification 3-tier fallback — regex → Gemini AI → manual (in `identify.py` + `ai.py`)
- [x] F-15: Fetch Arabic text, translation, tafseer — `api.py` (quran.com)
- [x] F-16: Per-platform captions — `build_caption()` in `plugin.py`
- [x] F-17: Extract thumbnail — in `render.py`
- [x] F-18: Queue for publishing — `ProducedContent` with status flow

### Missing from Quran Plugin
- [ ] **`caption.py`** — Conceived as standalone module (doc `16-build-plan` line 96); caption logic lives inside `plugin.py` instead (not necessarily wrong, just different from plan)
- [ ] **`plugin.yaml` manifest** — Conceived in `06-fsd` §1.1; plugins use Python class registration instead of YAML manifests
- [ ] **Whisper.cpp / fuzzy match** — `09-data-strategy` §4.1 mentions `fallback_method: whisper_fuzzy_match`; no Whisper integration exists. Gemini AI is used as the only fallback.

---

## 4. Publishing Features (docs: `01-prd`, `06-fsd`, `12-api-strategy`)

### F-20 to F-25
- [x] F-20: Manual "post now" + cron triggers — API endpoint + scheduler integration
- [x] F-21: `post_records` dedup — unique constraint `(produced_content_id, worker_id)`
- [x] F-22: Retry 3× with backoff — `publish.py` MAX_RETRIES=3
- [/] F-23: Platform workers for YouTube, Telegram, Instagram, TikTok, X — **all are stubs only**
  - [x] YouTube Data API v3 upload — implemented
  - [ ] Telegram Bot API posting — **no platform file exists** (not even a stub)
  - [ ] Instagram (Instagrapi or Graph API) — stub
  - [ ] TikTok (Business API) — stub
  - [ ] X API v2 — stub
- [ ] F-24: Multiple accounts per platform — model supports it; no UI/workflow exists
- [x] F-25: Auto-delete after successful publish — `_maybe_auto_delete()` in `publish.py`

### Platform Worker Interface (doc: `12-api-strategy` §4.2)
- [x] `publish()` method — all stubs implement it
- [ ] **`authenticate()` method** — conceived in FSD; **not in base class**
- [ ] **`get_quota()` method** — conceived in FSD; **not in base class**
- [ ] **`TransientError` / `PermanentError` exceptions** — conceived in `12-api-strategy` §4.3; current impl uses `PublishResult.transient` flag instead (different pattern, works but diverged)

---

## 5. Admin Panel Screens (docs: `03-info-arch`, `05-wireframes`)

### Dashboard (`/admin`)
- [/] System health indicator — health dot in sidebar exists
- [ ] **Uptime display** — no uptime shown in UI
- [x] **Storage meter** — implemented `get_storage_budget()` for dashboard API
- [/] Pipeline cards — basic list, not rich cards per wireframe
- [/] Platform worker cards — basic list, not card layout
- [/] Recent activity — API endpoint exists; basic render in UI
- [ ] **Alerts banner** — no critical alerts banner
- [ ] **Stock level bars** — no horizontal bars per ingredient category
- [ ] **Next scheduled action** — not shown

### Pipeline Detail (`/admin/pipelines/{id}`)
- [/] Overview tab — basic pipeline info displayed
- [/] Ingredients tab — grid of cards with approve/reject
- [/] Production tab — table with status filters
- [ ] **Settings tab** — no pipeline config editor (source channels, keywords, timing sets)
- [ ] **Render preview player** — API exists, no embedded video player in UI

### Worker Detail (`/admin/workers/{id}`)
- [ ] **Schedule editor** — no cron builder
- [ ] **Caption override editor** — no template editor
- [ ] **Hashtag editor** — no tag management UI
- [ ] **Test credentials button** — no `POST /api/workers/{id}/test` endpoint
- [ ] **Danger zone** — no disconnect/delete section

### Post Log (`/admin/posts`)
- [ ] **Post history list** — navigation button exists but **no `posts.py` API router**
- [ ] **Post detail view** — no API endpoint for individual post details
- [ ] **Filters** (platform, pipeline, date, status) — no implementation

### System Settings (`/admin/system/settings`)
- [/] Key-value settings — CRUD API exists (`/api/system/settings`)
- [ ] **Settings UI with tabs** (General, Library, Sources, Captions, Timing, Security) — no tabbed settings UI
- [ ] **Storage budget editor** — no UI
- [ ] **Auto-delete policy toggle** — no UI
- [ ] **Timezone selector** — no UI
- [ ] **Caption template builder** — no reorderable component editor (SortableJS)
- [ ] **Timing set editor** — no UI

### Plugin Manager (`/admin/system/plugins`)
- [/] Plugin list — navigation button exists; basic display
- [ ] **Enable/disable toggle** — no UI toggle
- [ ] **Version/API info display** — not shown per wireframe
- [ ] **Plugin upload from ZIP/Git** — not implemented

---

## 6. API Endpoints (doc: `06-fsd` §3)

### System APIs
- [x] `GET /api/health` — implemented
- [x] `GET /api/dashboard` → mapped to `/api/system/dashboard`
- [x] `GET /api/settings` → `/api/system/settings`
- [x] `PUT /api/settings` → `/api/system/settings/{key}`
- [x] `GET /api/activity` → `/api/system/activity`
- [ ] **`GET /api/metrics`** — Prometheus-compatible endpoint (doc `13-monitoring` §6.2; not implemented)

### Pipeline APIs
- [x] `GET /api/pipelines`
- [x] `POST /api/pipelines`
- [x] `GET /api/pipelines/{id}`
- [x] `PUT /api/pipelines/{id}`
- [x] `DELETE /api/pipelines/{id}`
- [x] `POST /api/pipelines/{id}/trigger`
- [/] `GET /api/pipelines/{id}/stats` — endpoint exists but returns limited data

### Ingredient APIs
- [x] `GET /api/pipelines/{id}/ingredients`
- [x] `POST /api/pipelines/{id}/ingredients/approve`
- [x] `POST /api/pipelines/{id}/ingredients/reject`
- [x] `DELETE /api/pipelines/{id}/ingredients`
- [ ] **`GET /api/pipelines/{id}/ingredients/{iid}`** — individual ingredient detail not confirmed

### Production APIs
- [x] `GET /api/pipelines/{id}/production`
- [x] `GET /api/pipelines/{id}/production/{cid}`
- [x] `POST /api/pipelines/{id}/production/{cid}/update_meta`
- [ ] **`POST /api/pipelines/{id}/production/{cid}/requeue`** — not confirmed
- [ ] **`DELETE /api/pipelines/{id}/production/{cid}`** — not confirmed

### Worker APIs
- [x] `GET /api/workers`
- [x] `POST /api/workers`
- [x] `GET /api/workers/{id}`
- [x] `PUT /api/workers/{id}`
- [x] `DELETE /api/workers/{id}`
- [ ] **`POST /api/workers/{id}/test`** — test credentials endpoint not found
- [x] `POST /api/workers/{id}/post_now` → mapped to `POST /api/workers/{id}/post`

### Post APIs
- [ ] **`GET /api/posts`** — no posts router found
- [ ] **`GET /api/posts/{id}`** — no post detail endpoint

### Remote API
- [x] **`POST /api/system/remote`** — remote command endpoint (for GitHub Actions; doc `12-api-strategy` §5.2; stub implemented)

---

## 7. Infrastructure & Deployment (doc: `10-infra-plan`)

- [x] Bootstrap script — `scripts/bootstrap.sh`
- [x] Start script — `scripts/start.sh`
- [x] `.env.example` — exists with documented variables
- [ ] **Termux:Boot integration** — `bootstrap.sh` copies to `~/.termux/boot/` but not tested/validated
- [x] **Cloudflare Tunnel setup** — setup script `scripts/setup_cloudflare_tunnel.sh`
- [ ] **Tailscale documentation** — mentioned but no setup scripts
- [x] **Automated DB backup** — APScheduler daily job at 04:00 UTC in `scheduler_jobs.py` + `hardening.py`
- [x] **Log rotation config** — `RotatingFileHandler` with 5MB/5 backups in `logger.py` (confirmed working)
- [ ] **Alembic migrations** — no `alembic/` directory exists; tables created via `create_all()`
- [ ] **Disaster recovery playbook** — documented only, no automation

---

## 8. Monitoring, Observability & Alerting (doc: `13-monitoring`)

### Health Check
- [x] `GET /api/health` — returns status, uptime, version
- [x] Rich health endpoint — `/api/health` returns `checks.database`, `checks.scheduler`, `checks.storage`, `checks.thermal`, `checks.workers`
- [x] **Internal health job** — APScheduler 5-min interval in `scheduler_jobs.py`
- [x] **`degraded` / `unhealthy` status** — computed from subsystem check results

### Alerting Rules
- [ ] **Immediate Telegram alerts** — worker failed, storage critical, render failed 3×, verse backlog, DB error
- [ ] **Daily digest alerts** — summary of posts/renders/failures
- [ ] **Weekly quota alerts** — YouTube quota usage
- [ ] **Storage trend alerts** — weekly delta notifications

### Metrics
- [ ] **`GET /api/metrics`** — Prometheus-compatible text endpoint
- [ ] **Key metrics tracked** — `flux_posts_total`, `flux_renders_total`, `flux_storage_used_bytes`, etc.
- [ ] **Health snapshots** — stored in DB for trend analysis

### Dashboard Observability
- [ ] **Daemon uptime in UI** — not shown
- [ ] **Next scheduled action** — not shown
- [ ] **Render progress polling** — no real-time render status
- [ ] **Worker status dots** — sidebar has health dot but not per-worker
- [ ] **Storage bar** — no visual meter
- [ ] **Activity log calendar view** — not implemented
- [ ] **Render time chart** — not implemented
- [ ] **Storage trend chart** — not implemented

---

## 9. Security (doc: `11-security`)

### Access Control
- [x] Admin panel bound to `127.0.0.1` — `uvicorn.run()` uses `host="127.0.0.1"`
- [x] No auth required (localhost only) — by design
- [ ] **Optional API key for `/api/system/remote`** — endpoint doesn't exist
- [ ] **IP allowlist** — not implemented

### Credential Security
- [x] Fernet encryption — `flux/core/crypto.py`
- [x] Master key from `FLUX_MASTER_KEY` env var — validated in `config.py`
- [ ] **Key rotation CLI command** — not implemented
- [x] **OAuth flow for YouTube** — implemented via `scripts/youtube_auth.py`

### Platform Ban Mitigation
- [ ] **Rate limiting enforced** — no `randint(0, 600)` jitter before posts
- [ ] **Post timing window** — no 07:00–21:00 restriction
- [ ] **Session reuse** — no Instagram session management
- [x] Circuit breaker — worker paused after 3 failures (in `publish.py`)

### Content Integrity
- [x] Approval gate — all ingredients start as `pending`
- [x] Verse identification fallback — 3-tier (regex → Gemini → manual)
- [x] Keyword blocklist — in `backgrounds.py`

### Log Redaction
- [/] Log redaction — `logger.py` references credential sanitization but unclear if comprehensive `REDACT_PATTERNS` from doc §4.4 are implemented

---

## 10. Data Strategy (doc: `09-data-strategy`)

### Content Model
- [x] 4-layer stack (Sources → Ingredients → Produced Content → Post Records)
- [x] Generic ingredient schema — `metadata_json` for plugin-specific data
- [x] Render modes — `video_compose` supported; `image_compose`, `text_only`, `passthrough` defined but untested

### Stock Management
- [/] Auto-fetch on low stock — trigger exists but no per-type threshold config in settings UI
- [x] **Pause fetch on max stock** — implemented in `trigger_fetch`
- [x] **StockLevel dataclass** — implemented in `flux/core/ingredients.py`

### Data Retention
- [x] **Auto-delete rejected ingredients after 7 days** — implemented in `cleanup_database`
- [x] **Activity log auto-truncate after 30 days** — implemented in `cleanup_database`
- [x] **Render log cleanup after 7 days** — implemented in `cleanup_database`
- [x] Auto-delete published videos — `_maybe_auto_delete()` exists

### Multi-Pipeline Isolation
- [x] `pipeline_id` FK on ingredients — enforced
- [x] `pipeline_id` FK on produced_content — enforced
- [x] Many-to-many workers — `pipeline_workers` junction table
- [x] **Per-pipeline storage tracking** — added `storage` dict to `/api/pipelines/{id}/stats`
- [x] Global render lock — one FFmpeg at a time

---

## 11. Testing (doc: `16-build-plan` §5)

### Unit Tests
- [x] `tests/unit/test_health.py` — exists
- [ ] **Plugin base tests** — RenderResult validation, hook signatures
- [ ] **Verse ID regex tests** — patterns against sample titles
- [ ] **Caption template tests** — Jinja2 rendering, truncation
- [ ] **Lock tests** — acquire/release, timeout, concurrency
- [x] **Storage budget tests** — `tests/unit/test_storage.py`
- [ ] **Notification format tests** — no `notifications.py` module

### Integration Tests
- [x] `test_pipelines.py` — Pipeline CRUD
- [x] `test_ingredients.py` — Ingredient lifecycle
- [x] `test_quran_fetch.py` — Quran fetch trigger
- [x] `test_quran_render.py` — Render integration
- [x] `test_system.py` — System health/settings
- [x] `test_workers.py` — Worker CRUD
- [ ] **Post dedup tests** — double-post → 409 or skipped
- [ ] **Publish flow tests** — full publish lifecycle

### Device Tests
- [ ] **`@pytest.mark.device` marker** — no device test directory
- [ ] **FFmpeg ARM render test** — not in test suite
- [ ] **yt-dlp fetch on device** — not in test suite
- [ ] **48-hour soak test** — not created

### Manual Checklists
- [ ] **Per-phase `PHASE_N_CHECKLIST.md`** — only `PHASE_4_PLAN.md` exists

---

## 12. Post-v1.0 / Future Features (docs: `14-content-roadmap`, `16-build-plan` §8)

These are explicitly out of scope for v1 but documented for future:

- [ ] Hadith image plugin (`image_compose` render mode)
- [ ] Multi-pipeline coordination (queue fairness)
- [ ] Best-time-to-post (YouTube analytics)
- [ ] Plugin marketplace (git-based install from admin)
- [ ] Meta Graph API (Facebook/Instagram official)
- [ ] Daily reminder threads plugin
- [ ] News summary clips plugin
- [ ] Community submission queue plugin
- [ ] A/B testing framework
- [ ] AI-assisted captioning (OpenAI)
- [ ] Content calendar visual view
- [ ] Cross-pipeline coordination
- [ ] Multi-user admin / RBAC
- [ ] Cloud deployment (Docker/VPS)

---

## Summary Stats

| Category | Done | In Progress | Not Started | Total |
|----------|------|-------------|-------------|-------|
| Build Plan Phases 0–4 | 31 | 0 | 0 | 31 |
| Build Plan Phase 5 | 9 | 0 | 4 | 13 |
| Build Plan Phase 6 | 0 | 1 | 5 | 6 |
| Build Plan Phase 7 | 7 | 0 | 0 | 7 |
| Core Engine | 7 | 1 | 2 | 10 |
| Platform Workers | 2 | 1 | 5 | 8 |
| Admin UI Screens | 1 | 4 | 23 | 28 |
| API Endpoints | 19 | 1 | 6 | 26 |
| Infrastructure | 6 | 0 | 4 | 10 |
| Monitoring & Alerting | 4 | 0 | 14 | 18 |
| Security | 6 | 1 | 3 | 10 |
| Data Strategy | 12 | 0 | 0 | 12 |
| Testing | 7 | 0 | 8 | 15 |
| **TOTAL** | **111** | **9** | **74** | **194** |

> **~52% done, ~6% in-progress, ~43% not started.** Phase 7 (hardening/watchdog/remote) is now complete. The largest remaining gaps are: platform publishing (4 stubs), admin UI polish (28 items), and monitoring/alerting notifications.
