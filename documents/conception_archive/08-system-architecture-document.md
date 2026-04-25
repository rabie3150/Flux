# Flux — System Architecture Document (SAD)

## 1. Architectural Drivers

1. **Single-node deployment** — Everything runs on one Android phone.
2. **Plugin extensibility** — New content types must not require core changes.
3. **Account multiplicity** — Multiple accounts per platform, multiple pipelines per account.
4. **Resilience** — Survive reboots, process kills, network outages without duplicate posts.
5. **Zero cloud dependency** — No VPS, no managed DB, no SaaS required (optional watchdog excepted).

---

## 2. High-Level Architecture

```
+-------------------------+
|       OPERATOR          |
|  (Laptop / Browser)     |
+-----------+-------------+
            | LAN / Tailscale
+-----------v-------------+
|     Termux / Debian     |
|  +-------------------+  |
|  |   FastAPI Server  |  |
|  |   (Uvicorn)       |  |
|  |   :8000           |  |
|  +---------+---------+  |
|            |            |
|  +---------v---------+  |
|  |   APScheduler     |  |
|  |   (SQLite store)  |  |
|  +---------+---------+  |
|            |            |
|  +---------v---------+  |
|  |   Plugin Engine   |  |
|  |  +-------------+  |  |
|  |  | Quran Plugin |  |  |
|  |  | (v1)         |  |  |
|  |  +-------------+  |  |
|  |  | Future: ...  |  |  |
|  |  +-------------+  |  |
|  +---------+---------+  |
|            |            |
|  +---------v---------+  |
|  |   Platform Workers |  |
|  |  +------+------+  |  |
|  |  | YT   | IG   |  |  |
|  |  | TG   | TT   |  |  |
|  |  | X    | ...  |  |  |
|  |  +------+------+  |  |
|  +---------+---------+  |
|            |            |
|  +---------v---------+  |
|  |   SQLite DB       |  |
|  |   (app.db, WAL)   |  |
|  +---------+---------+  |
|            |            |
|  +---------v---------+  |
|  |   Media Storage   |  |
|  | /storage/emul/0/  |  |
|  |   /Flux/          |  |
|  +-------------------+  |
+-------------------------+
            |
            | Internet
+-----------v-------------+
|  APIs: YouTube, Pexels, |
|  Telegram, Quran APIs   |
+-------------------------+
```

---

## 3. Layered Architecture

### 3.1 Presentation Layer
- **Admin Panel:** Vanilla HTML + Alpine.js, served as static files by FastAPI.
- **Telegram Bot:** Async bot (python-telegram-bot) for notifications and quick commands.
- **SSH CLI:** Operator can SSH in and use management commands directly.

### 3.2 API Layer
- **FastAPI Routers:** `/api/system`, `/api/pipelines`, `/api/workers`, `/api/posts`
- **Middleware:** Request logging, error handling. CORS unnecessary (admin panel on localhost).
- **Static Files:** `/admin/*` serves the UI.

### 3.3 Service Layer (Core Engine)
- **Pipeline Orchestrator:** Manages pipeline lifecycle, routes jobs to plugins.
- **Job Scheduler:** APScheduler triggers fetch, render, publish, cleanup jobs.
- **Lock Manager:** File-based or SQLite-based distributed locks (single node, but prevents race conditions).
- **Storage Manager:** Tracks file sizes, enforces budgets, handles cleanup.
- **Notification Service:** Sends Telegram alerts; extensible to other channels.

### 3.4 Plugin Layer
- **Plugin Loader:** Scans `./plugins/`, validates manifests, imports modules.
- **Plugin Registry:** In-memory mapping of `plugin_id -> ContentPlugin instance`.
- **Plugin Instances:** Quran plugin (v1). Future plugins implement the same interface.

### 3.5 Integration Layer
- **Platform Worker Factory:** `PlatformWorker.create(platform)` returns the correct implementation.
- **API Clients:** YouTube Data API, Telegram Bot API, Pexels, Unsplash, quran.com.
- **HTTP Clients:** `httpx` for all API calls; no browser automation on Termux.

### 3.6 Data Layer
- **SQLite:** Single-file database (`app.db`).
- **Media Files:** Organized directory tree on external storage.
- **Config:** `.env` file for secrets; `settings` table for runtime config.

---

## 4. Component Diagram (Detailed)

```
+---------------------------------------------------------------+
|                         FLUX CORE                              |
+---------------------------------------------------------------+
|                                                                |
|  +----------------+  +----------------+  +------------------+  |
|  |  Web Router    |  |  Scheduler     |  |  Plugin Loader   |  |
|  |  (FastAPI)     |  |  (APScheduler) |  |  (Dynamic Import)|  |
|  +--------+-------+  +--------+-------+  +--------+---------+  |
|           |                   |                   |            |
|  +--------v-------+  +--------v-------+  +--------v---------+  |
|  |  Admin Panel   |  |  Job Queue     |  |  Plugin Registry |  |
|  |  (Alpine.js)   |  |  (SQLite)      |  |  (In-Memory)     |  |
|  +----------------+  +--------+-------+  +--------+---------+  |
|                               |                   |            |
|  +----------------+  +--------v-------+  +--------v---------+  |
|  |  Telegram Bot  |  |  Lock Manager  |  |  Quran Plugin    |  |
|  |  (Notifier)    |  |  (File/SQLite) |  |  (Fetch/Render)  |  |
|  +----------------+  +--------+-------+  +--------+---------+  |
|                               |                   |            |
|  +----------------+  +--------v-------+  +--------v---------+  |
|  |  Storage Mgr   |  |  Worker Mgr    |  |  Future Plugins  |  |
|  |  (Budget/FS)   |  |  (Post/Retry)  |  |  (Hadith, etc.)  |  |
|  +--------+-------+  +--------+-------+  +------------------+  |
|           |                   |                                |
+-----------|-------------------|--------------------------------+
            |                   |
+-----------v-------------------v--------------------------------+
|                         DATA & FILES                           |
|  +----------------+  +----------------+  +------------------+  |
|  |  SQLite DB     |  |  Media Storage |  |  Config (.env)   |  |
|  |  (app.db)      |  |  (/Flux/...)   |  |  (secrets)       |  |
|  +----------------+  +----------------+  +------------------+  |
+----------------------------------------------------------------+
```

