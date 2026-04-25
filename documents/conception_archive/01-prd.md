# Flux — Product Requirements Document

## Metadata
| Field | Value |
|-------|-------|
| **Document** | PRD v1.0 |
| **Product** | Flux |
| **Status** | Conception — Ready for architecture |
| **Tagline** | The idle automator. One post per day, perfectly timed, fully hands-off. |
| **Runtime Target** | Debian (Termux) on Android phone |
| **Core Language** | Python 3.11 |
| **Database** | SQLite |

---

## 1. Vision & Elevator Pitch

Flux is a **content automation engine** designed to run quietly on an old Android phone, producing and publishing social media posts with zero daily intervention. The name reflects the system's nature: it is idle most of the time, flowing into brief periods of focused activity.

The first **automation pipeline** (v1) produces Quran short-form videos. Future pipelines will handle other content types — motivational clips, news summaries, curated image carousels — each running as an independent, pluggable module.

> **Core philosophy:** Build the automation framework once. Add content types as plugins. Never rebuild the engine.

---

## 2. Problem Statement

1. **Maintaining a social presence is relentless.** Posting daily requires creativity, time, and consistency.
2. **Old phones are landfill.** An idle Android device has compute, storage, and network — enough to run a 24/7 automation daemon.
3. **Existing tools are cloud-centric or expensive.** SaaS schedulers (Buffer, Hootsuite) charge monthly and lack deep content generation. Self-hosted alternatives assume a VPS or Docker host.
4. **Content creation is repetitive.** Quran videos follow the same pattern every time: source clip + background + caption + publish. This repetition is ideal for automation.
5. **Future expansion must not require rewrites.** The user already knows more content types are coming. The architecture must anticipate this.

---

## 3. Objectives

### Business Objectives
- Run a 24/7 automation daemon on a $0-cost device (old phone).
- Reduce operator touch-time to < 5 minutes per week after initial setup.
- Maintain a consistent daily posting schedule across multiple platforms.
- Provide a foundation for rapid addition of new content pipelines without touching core infrastructure.

### Technical Objectives
- Zero external server dependencies (no cloud VPS, no managed database).
- Survive phone reboots, process kills, and network outages without data loss or duplicate posts.
- All state persisted in SQLite; all configuration in version-controlled files or the same DB.
- Remote manageability via SSH (Tailscale) and a web-based admin panel accessed through SSH port-forwarding.
- GitHub Actions watchdog (30-min schedule, within free tier) provides external heartbeat monitoring and remote trigger capability; requires Cloudflare Tunnel or router port forwarding for phone reachability.

### Content Objectives
- Quran pipeline (v1): 1 post/day to 2+ platforms.
- Each post is unique (no duplicates per platform).
- All religious content is accurate (correct verse identification is non-negotiable).
- Content requires explicit operator approval before entering production.

---

## 4. Target Audience / Operator Profile

Flux is operated by a **single technical owner** (the builder). There are no "end users" in the traditional consumer sense — the operator is both user and administrator.

- **Tech-savviness:** Comfortable with Linux, SSH, Python, and APIs.
- **Time constraints:** Wants a "set and forget" system that runs for months.
- **Values:** Privacy (no cloud), frugality (use existing hardware), expandability.
- **Risk tolerance:** Accepts that unofficial APIs (Instagram, TikTok) carry ban risk; mitigates via careful rate-limiting.

> **Design implication:** The UI is an admin panel, not a consumer app. Power-user features are exposed directly. No onboarding wizard — the operator edits config files or uses precise admin controls.

---

## 5. Functional Requirements

### 5.1 Core Automation Engine
| ID | Requirement | Priority |
|----|-------------|----------|
| F-01 | The system shall run as a persistent daemon on Debian/Termux. | P0 |
| F-02 | The system shall survive reboots and resume all scheduled jobs without duplication. | P0 |
| F-03 | The system shall support multiple independent **automation pipelines**. | P0 |
| F-04 | Each pipeline shall be associated with exactly one **content type plugin**. | P0 |
| F-05 | Each pipeline shall publish to one or more **platform workers** (social accounts). | P0 |
| F-06 | The system shall expose a web admin panel on `127.0.0.1:8000/admin`; accessed via SSH port-forward on LAN or Tailscale remotely. | P0 |
| F-07 | The system shall send Telegram notifications for critical events (errors, low stock, storage alerts). | P1 |

