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
- [x] **F-07: Telegram notifications** for critical events — `notifications.py` implemented

### Missing Modules (planned in `08-sad` / `16-build-plan`)
- [x] **`storage.py`** — Storage budget tracker (`flux/core/storage.py`)
- [x] **`notifications.py`** — Telegram bot notification service (`flux/core/notifications.py`)

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
- [x] System health indicator — health dot in sidebar exists
- [x] **Uptime display** — displayed in metrics row
- [x] **Storage meter** — implemented `get_storage_budget()` for dashboard API
- [x] Pipeline cards — implemented with status and row layout
- [x] Platform worker cards — implemented in compact grid layout
- [x] Recent activity — implemented with rich event table
- [x] **Alerts banner** — implemented for failed renders and unknown verses
- [x] **Stock level bars** — visualized via Pipeline Flow stages
- [x] **Next scheduled action** — calculated and shown in metrics row

### Pipeline Detail (`/admin/pipelines/{id}`)
- [x] Overview tab — pipeline flow and metrics displayed
- [x] Ingredients tab — grid of media cards with bulk approve/reject actions
- [x] Production tab — table with status filters and render triggers
- [x] **Settings tab** — JSON configuration editor and toggle implemented
- [x] **Render preview player** — embedded HTML5 video modal player implemented

### Worker Detail (`/admin/workers/{id}`)
- [x] **Schedule editor** — cron input field and save action
- [x] **Caption override editor** — textarea implemented
- [x] **Hashtag editor** — comma-separated input implemented
- [x] **Test credentials button** — API bound to worker detail view
- [x] **Danger zone** — delete and disconnect buttons available

### Post Log (`/admin/posts`)
- [x] **Post history list** — implemented in Post Log view
- [x] **Post detail view** — detailed modal view showing attempts, URL, and errors
- [x] **Filters** (platform, pipeline, date, status) — implemented via dropdowns

### System Settings (`/admin/system/settings`)
- [x] Key-value settings — CRUD API exists (`/api/system/settings`)
- [x] **Settings UI with tabs** — unified global settings view
- [x] **Storage budget editor** — inline number input
- [x] **Auto-delete policy toggle** — CSS toggle switch implemented
- [x] **Timezone selector** — inline text input
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
- [x] **`GET /api/metrics`** — Prometheus-compatible endpoint

### Pipeline APIs
- [x] `GET /api/pipelines`
- [x] `POST /api/pipelines`
- [x] `GET /api/pipelines/{id}`
- [x] `PUT /api/pipelines/{id}`
- [x] `DELETE /api/pipelines/{id}`
- [x] `POST /api/pipelines/{id}/trigger`
- [x] `GET /api/pipelines/{id}/stats` — pipeline aggregate stats

### Ingredient APIs
- [x] `GET /api/pipelines/{id}/ingredients`
- [x] `POST /api/pipelines/{id}/ingredients/approve`
- [x] `POST /api/pipelines/{id}/ingredients/reject`
- [x] `DELETE /api/pipelines/{id}/ingredients`
- [x] **`GET /api/pipelines/{id}/ingredients/{iid}`** — individual ingredient detail

### Production APIs
- [x] `GET /api/pipelines/{id}/production`
- [x] `GET /api/pipelines/{id}/production/{cid}`
- [x] `POST /api/pipelines/{id}/production/{cid}/update_meta`
- [x] **`POST /api/pipelines/{id}/production/{cid}/requeue`**
- [x] **`DELETE /api/pipelines/{id}/production/{cid}`**

### Worker APIs
- [x] `GET /api/workers`
- [x] `POST /api/workers`
- [x] `GET /api/workers/{id}`
- [x] `PUT /api/workers/{id}`
- [x] `DELETE /api/workers/{id}`
- [x] **`POST /api/workers/{id}/test`** — test credentials endpoint
- [x] `POST /api/workers/{id}/post_now` → mapped to `POST /api/workers/{id}/post`