---

## 5. Key Architectural Patterns

### 5.1 Plugin Architecture
- **Strategy Pattern:** Each content type is a strategy for fetch/render/caption.
- **Registry Pattern:** Plugins self-register via manifest; core engine dispatches by `plugin_id`.
- **Template Method:** The pipeline orchestrator defines the skeleton (fetch → approve → render → identify → caption → publish); plugins implement the variable steps.

### 5.2 Worker Architecture
- **Adapter Pattern:** Each platform is an adapter implementing `PlatformWorker` interface.
- **Command Pattern:** Publishing a video encapsulates the request as a command object stored in `post_records`.

### 5.3 Resilience Patterns
- **Circuit Breaker:** If a worker fails 3 consecutive posts, it is paused (circuit opens). Admin must manually reset.
- **Retry with Backoff:** Transient failures retry at 60s, 120s, 240s.
- **Idempotency:** Composite unique key `(produced_content_id, worker_id)` prevents double-posting.
- **Graceful Degradation:** If a platform worker fails, other platforms still post. If rendering fails, publishing continues for already-ready videos.

---

## 6. Data Flow Diagrams

### 6.1 Fetch Flow

```
APScheduler ──trigger──> PipelineOrchestrator
                              │
                              ▼
                        Plugin.fetch()
                              │
                              ▼
                    +-------------------+
                    |  yt-dlp           |
                    |  Pexels API       |
                    |  Unsplash API     |
                    |  quran.com API    |
                    +-------------------+
                              │
                              ▼
                        ingredients table (status=pending)
                              │
                              ▼
                    Telegram notification to admin
```

### 6.2 Render Flow

```
APScheduler ──trigger──> PipelineOrchestrator
                              │
                              ▼
                    Select approved ingredients
                              │
                              ▼
                        Plugin.render()
                              │
                              ├──> FFmpeg colorkey
                              ├──> FFmpeg overlay/scale
                              └──> FFmpeg encode
                              │
                              ▼
                    produced_content table (status=rendered)
                              │
                              ▼
                    Plugin.identify_content()
                              │
                    +---------+---------+
                    |                   |
                    ▼                   ▼
              Verse known         Verse unknown
                    |                   |
                    ▼                   ▼
              status=ready      status=rendered (with meta flag: needs_review)
                    |           (notify admin)
                    ▼
            Plugin.build_caption()
                    │
                    ▼
              Queue for publish
```

### 6.3 Publish Flow

```
APScheduler ──trigger──> WorkerManager
                              │
                              ▼
                    Select next ready video
                    (not yet posted to this worker)
                              │
                              ▼
                    PlatformWorker.post()
                              │
                    +---------+---------+
                    |                   |
                    ▼                   ▼
                 Success            Failure
                    |                   |
                    ▼                   ▼
            post_records          Retry 3×
            status=published            |
                    |                   ▼
                    ▼              Still failed
            Auto-delete?                |
                    |                   ▼
              +-----+-----+      Worker paused
              |           |      Admin notified
              ▼           ▼
          Yes delete    Keep file
```

---

## 7. Deployment View

```
Android Phone
├── Termux (Debian environment)
│   ├── ~/flux/                      ← Application code
│   │   ├── main.py                  ← FastAPI entrypoint
│   │   ├── plugins/
│   │   │   └── quran_shorts/        ← Quran plugin
│   │   ├── static/admin/            ← Alpine.js UI
│   │   ├── requirements.txt
│   │   └── .env                     ← Secrets
│   │
│   ├── app.db                       ← SQLite database
│   ├── quran_text.db                ← Local Quran text for fuzzy matching
│   └── venv/                        ← Python virtual environment
│
└── /storage/emulated/0/Flux/        ← External media storage
    ├── library/
    │   ├── quran_clips/             ← Downloaded clips
    │   ├── backgrounds/
    │   │   ├── images/
    │   │   └── videos/
    │   └── production/              ← Rendered videos
    ├── thumbnails/
    └── logs/

Remote Services
├── GitHub Actions                   ← Watchdog (30-min curl) + remote triggers
├── Cloudflare Tunnel / DDNS         ← Public reachability for GH Actions
├── Tailscale                        ← Mesh VPN for remote SSH
└── Telegram Bot API                 ← Notifications
```

---

## 8. Technology Constraints & Assumptions

1. **Single SQLite file (WAL mode enabled):** No read replicas, no horizontal scaling. WAL allows concurrent reads during writes. Acceptable for single-operator, single-node system.
2. **Python import system for plugins:** Plugins must be valid Python packages. Sandboxing is limited — plugins run with full process privileges. Only install trusted plugins.
3. **No real-time requirements:** All jobs are batch/asynchronous. WebSocket not needed.
4. **Storage is finite:** Architecture must aggressively clean up and track usage.
5. **Network is intermittent:** All external calls must have timeouts and retry logic.