### 5.2 Content Pipeline — Quran (v1 Plugin)
| ID | Requirement | Priority |
|----|-------------|----------|
| F-10 | Automatically monitor and download Quran short clips from whitelisted YouTube channels. | P0 |
| F-11 | All downloaded clips enter a **pending approval** state; never used until approved. | P0 |
| F-12 | Automatically fetch background images/videos from Pexels/Unsplash using safe keyword lists. | P0 |
| F-13 | Compose rendered videos: keyed Quran text overlay + background + timing set. | P0 |
| F-14 | Identify the Quranic verse reference via 3-tier fallback: metadata → Whisper → manual. | P0 |
| F-15 | Fetch Arabic text, translation, and tafseer from quran.com API. | P0 |
| F-16 | Generate per-platform captions via a template engine. | P0 |
| F-17 | Extract thumbnail from rendered video. | P0 |
| F-18 | Queue fully packaged videos for publishing. | P0 |

### 5.3 Publishing
| ID | Requirement | Priority |
|----|-------------|----------|
| F-20 | Support manual "post now" and scheduled (cron-based) triggers per platform worker. | P0 |
| F-21 | Track every post in a `post_records` table; prevent duplicate publishing of the same video to the same platform. | P0 |
| F-22 | Retry failed posts up to 3 times with exponential backoff. | P0 |
| F-23 | Support platform workers: YouTube, Telegram, Instagram, TikTok, X/Twitter. | P0 |
| F-23a | **Note:** Browser automation (Selenium) is not viable on Termux. TikTok and X rely on unofficial APIs or manual fallback. | P0 |
| F-24 | Allow multiple accounts per platform (e.g., 2 YouTube channels). | P1 |
| F-25 | Auto-delete local video files after successful publish to all configured platforms (configurable). | P1 |

### 5.4 Admin Panel
| ID | Requirement | Priority |
|----|-------------|----------|
| F-30 | Dashboard: stock levels, pending approvals, queue status, storage usage, next post times. | P0 |
| F-31 | Pipeline management: enable/disable pipelines, view plugin status. | P0 |
| F-32 | Ingredient library browser with approve/reject/preview/delete. | P0 |
| F-33 | Production history: filter by status, manual verse assignment, re-queue. | P0 |
| F-34 | Platform worker config: add/remove accounts, set schedules, caption overrides. | P0 |
| F-35 | Global settings: thresholds, storage budget, trusted sources, caption templates. | P0 |
| F-36 | Activity log: last 200 events with timestamps. | P1 |

### 5.5 Future Content Pipelines (Non-Quran)
| ID | Requirement | Priority |
|----|-------------|----------|
| F-40 | The plugin interface shall support arbitrary content types without core changes. | P1 |
| F-41 | A new pipeline shall be creatable by: installing a plugin, configuring sources, assigning workers. | P1 |
| F-42 | Ingredients shall be typed per content plugin; the library shall be namespace-isolated. | P1 |
| F-43 | Each plugin shall define its own render pipeline (or skip rendering if not video). | P1 |

---

## 6. Non-Functional Requirements

### 6.1 Performance
- Render throughput: 1 video per 2–5 minutes on a mid-range ARM phone (acceptable).
- Admin panel load time: < 500ms on LAN.
- SQLite queries: < 100ms for all dashboard aggregations.

### 6.2 Reliability
- No duplicate posts, ever. Database-level uniqueness constraints + idempotency keys.
- Render jobs resume after interruption (status tracking in DB).
- Network outages shall not crash the daemon; retry with backoff.

### 6.3 Security
- Admin panel bound to `127.0.0.1` only; no auth required. LAN access via SSH port-forward. Remote access via Tailscale + SSH port-forward.
- All platform credentials encrypted at rest (Fernet/AES via a master key in environment).
- SSH key-based access only; no password login.
- No inbound ports exposed beyond LAN (except reverse-SSH tunnel if used).

### 6.4 Resource Constraints
- Storage budget: configurable (default 5 GB for all pipelines combined).
- CPU: single FFmpeg process at a time to prevent thermal throttling.
- RAM: SQLite + FastAPI + APScheduler must run within 1–2 GB available on old phones.

### 6.5 Maintainability
- All config in files or DB; no hardcoded values.
- Plugin API versioned (v1); breaking changes bump API version.
- Decision records (ADRs) kept for all major architectural choices.

---

## 7. Out of Scope (for v1.0)

The following are explicitly deferred to keep v1 focused:

- Multi-user admin panel / RBAC.
- Cloud deployment option (Docker/VPS).
- Analytics/engagement tracking beyond basic post success/failure.
- AI-generated content (images, video, text).
- Real-time collaboration.
- Mobile app (the admin panel is web-based).
- Automated comment/reply management.

---

## 8. Success Criteria

1. Quran pipeline runs unattended for 30 days with zero manual intervention beyond initial approvals.
2. Operator can add a second content pipeline (e.g., "Daily Motivation") by writing/ installing a plugin and editing config — without modifying core code.
3. System recovers from phone reboot within 60 seconds and resumes all schedules.
4. Zero duplicate posts across all platforms for the first 90 days.
5. Storage usage stays within configured budget without manual cleanup.