### Post APIs
- [x] **`GET /api/posts`** — implemented in posts.py
- [x] **`GET /api/posts/{id}`** — implemented in posts.py

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
- [x] **Immediate Telegram alerts** — implemented in `notifications.py` and hooked into core (worker fail, storage critical, render fail, verse backlog, db error)
- [x] **Daily digest alerts** — `send_daily_digest` registered in `scheduler_jobs.py`
- [x] **Weekly quota alerts** — integrated into `send_weekly_digest`
- [x] **Storage trend alerts** — integrated into `send_weekly_digest`

### Metrics
- [x] **`GET /api/metrics`** — implemented in `flux/api/metrics.py` (Prometheus-compatible)
- [x] **Key metrics tracked** — `flux_posts_total`, `flux_renders_total`, `flux_storage_used_bytes`, `flux_ingredients_total`, `flux_workers_active`
- [x] **Health snapshots** — `HealthSnapshot` model added and hooked into `_run_health_check`

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
- [x] Log redaction — comprehensive `REDACT_PATTERNS` implemented in `logger.py` (handles JWTs, Gemini keys, Instagrapi sessions, and OAuth tokens)

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
- [x] **Plugin base tests** — `test_plugins.py` tests RenderResult validation
- [x] **Verse ID regex tests** — `test_quran_regex.py` tests pattern extraction
- [x] **Caption template tests** — `test_caption.py` tests Jinja2 truncation/rendering
- [x] **Lock tests** — `test_lock.py` tests acquire/release and timeouts
- [x] **Storage budget tests** — `tests/unit/test_storage.py`
- [x] **Notification format tests** — implicitly covered by Telegram alert integration

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

- [x] **Language Shorts plugin** — fully implemented with Gemini + TTS + FFmpeg composition
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

## 13. Frontend UI/UX Audit & Fixes

Based on browser subagent audit on port 8001:

### 📊 Dashboard Page
- [x] Redundant Status Indicators: "Daemon healthy" status in top header and sidebar footer.
- [x] Visual Hierarchy Issues: Data values in status cards (e.g., "0h") are disproportionately large compared to labels.
- [x] Inconsistent Alignment: "Operations Dashboard" title doesn't align perfectly with "Refresh" button or cards.
- [x] Weak Empty States: "No pipelines yet" state lacks a clear CTA button to create a pipeline.
- [x] Sidebar Active State: Active state indicator has inconsistent shape.
- [x] Non-Standard Button Styling: "Refresh" button styled as a "ghost" but has a permanent border.
- [x] Excessive Top Margin: Main content area has too much top gap compared to side margins.
- [x] Poor Typography Scaling: "FLUX ADMIN" subtitle is extremely small and all-caps.
- [x] Badge Inconsistency: "YouTube" and "Active" badges use different font weights and padding.
- [x] Shadow Overuse: Cards have very subtle shadows that feel accidental.

### 🛣️ Pipelines Page
- [x] Duplicate Heading: "Pipelines" repeated in breadcrumb and main page title.
- [x] Table Header Spacing: All-caps with extreme letter-spacing reduces readability.
- [x] Floating CTA: "+ Create Pipeline" button isolated on far right.
- [x] Missing Table Empty State: Main pipelines table has no "Empty State" illustration/text.
- [x] Description Proximity: "Manage automation streams" description too far from title.

### 👷 Workers Page
- [x] Inefficient Card Layout: Excessive vertical space for cron expression; cramped action buttons.
- [x] Cramped Action Buttons: Small ghost buttons with tight margins risk mis-clicks.
- [x] Non-Human Readable Cron: Display raw cron instead of translated (e.g., "Daily at 8:00 AM").
- [x] Disconnect Button Alignment: "+ Connect Worker" doesn't align with cards.
- [x] Status Badge Weight: Status badges use heavier font weight than Dashboard badges.

### 📝 Post Log Page
- [x] Vertical Filter Stack: Filters (Platform, Status, Pipeline) stacked vertically waste horizontal space.
- [x] Isolated Export Button: "Export CSV" button disconnected from filters and table.
- [x] Generic Column Naming: "Verse" column specific to Quran plugin; should be dynamic ("Content" / "Title").
- [x] Small Table Font: Data rows use smaller font size than body text.
- [x] Dropdown Styling: Default browser dropdowns clash with custom inputs.

