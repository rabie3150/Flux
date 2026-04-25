# Flux — Information Architecture & Sitemap

## 1. Design Principle

Flux is a **single-page admin application** served by FastAPI. The information architecture is organized around **pipelines** (content flows) and **platforms** (destination accounts), with shared global resources (library, settings, logs).

> **Rule:** Every screen must answer "What pipeline? What platform?" within 2 seconds of looking.

---

## 2. Top-Level Hierarchy

```
Flux Admin Panel (/
├── Dashboard                          ← Landing screen. Global health overview.
│
├── Pipelines                          ← The heart of the app.
│   ├── Pipeline List                  ← All pipelines, status cards.
│   └── Pipeline Detail / Config       ← Per-pipeline: sources, schedule, ingredients, renders.
│       └── [Quran v1]                 ← First plugin instance.
│           ├── Ingredient Library     ← Clips, backgrounds, pending/approved.
│           ├── Production Queue       ← Rendered / ready / published / failed.
│           └── Render Preview         ← Watch rendered video before publish.
│
├── Platform Workers                   ← Where content goes.
│   ├── Worker List                    ← All connected accounts.
│   └── Worker Detail / Config         ← Schedule, credentials, caption override, logs.
│
├── Posts                              ← Historical record.
│   ├── Post Log                       ← Every post ever attempted.
│   └── Post Detail                    ← Platform URL, caption, errors.
│
├── System                             ← Global controls.
│   ├── Settings                       ← Storage, thresholds, templates, sources.
│   ├── Plugin Manager                 ← Installed plugins, enable/disable, version.
│   ├── Activity Log                   ← System events (last 500).
│   └── Health & Diagnostics           ← Storage, CPU, queues, heartbeat.
│
└── Help & Docs                        ← Embedded markdown docs.
```

---

## 3. Screen-by-Screen Content Inventory

### 3.1 Dashboard (`/admin`)
**Purpose:** At-a-glance system health. Operator lands here.

| Section | Content | Data Source |
|---------|---------|-------------|
| Status Bar | Daemon uptime, next scheduled action, GitHub Actions watchdog last ping | System metrics |
| Pipeline Cards | One card per pipeline: name, plugin type, status (active/paused/error), items in queue, last run | `pipelines` + `production_queue` |
| Platform Cards | One card per worker: platform icon, account name, last post time, next scheduled post, error flag | `platform_workers` + `post_records` |
| Stock Levels | Horizontal bars per ingredient category (across all pipelines) | `ingredients` aggregation |
| Storage Meter | Used / Budget GB, colour-coded (green < 60%, amber < 80%, red >= 80%) | File system + `settings` |
| Recent Activity | Last 10 events with icons (fetch, render, post success, post fail, approval) | `activity_log` |
| Alerts Banner | Critical alerts requiring action (storage full, worker error, content review backlog) | Derived from system state |

### 3.2 Pipeline List (`/admin/pipelines`)
**Purpose:** Manage automation pipelines.

| Section | Content |
|---------|---------|
| Pipeline Grid | Card per pipeline: name, plugin badge, schedule summary, worker count, queue depth |
| Add Pipeline | Button → modal with plugin selector (only Quran available in v1) |
| Pipeline Actions | Pause / resume / delete (delete warns about data loss) |

### 3.3 Pipeline Detail — Quran (`/admin/pipelines/{id}`)
**Purpose:** Operate a specific pipeline end-to-end.

**Tabs:**
1. **Overview** — Pipeline status, recent renders, quick stats (approved clips count, renders this week).
2. **Ingredients** — Library browser (see 3.4).
3. **Production** — Queue browser (see 3.5).
4. **Settings** — Pipeline-specific config: source channels, keyword lists, timing sets, render preset.

### 3.4 Ingredient Library (`/admin/pipelines/{id}/ingredients`)
**Purpose:** Browse, approve, and manage raw content.

| Filter | Values |
|--------|--------|
| Type | Quran clip / Background image / Background video |
| Status | All / Pending / Approved / Rejected |
| Source | Channel name / API source |

| Bulk Actions | Approve selected, Reject selected, Delete selected |
| Item Card | Thumbnail/preview, title, duration, file size, source URL, status badge, action buttons |

### 3.5 Production Queue (`/admin/pipelines/{id}/production`)
**Purpose:** Track videos from render to publish.