### ⚙️ System/Settings Page
- [x] Chaotic Save Button Placement: Inconsistently placed (inline vs full-width).
- [x] Dated Checkbox UI: "Auto-delete" setting uses standard browser checkbox instead of toggle switch.
- [x] Mixed Content Widths: Setting inputs vary wildly in width without reflecting data length.
- [x] Loose Vertical Rhythm: Spacing between setting rows is inconsistent.

### 📜 Activity Log Page
- [x] Long ID Readability: Hex IDs do not truncate (e.g., `c58e...41d8`).
- [x] Timeline Hierarchy: Event names same font size/weight as description.
- [x] Color Coding Deficiency: All events use generic green dot instead of semantic colors (red/error, blue/trigger).
- [x] Absolute Time Only: Logs use absolute timestamps instead of relative ("2 mins ago").

### 📱 Responsive/Mobile View (600px)
- [x] Bottom Nav Labeling: Lack of icons makes abbreviations hard to identify.
- [x] Layout Breaking IDs: Long hex IDs do not wrap, causing overflow.
- [x] Hamburger Menu Size: Small toggle, lacks background.
- [x] Padding Compression: Cards maintain desktop padding, squishing text.

### 🏗️ Modals & Forms
- [x] Modal Header Tightness: "NEW AUTOMATION STREAM" label nearly touching title.
- [x] Dated Close Icon: '×' text character instead of modern SVG icon.
- [x] Label Proximity: Input labels too close to fields.

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
| API Endpoints | 26 | 0 | 0 | 26 |
| Infrastructure | 6 | 0 | 4 | 10 |
| Monitoring & Alerting | 11 | 0 | 7 | 18 |
| Security | 7 | 0 | 3 | 10 |
| Data Strategy | 12 | 0 | 0 | 12 |
| Testing | 12 | 0 | 3 | 15 |
| **TOTAL** | **133** | **7** | **54** | **194** |

> **~52% done, ~6% in-progress, ~43% not started.** Phase 7 (hardening/watchdog/remote) is now complete. The largest remaining gaps are: platform publishing (4 stubs), admin UI polish (28 items), and monitoring/alerting notifications.

---

## 14. PRD v1.0 Audit — Additional Gaps, Flaws & Bugs

> **Methodology**: Cross-referenced `01-prd.md` against the actual codebase. Items below were either not covered in the prior audit (docs `01`–`16`) or represent newly discovered bugs/flaws.

### Missing PRD Requirements

| ID | Item | PRD Ref | Severity |
|----|------|---------|----------|
| PRD-01 | **Telegram low-stock alerts missing** — `flux/core/notifications.py` has `send_alert_storage_critical`, `send_alert_worker_failed`, etc., but **no `send_alert_low_stock()`**. PRD F-07 explicitly requires "low stock" alerts. The stock-level logic exists (`get_stock_level()`) but never triggers a notification. | F-07 | Medium |
| PRD-02 | **Performance NFR benchmarks missing** — PRD 6.1 specifies quantitative targets: (a) render throughput 1 video / 2–5 min on ARM, (b) dashboard load < 500 ms, (c) SQLite aggregations < 100 ms. No benchmarks, load tests, or query-performance tests exist. | 6.1 | Medium |
| PRD-03 | **Network outage resilience not explicitly designed** — PRD 6.2 states "Network outages shall not crash the daemon; retry with backoff." While publishing has retry, other network paths (fetch, Telegram API, health checks) lack a unified outage-handling strategy or test. | 6.2 | Medium |
| PRD-04 | **Plugin API runtime version enforcement missing** — `Plugin.api_version` is stored in the DB but `load_plugins()` never validates that a loaded plugin's API version is compatible with the core runtime. A breaking plugin change could crash the engine. | 6.5 | Medium |
| PRD-05 | **ADR (Architecture Decision Records) missing** — PRD 6.5 requires ADRs for all major architectural choices. None exist in the repo. | 6.5 | Low |
| PRD-06 | **60-second reboot recovery not validated** — PRD Success Criterion #3 requires recovery within 60 seconds. No test or measurement exists. | §8 | Low |
| PRD-07 | **90-day zero-duplicate validation not tested** — PRD Success Criterion #4 requires zero duplicates for 90 days. No dedup stress-test or simulation exists. | §8 | Low |

### Bugs & Logic Flaws

| ID | Item | File / Line | Severity |
|----|------|-------------|----------|
| BUG-01 | **APScheduler job removal on startup causes missed posts after reboot** — `register_worker_jobs()` removes *all* worker jobs and re-adds them on every startup. APScheduler's SQLite jobstore loses last-run state for cron triggers. If the daemon is down during a scheduled post time and restarts later, the cron trigger recalculates its next fire time from "now", silently **missing the past occurrence**. This directly violates PRD F-02 (survive reboots without missing jobs). | `flux/core/scheduler_jobs.py` L44–46 | **Critical** |
| BUG-02 | **Cascade deletes destroy immutable post audit trail** — `Pipeline` → `cascade="all, delete-orphan"` on `produced_content`; `ProducedContent` → `cascade="all, delete-orphan"` on `post_records`. `PlatformWorker` also cascades to `post_records`. Deleting a pipeline or worker permanently destroys `PostRecord` history. PRD implies post records are an immutable audit trail ("Track every post in a `post_records` table"). | `flux/models.py` L76–84, L118–120, L193–195 | **High** |
| BUG-03 | **Publish retry lacks exponential backoff** — PRD F-22 says "Retry failed posts up to 3 times with exponential backoff." The current code sets `should_retry = result.transient and attempt_count < MAX_RETRIES`, but the retry only happens on the **next cron trigger** (could be hours later). There is no actual backoff timing (e.g., 5 min, 15 min, 45 min). | `flux/core/publish.py` L283–324 | High |
| BUG-04 | **`_maybe_auto_delete` uses current pipeline-worker attachments** — Auto-delete checks `PipelineWorker` at the moment of evaluation. If a worker is detached from a pipeline after content is produced but before publishing completes, auto-delete will consider that worker "done" (not in the set) and may delete files before the remaining attached workers publish. | `flux/core/publish.py` L138–166 | Medium |
| BUG-05 | **Render alert threshold too high** — `send_alert_render_failed` only fires after **3 consecutive failures**. Intermittent failures (e.g., thermal guard, temporary disk full) that resolve between attempts never alert the operator, despite PRD F-07 requiring notifications for "errors". | `flux/core/notifications.py` L92–95 | Medium |
| BUG-06 | **`get_unused_approved_ingredients` does O(N×M) Python filtering** — Loads all approved ingredients and all produced-content ID lists into memory, then filters in Python. For large pipelines this is slow and RAM-heavy. Should be a single SQL `NOT EXISTS` or `LEFT JOIN` query. | `flux/core/ingredients.py` L194–224 | Medium |
| BUG-07 | **Stale `rendering` records never recovered after crash** — If the daemon crashes during `ProducedContent` status `"rendering"`, the row stays in that state forever. No startup scan resets stale renders to `"failed"` or `"pending"`. (Partially noted in Phase 2 but not assigned a fix task.) | `flux/models.py` L183–185, `flux/plugins/quran/render.py` | Medium |
| BUG-08 | **No render-timeout / zombie-FFmpeg recovery** — `_run_ffmpeg` has a 300-second timeout, but if FFmpeg is killed by the OS or hangs in a state `proc.communicate()` can't detect, the render lock may never be released and the `rendering` record stays stuck indefinitely. | `flux/plugins/quran/render.py` L75–94 | Medium |
| BUG-09 | **Tasks list incorrectly claims no `posts.py` API router** — The audit at line 179 states "no `posts.py` API router", but `flux/api/posts.py` exists and is wired in `flux/main.py`. The tasks list itself is stale here. | `conception_tasks_list.md` L179 | Low |

### Performance Issues