| Status Filter | Description |
|---------------|-------------|
| Rendering | FFmpeg currently working on it |
| Rendered | Video file exists, awaiting verse ID / caption |
| Ready | Fully packaged, in publishing queue |
| Published | Already posted to all assigned workers |
| Failed | Render error or post error |
| Verse Unknown | Stalled at verse identification |

| Columns | Video thumbnail, verse reference, BG mode, timing set, created, status, actions |
| Actions | Preview, Assign verse, Re-queue for platform, Delete |

### 3.6 Platform Workers (`/admin/workers`)
**Purpose:** Manage destination accounts.

| Section | Content |
|---------|---------|
| Worker Grid | Platform icon, display name, associated pipelines, schedule, status dot |
| Add Worker | Form: platform selector → platform-specific credential fields |
| Worker Detail | Schedule (cron builder), caption template override, hashtag list, associated pipelines, manual "Post Now" button |

### 3.7 Post Log (`/admin/posts`)
**Purpose:** Audit trail of everything published.

| Filters | Platform, Pipeline, Date range, Status |
| Columns | Thumbnail, verse ref (or content title), platform, account, posted at, status, URL |
| Detail View | Full caption sent, error log if failed, retry history |

### 3.8 System Settings (`/admin/system/settings`)
**Purpose:** Global configuration.

| Tab | Settings |
|-----|----------|
| General | Storage budget, auto-delete policy, timezone, notification chat ID |
| Library | Default min/max stock thresholds per ingredient type, fetch concurrency |
| Sources | Trusted YouTube channels, Pexels/Unsplash API keys, safe keyword lists, blocklists |
| Captions | Global template builder (reorderable components via arrows or SortableJS), default hashtag pools |
| Timing | Timing set editor (add/edit/delete sets) |
| Security | Master encryption key rotation, SSH tunnel config, LAN allowlist |

### 3.9 Plugin Manager (`/admin/system/plugins`)
**Purpose:** Discover and manage content plugins.

| Section | Content |
|---------|---------|
| Installed | Plugin name, version, API version, author, description, enabled toggle |
| Available | List of community plugins (future: fetched from registry) |
| Upload | Install from local ZIP or Git URL |

---

## 4. Data Relationships (Conceptual)

```
┌─────────────┐       ┌─────────────┐       ┌─────────────────┐
│   Plugin    │◄──────│  Pipeline   │──────►│ Platform Worker │
│  (Quran)    │       │  (Quran     │       │  (YouTube Ch1)  │
│  (Hadith)   │       │   Daily)    │       │  (Telegram)     │
└─────────────┘       └──────┬──────┘       └─────────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │  Ingredient │
                      │   Library   │
                      └──────┬──────┘
                             │
                             ▼
                      ┌─────────────┐
                      │   Render    │
                      │   Engine    │
                      └──────┬──────┘
                             │
                             ▼
                      ┌─────────────┐
                      │  Production │
                      │    Queue    │
                      └──────┬──────┘
                             │
                             ▼
                      ┌─────────────┐
                      │  Post Log   │
                      └─────────────┘
```

**Rule:** A platform worker can be attached to multiple pipelines. A pipeline can publish to multiple workers. This many-to-many relationship is what makes Flux expandable.

---

## 5. Navigation Patterns

| Pattern | Usage |
|---------|-------|
| **Sidebar** | Persistent left nav: Dashboard, Pipelines, Workers, Posts, System. |
| **Breadcrumbs** | Pipeline Detail → Production Queue → Video Preview |
| **Contextual Tabs** | Pipeline Detail uses tabs (Overview / Ingredients / Production / Settings). |
| **Quick Actions** | Dashboard cards have "View all" and primary action (e.g., "Approve pending"). |
| **Command Palette** | Future: `Ctrl+K` to jump to any video, worker, or setting. |

---

## 6. URL Structure (RESTful)

```
GET  /admin                      → Dashboard (served by FastAPI static mount)
GET  /admin/pipelines            → Pipeline list
GET  /admin/pipelines/{id}       → Pipeline detail
GET  /admin/pipelines/{id}/ingredients
GET  /admin/pipelines/{id}/production
GET  /admin/workers              → Worker list
GET  /admin/workers/{id}         → Worker detail
GET  /admin/posts                → Post log
GET  /admin/posts/{id}           → Post detail
GET  /admin/system/settings      → Settings
GET  /admin/system/plugins       → Plugin manager
GET  /admin/system/health        → Diagnostics
```