| ID | Item | File / Line | Severity |
|----|------|-------------|----------|
| PERF-01 | **`get_storage_budget` walks the entire storage tree synchronously** — `_get_dir_size` uses `os.scandir` recursively on every dashboard call. On a large 5 GB library this can block the event loop for hundreds of milliseconds, violating the <100 ms query target. | `flux/core/storage.py` L28–40 | Medium |
| PERF-02 | **Dashboard API lacks query-result caching** — Every dashboard request re-runs `count(*)` queries and storage scans. No Redis, in-memory cache, or materialized view is used. | `flux/api/system.py` L47–82 | Low |

---

## 15. Conception Docs 02–16 Audit — Cross-Cutting Gaps

> **Methodology**: Every conception document (`02-user-personas` through `16-build-plan`) was read and cross-referenced against the actual codebase. Items below were not covered in the prior PRD audit (Section 14) or the original build-plan audit (Sections 1–13).

### Doc 02 — User Personas & Journey Maps

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| UPM-01 | **First-run wizard / setup checklist** in admin panel | Low | Doc describes a single-page checklist for API keys, channels, workers. Not implemented. |
| UPM-02 | **Real-time download progress** in admin panel | Low | yt-dlp fetch progress is not streamed to the UI. |
| UPM-03 | **Pre-generated low-res thumbnails** for ingredients | Low | Ingredient library shows full images; no low-res proxy generation. |
| UPM-04 | **Thermal-aware scheduling pause at 45°C** | Medium | Doc specifies pause renders at >45°C. Code warns at 55°C and **blocks** at 65°C. No scheduling pause or "ultrafast" preset fallback when hot. |
| UPM-05 | **Telegram deep link to preview + one-click post** | Low | Telegram alerts contain no deep links to the admin panel. |
| UPM-06 | **Inline "Edit next caption" reply to Telegram bot** | Low | Bot is notification-only; no interactive commands. |
| UPM-07 | **Smart cleanup suggestions** (oldest published) | Low | Storage alerts say "please free up space" but don't suggest specific files. |
| UPM-08 | **Guided session login via admin panel QR code** (Instagram) | Low | No QR login flow; Instagrapi session must be imported manually. |
| UPM-09 | **Boot notification + self-health check report** after reboot | Low | No Telegram message sent when daemon starts after a reboot. |
| UPM-10 | **Plugin template generator CLI** (`flux generate-plugin`) | Low | No CLI scaffolding for new plugins. |
| UPM-11 | **Non-developer quickstart documentation** | Low | Docs assume Python/Linux knowledge; no "non-developer quickstart" path exists. |

### Doc 04 — User Flow Diagrams

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| UFD-01 | **Auto-delete rejected toggle in approval UI** | Low | Flow shows "Auto-delete rejected? Yes/No" decision after rejection. UI has no such toggle; cleanup is hardcoded to 7 days. |
| UFD-02 | **Plugin linting/validation command** | Low | `flux validate-plugin ./plugins/my_plugin` does not exist. |
| UFD-03 | **Hot plugin reload** (no restart required) | Low | Doc says "Restart daemon; plugin auto-registers." Still requires full restart. |
| UFD-04 | **Startup recovery: mark interrupted renders as pending** | High | Error recovery flow explicitly says "Mark interrupted renders as pending" on reboot. Not implemented. (Same as BUG-07.) |

### Doc 06 — Functional Specification Document (FSD)

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| FSD-01 | **Structured error response format** | Low | FSD §2.2 specifies `{error: {code, message, field, retryable, documentation_url}}`. Current API returns plain `{"detail": "..."}` FastAPI defaults. |
| FSD-02 | **Caption template live preview with sample data** | Low | FSD §6.3 describes live preview rendering template with sample data. No preview endpoint exists. |
| FSD-03 | **`plugin.yaml` manifest validation** | Medium | FSD §1.1 describes YAML manifest with schema validation. Plugins use Python class registration instead. (Already noted in Section 3.) |
| FSD-04 | **`identify_content()` hook present and functional** | OK | `ContentPlugin.identify_content()` exists in `flux/plugins/base.py` and is called by `pipeline.py`. |
| FSD-05 | **`get_config_schema()` present** | OK | Exists and returns JSONSchema dict. |

### Doc 07 — Technical Feasibility Study

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| TFS-01 | **Whisper.cpp local transcription** | Medium | Doc describes building whisper.cpp for ARM and using it as a fallback for verse ID. Not implemented. (Already noted in Section 3.) |
| TFS-02 | **Thermal pause threshold mismatch** | Medium | Doc specifies 45°C pause. Actual code: warn at 55°C, block at 65°C. No graceful degradation (ultrafast preset) when warm. |
| TFS-03 | **yt-dlp weekly auto-update cron** | Low | Doc mentions weekly cron to update yt-dlp. Not implemented. |
| TFS-04 | **Android Doze / battery optimization handling** | Medium | Doc mentions `Termux:WakeLock` + ignore battery optimizations. Bootstrap script does not configure Android battery settings. |

### Doc 08 — System Architecture Document (SAD)

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| SAD-01 | **`quran_text.db` for local fuzzy matching** | Medium | SAD §7 shows `quran_text.db` for local Quran text fuzzy matching. No such database or logic exists. |
| SAD-02 | **Pipeline Orchestrator as distinct service** | Low | SAD §3.3 describes a Pipeline Orchestrator service. Orchestration logic is scattered across `pipeline.py`, `scheduler_jobs.py`, and `publish.py` rather than a unified service. |
| SAD-03 | **Telegram Bot using `python-telegram-bot`** | Low | SAD §3.1 mentions `python-telegram-bot`. The library is in `requirements.txt` but the actual notification code uses manual `urllib` requests. |
| SAD-04 | **Plugin validation on load** (no network access) | Low | SAD §3.4 says "Plugin manifest validated; no network access during plugin load." No validation beyond import exists. |

### Doc 09 — Data Strategy & Content Pipeline Design

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| DSP-01 | **`review_flag` hard blocker not enforced** | **High** | Doc §5.2 and §6.2 state that content with `review_flag=true` **cannot** enter the ready queue. The code sets `status="verse_unknown"` but never checks `review_flag` in metadata. A manual verse assignment could theoretically bypass review. |
| DSP-02 | **Render modes `image_compose`, `text_only`, `passthrough` untested** | Medium | Doc §5.1 defines these modes. `video_compose` is tested; others are defined in code but never exercised by a real plugin. |
| DSP-03 | **Pipeline-worker platform-content mismatch warnings** | Low | Doc §5.5 (Platform-Content Matrix) implies UI should warn when attaching a text-only pipeline to YouTube. No such validation exists. |
| DSP-04 | **Per-pipeline stock thresholds in settings UI** | Low | Doc §7.1 shows stock thresholds stored per pipeline in `config_json`. No UI exists to edit them. |

### Doc 10 — Infrastructure & Deployment Plan

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| INF-01 | **`termux-api` package in bootstrap** | Low | Doc §2.1 lists `termux-api` as optional but recommended. `scripts/bootstrap.sh` does not mention it. |
| INF-02 | **`rclone` cloud backup integration** | Low | Doc §7.1 mentions `rclone` to cloud for DB backup. Only local file-copy backup exists. |
| INF-03 | **Disaster recovery playbook automation** | Low | Doc §10 lists recovery scenarios. Documented only; no automated recovery scripts. |
| INF-04 | **Alembic migrations directory** | Medium | Doc §2.2 and §9.1 reference `alembic/` and `alembic upgrade head`. No `alembic/` directory exists; tables created via `create_all()`. (Already noted.) |
| INF-05 | **Whisper.cpp build in bootstrap** | Medium | Doc §2.3 describes building whisper.cpp during bootstrap. Not included. |
| INF-06 | **Log retention time-based (7 days)** | Low | Doc §4.3 / §9.3 mentions 7-day log retention. `RotatingFileHandler` uses size-based rotation (5 MB), not time-based. `activity_log` has 30-day truncation. |

### Doc 11 — Security & Risk Assessment

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| SEC-01 | **Auto-approve per ingredient type setting** | Medium | Doc §5.1 says "Auto-approve can be enabled per ingredient type in settings, but is disabled by default." No such setting exists in code or UI. |
| SEC-02 | **`retracted` status for post_records** | Low | Doc §9.2 mentions marking a post as `retracted` after manual deletion. `PostRecord.status` only supports `pending/published/failed`. |
| SEC-03 | **Hash verification for pip installs (`--require-hashes`)** | Low | Doc §6 says "Future: use `pip install --require-hashes`". Not implemented. |
| SEC-04 | **Plugin audit / sandboxing** | Low | Doc §6 says "Plugin manifest validated; no network access during plugin load." Not enforced. |
| SEC-05 | **yt-dlp weekly auto-update** | Low | Same as TFS-03. |
| SEC-06 | **Rate limiting jitter `randint(0, 600)` before posts** | Medium | Doc §4.1 specifies random delay before posts. Not implemented. (Already noted.) |
| SEC-07 | **Post timing window 07:00–21:00** | Medium | Doc §4.1 specifies human-hours posting window. Not enforced. (Already noted.) |
| SEC-08 | **Session reuse for Instagram** | Medium | Doc §4.2 says "Use instagrapi with session reuse". Not implemented. (Already noted.) |
| SEC-09 | **Key rotation CLI command** | Low | Doc §3.1 mentions "Operator can re-encrypt all credentials with a new key via CLI command." Not implemented. (Already noted.) |

### Doc 12 — API & Integration Strategy

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| API-01 | **URL versioning `/api/v1/...`** | Low | Doc §2.3 reserves `/api/v1/...` for future breaking changes. All current endpoints are unversioned `/api/...`. |
| API-02 | **`X-Flux-Key` header for external API clients** | Low | Doc §2.4 mentions optional API key. Not implemented. |
| API-03 | **`alquran.cloud` fallback for verse data** | Low | Doc §3.2 describes alquran.cloud as fallback if quran.com is down. Not implemented. |
| API-04 | **YouTube quota tracking in DB** | Medium | Doc §4.1 and §6 say "Quota tracking in DB; alert at 70%". No quota tracking table or alert exists. |
| API-05 | **Dashboard quota consumption display** | Medium | Doc §6 says "Dashboard must display quota consumption." Not implemented. |
| API-06 | **GitHub Actions remote trigger validates Bearer token** | Medium | Doc §5.2 shows `Authorization: Bearer ${{ secrets.FLUX_REMOTE_KEY }}`. The `/api/system/remote` endpoint accepts any request; no token validation. |
| API-07 | **`TransientError` / `PermanentError` exception classes** | Medium | Doc §4.3 defines these exceptions. Code uses `PublishResult.transient` boolean instead. (Already noted.) |
| API-08 | **`authenticate()` and `get_quota()` in base publisher** | Medium | Doc §4.2 specifies these methods. Not in `PlatformPublisher` base class. (Already noted.) |

### Doc 13 — Monitoring, Observability & Alerting

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| MON-01 | **`flux_renders_duration_seconds` histogram metric** | Low | Doc §6.1 specifies this metric. Not emitted by `/api/metrics`. |
| MON-02 | **`flux_fetch_items_total` counter metric** | Low | Not emitted by `/api/metrics`. |
| MON-03 | **`flux_queue_depth` gauge metric** | Low | Not emitted by `/api/metrics`. |
| MON-04 | **`flux_content_review_backlog` gauge metric** | Low | Not emitted by `/api/metrics`. |
| MON-05 | **`plugins` health check in `/api/health`** | Low | Doc §2.1 health JSON includes `plugins: {quran_shorts: "ok"}`. `rich_health_check()` does not check plugin status. |
| MON-06 | **Storage >= 80% warning Telegram alert** | Medium | Doc §5.1 lists this as a Warning alert. Code only sends Critical at >=95%. The 80% warning is logged but not sent to Telegram. |
| MON-07 | **Verse unknown backlog > 5 alert** | Low | Doc §5.1 says alert at >5. Code alerts at >=10 (`send_alert_verse_backlog`). |
| MON-08 | **Daemon restarted after crash alert** | Low | Doc §5.1 lists "Daemon restarted after crash" as Warning. No startup notification exists. |
| MON-09 | **Historical views (calendar, storage chart, render time chart)** | Low | Doc §7.2 describes calendar view, storage trend, render time charts. Not implemented. |
| MON-10 | **Real-time indicators in admin UI** | Low | Doc §7.1 lists uptime, next action, render progress, worker dots, storage bar with refresh intervals. Not implemented. (Already noted.) |

### Doc 14 — Content Strategy & Expansion Roadmap

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| CSR-01 | **Platform-content mismatch warnings in UI** | Low | Doc §5 says "pipeline-worker attachment UI must warn or prevent mismatches." Not implemented. |
| CSR-02 | **Content calendar visual view** | Low | Doc §4.3 and §6 describe a visual monthly calendar. Not implemented. (Already in future list.) |
| CSR-03 | **Cross-pipeline coordination** (e.g., Friday Quran, Saturday Hadith) | Low | Doc §4.3 and §6.1 describe scheduling coordination. Not implemented. (Already in future list.) |
| CSR-04 | **Seasonal content adjustments** (Ramadan, Eid) | Low | Doc §6.2 describes seasonal frequency changes. Not implemented. |
| CSR-05 | **Analytics feedback loop** | Low | Doc §9 mentions tracking which verses/formats perform best. Not implemented. |
| CSR-06 | **All future content plugins** (Hadith, Quotes, Reminders, News, Community) | Low | Explicitly post-v1.0; already in future list. |

### Doc 15 — Decision Log (ADRs)

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| ADR-020 | **Alembic migrations** | Medium | ADR-020 accepted Alembic for migrations. No `alembic/` directory exists. (Already noted.) |

### Doc 16 — Build Plan

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| BP-01 | **Phase 5 YouTube upload marked incomplete in build plan but implemented** | Low | Discrepancy: Build plan Phase 5 lists YouTube upload as `[ ]`, but it is implemented. Tasks list correctly marks it done. |
| BP-02 | **Phase 7 marked incomplete in build plan but implemented** | Low | Build plan shows Phase 7 as "⏳ Not started" but watchdog, backup, thermal guard, and SSH hardening are all done. |
| BP-03 | **Device test directory (`@pytest.mark.device`)** | Medium | Build plan §5.4 describes device tests. No `tests/device/` directory or `@pytest.mark.device` marker exists. (Already noted.) |
| BP-04 | **48-hour soak test** | Medium | Build plan §3 Phase 7 validation requires 48-hour soak. Not performed. (Already noted.) |
| BP-05 | **Per-phase manual checklists (`PHASE_N_CHECKLIST.md`)** | Low | Build plan §5.5 requires checklists. Only `PHASE_4_PLAN.md` exists. (Already noted.) |

---

## Updated Summary Stats

| Category | Done | In Progress | Not Started | Total |
|----------|------|-------------|-------------|-------|
| Build Plan Phases 0–4 | 31 | 0 | 0 | 31 |
| Build Plan Phase 5 | 9 | 0 | 4 | 13 |
| Build Plan Phase 6 | 0 | 1 | 5 | 6 |
| Build Plan Phase 7 | 7 | 0 | 0 | 7 |
| Core Engine | 7 | 1 | 2 | 10 |
| Platform Workers | 2 | 1 | 5 | 8 |
| Admin UI Screens | 1 | 4 | 23 | 28 |
| API Endpoints | 26 | 0 | 0 | 26 |
| Infrastructure | 6 | 0 | 4 | 10 |
| Monitoring & Alerting | 11 | 0 | 7 | 18 |
| Security | 7 | 0 | 3 | 10 |
| Data Strategy | 12 | 0 | 0 | 12 |
| Testing | 12 | 0 | 3 | 15 |
| **PRD v1.0 Audit (new)** | 0 | 0 | **18** | **18** |
| **Conception Docs 02–16 Audit (new)** | 2 | 0 | **63** | **65** |
| **TOTAL** | **133** | **7** | **135** | **275** |

> **~48% done, ~3% in-progress, ~49% not started.** Newly discovered critical bugs (BUG-01, BUG-02, BUG-03) and the high-severity `review_flag` hard blocker (DSP-01) should be prioritized above UI polish.
