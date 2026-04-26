# Flux — Build Plan: From Zero to Autonomous Pipeline

## 1. Development Philosophy

### 1.1 Vertical Slice > Backend-First
**Do not build the entire backend, then the entire frontend.** This app has too many unknowns (FFmpeg on ARM, YouTube API quotas, Instagrapi session persistence). A backend-only "completion" is useless if the phone cannot render a video or post to YouTube.

**Rule:** Every phase must produce a **working, testable slice** that touches database → API → minimal UI → real hardware.

### 1.2 Risk-Driven Order
Build the **highest-risk components first.** If they fail, we fail fast and cheap.

| Risk Rank | Component | Why It's High Risk |
|-----------|-----------|-------------------|
| 1 | FFmpeg render pipeline (colorkey, overlay, encode) | ARM performance, thermal throttling, filtergraph complexity |
| 2 | yt-dlp fetch + YouTube Data API upload | yt-dlp breaks when YouTube changes; API quota is finite |
| 3 | Instagrapi session persistence | Unofficial; sessions expire; ban risk |
| 4 | Whisper.cpp on Termux | Compilation issues, model size, accuracy on phone audio |
| 5 | Plugin loader / dynamic imports | Python import edge cases, namespace collisions |
| 6 | Admin UI (Alpine.js) | Lowest risk; pure frontend logic |

### 1.3 Device-First Validation
**Every phase ends with a Termux validation.** Code that works on a laptop may fail on an old ARM phone. No phase is "done" until it runs on the target device.

### 1.4 Plugin-First Architecture
The Quran pipeline is the **reference implementation** of the plugin interface. Do not build a generic engine in a vacuum. Build the engine **while** building the Quran plugin so the interface is validated by real use.

---

## 2. Environment & Tooling

### 2.1 Development Machine (Laptop)
- Python 3.11+, venv, VS Code
- SQLite (same version as Termux)
- FFmpeg (same major version as Termux)
- `pytest`, `httpx`, `pytest-asyncio`
- Git with conventional commits

**Where to develop?**

| Environment | When to Use | Limitations |
|-------------|-------------|-------------|
| **Windows (direct)** ⭐ Primary | Phases 0–4 (foundation → core → fetch → render → distribute) | `termux-wake-lock`, `termux-boot`, Android storage paths don't work. Use Windows paths for dev. |
| **WSL** | If you prefer Linux/Unix tooling | Behaves like Termux; good for bash script testing. Not required. |
| **Termux (phone)** | Phase 5+ integration, device tests, ARM validation | Slower iteration; use only for final validation and soak tests. |

**Phase-by-phase dev environment:**

| Phase | Windows Dev? | Phone Needed? |
|-------|-------------|---------------|
| 0 Foundation | ✅ Yes | ❌ No |
| 1 Core Engine | ✅ Yes | ❌ No |
| 2 Fetch (APIs) | ✅ Yes | ❌ No |
| 3 Render (FFmpeg) | ✅ Yes (test filtergraphs) | ⚠️ Final ARM performance test |
| 4 Distribute (APIs) | ✅ Yes | ⚠️ Final Instagrapi/YouTube test |
| 5 Scheduler | ✅ Yes | ⚠️ Doze mode test only |
| 6 Integration | ⚠️ Simulate | ✅ Yes (full pipeline on device) |
| 7 Hardening | ⚠️ Simulate | ✅ Yes (48-hour soak test) |

> **Rule:** Develop on Windows (or WSL). The phone is for *validation*, not daily iteration.

### 2.2 Test Device (Phone)
- Termux from F-Droid
- Dedicated test Telegram channel
- Test YouTube channel (private/unlisted)
- Test Instagram account (burner)

### 2.3 Git Repository Structure (Monorepo)
```
flux/
├── .github/
│   └── workflows/
│       ├── watchdog.yml          # Phase 7
│       └── remote-command.yml    # Phase 7
├── scripts/
│   ├── bootstrap.sh              # Phase 0
│   └── start.sh                  # Phase 0
├── flux/
│   ├── __init__.py
│   ├── main.py                   # FastAPI entrypoint
│   ├── config.py                 # Pydantic settings
│   ├── db.py                     # SQLAlchemy engine + session
│   ├── scheduler.py              # APScheduler setup
│   ├── lock.py                   # File-based render lock
│   ├── storage.py                # Storage budget tracker
│   ├── notifications.py          # Telegram bot
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py               # ContentPlugin ABC
│   │   └── quran/
│   │       ├── __init__.py
│   │       ├── plugin.py         # Quran plugin impl
│   │       ├── fetch.py          # yt-dlp, Pexels, Unsplash
│   │       ├── render.py         # FFmpeg filtergraph
│   │       ├── identify.py       # Verse ID logic
│   │       └── caption.py        # Jinja2 templates
│   ├── core/
│   │   ├── pipeline.py           # Pipeline orchestrator
│   │   ├── ingredients.py        # Ingredient service
│   │   ├── production.py         # Render queue service
│   │   └── workers.py            # Platform worker manager
│   ├── api/
│   │   ├── __init__.py
│   │   ├── system.py             # Health, settings, activity
│   │   ├── pipelines.py
│   │   ├── ingredients.py
│   │   ├── production.py
│   │   ├── workers.py
│   │   └── posts.py
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── base.py               # PlatformWorker ABC
│   │   ├── youtube.py
│   │   ├── telegram.py
│   │   ├── instagram.py
│   │   ├── tiktok.py
│   │   └── x.py
│   └── static/
│       └── admin/                # HTML + Alpine.js
├── tests/
│   ├── unit/                     # Pure logic, no I/O
│   ├── integration/              # DB + API client
│   └── device/                   # Run on Termux only
├── alembic/
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── pyproject.toml
```

---

## 3. Phase Breakdown

### Phase 0: Foundation Spike (Week 1)
**Goal:** Prove the app can start on Termux and FFmpeg can run.

| Task | Definition of Done |
|------|-------------------|
| Project skeleton [x] | `main.py` runs; FastAPI serves `/api/health` |
| Bootstrap script [x] | One-command install works on clean Termux |
| SQLite + WAL [x] | `PRAGMA journal_mode=WAL` returns `wal` |
| Plugin loader [x] | Scans `./plugins/`, loads a dummy plugin, exposes `name` |
| FFmpeg spike [x] | A 5-second test video renders on the phone in < 30s |
| Start script [x] | `start.sh` survives `pkill` and auto-restarts |

**Validation:** SSH into phone, run bootstrap, hit `/api/health`, verify FFmpeg produces `test_output.mp4`.

**Status:** ✅ Complete — validated on Galaxy S21 Termux.

**Git commits:**
- `98c238e` feat: phase 0 — project skeleton, health endpoint, bootstrap, skills, audit

---

### Phase 1: Core Engine (Week 2)
**Goal:** Pipeline lifecycle, ingredient storage, minimal API, minimal UI.

| Task | Definition of Done |
|------|-------------------|
| Database schema [x] | All core tables created via Alembic; foreign keys enforced |
| Pipeline CRUD [x] | Create, read, update, delete, enable/disable pipelines via API |
| Ingredient service [x] | Insert, list, filter, approve, reject ingredients |
| APScheduler [x] | Jobs persist in SQLite; survive daemon restart; no duplication |
| File lock [x] | Two concurrent render attempts → one succeeds, one skips |
| Minimal admin UI [x] | Plain HTML forms; no Alpine.js yet. Server-rendered tables. |
| Settings [x] | `.env` loaded; secrets not in git; master key encrypts test creds |

**Validation:** Create a Quran pipeline via UI. Upload a test ingredient file manually. Approve it. Verify DB state.

**Status:** ✅ Complete — 25 tests passing after Hawk Eye review audit.

**Git commits:**
- `b3f49cd` feat: phase 1 — core engine, database models, API CRUD, scheduler, render lock, logging system, minimal admin UI
- `e3ad578` fix(review): hawk-eye audit fixes for Phase 0/1

---

### Phase 2: Quran Plugin — Fetch (Week 3)
**Goal:** Automated downloading of clips and backgrounds with approval gates.

| Task | Definition of Done |
|------|-------------------|
| yt-dlp fetch [x] | Downloads 5 Shorts from whitelisted channel; metadata saved |
| Pexels fetch [x] | Downloads 10 images with safe keywords; blocklist enforced |
| Unsplash fallback [x] | Downloads images if Pexels rate-limited |
| Approval gate [x] | All downloads land in `pending`; bulk approve/reject works |
| Stock monitoring [x] | Fetch triggers when approved count < min threshold |
| Telegram notify [ ] | Bot sends "5 clips pending approval" with deep link — **moved to Phase 5** |

**Validation:** Trigger fetch. Open admin panel. Approve 3 clips. Verify stock count updates.

**Status:** ✅ Complete — validated on device. 4 clips + 4 ingredients created successfully from `@Am9li9/shorts`.

**Git commits:**
- `b881c1a` feat(phase-2): quran plugin fetch — yt-dlp, pexels, unsplash, trigger endpoint
- `3215b6e` test(phase-2): quran fetch trigger integration tests + bugfix
- `ea754ca` chore(config): add default quran source channel @Am9li9/shorts
- `bbdc167` fix(core): auto-sync plugins to database on startup
- `1b36eed` fix(phase-2): review fixes — deep merge, blocklist enforcement, exception specificity, error isolation

**Note:** Blocklist filtering and 429 rate-limit detection added in review fix commit `1b36eed`.

---

### Phase 3: Render Pipeline (Week 4)
**Goal:** Compose a finished video from approved ingredients. **This is the riskiest phase.**

| Task | Definition of Done |
|------|-------------------|
| Colorkey filter [ ] | Black background removed; white text is transparent |
| Overlay [ ] | Quran clip composited over background at 1080×1920 |
| Image slideshow [ ] | N images cycle with timing set; Ken Burns optional |
| Video background [ ] | Background video loops, muted, trimmed to match Quran duration |
| Thumbnail [ ] | Frame extracted at 2s into rendered video |
| Render queue [/] | DB schema + lock mechanism exist; render orchestration stub only |
| Render preview [ ] | Admin panel streams rendered MP4 via API endpoint |

**Validation:** Select 1 approved clip + 3 approved images. Click "Render." Video plays correctly on phone. Duration matches source. Thumbnail is clear.

**Status:** 🔄 **Current focus** — Render method is stub (`return RenderResult(...)`). Full implementation pending.

**Git commit (planned):** `feat: render pipeline — ffmpeg colorkey, overlay, slideshow, thumbnails`

---

### Phase 4: Content ID & Captions (Week 5)
**Goal:** Identify verse, fetch translations, build captions.

| Task | Definition of Done |
|------|-------------------|
| Metadata regex | 90%+ of test clips correctly extract surah:ayah from title |
| Whisper fallback | Transcribes audio; fuzzy-matches against local Quran text |
| Manual assignment | Admin can assign verse via UI; video moves to `ready` |
| quran.com API | Fetches Arabic + translation + tafseer; cached in SQLite |
| Caption template | Jinja2 renders verse_ref + arabic + translation + hashtags |
| Platform overrides | YouTube gets full caption; X gets truncated version |

**Validation:** Render 5 videos. 4 identified via metadata. 1 triggers Whisper. 1 fails both → admin assigns manually. All captions render correctly per platform.

**Git commit:** `feat: verse identification, translation fetch, caption engine`

---

### Phase 5: Platform Workers & Publishing (Week 6)
**Goal:** Post content to social platforms. **Second riskiest phase.**

| Task | Definition of Done |
|------|-------------------|
| YouTube upload | Video + thumbnail + caption posted via Data API v3 |
| Telegram post | Video + caption posted to channel via Bot API |
| Instagram post | Video posted via Instagrapi; session reused; no re-login storm |
| Deduplication | Same video cannot be posted twice to same platform (DB constraint) |
| Retry logic | Transient failures retry 3×; permanent failures pause worker |
| Post log | Every attempt recorded with platform_post_id, URL, error_log |
| Auto-delete | Local MP4 deleted after all platforms succeed (configurable) |

**Validation:** Queue 1 ready video. It posts to YouTube + Telegram. Check YouTube Studio for unlisted video. Check Telegram channel. Verify post_records has 2 entries.

**Git commit:** `feat: platform workers — youtube, telegram, instagram, dedup, retry`

---

### Phase 6: Admin Panel Polish (Week 7)
**Goal:** Operator can manage everything without SSH.

| Task | Definition of Done |
|------|-------------------|
| Alpine.js UI [ ] | Replace server-rendered forms with reactive components |
| Dashboard [/] | `/api/pipelines/{id}/stats` endpoint exists; no visual bars yet |
| Real-time [ ] | Render progress polls API every 10s; post status updates live |
| Pipeline config [ ] | Form generated from plugin `config_schema` (not raw JSON) |
| Worker config [ ] | Cron builder, caption override, hashtag editor, test button |
| Mobile layout [ ] | Collapses to single column; touch-friendly |

**Validation:** Operator performs full setup (add channel, approve clips, add worker, trigger post) entirely from phone browser without SSH.

**Git commit:** `feat: alpine.js admin panel — dashboard, real-time updates, mobile layout`

---

### Phase 7: Watchdog, Remote Access & Hardening (Week 8)
**Goal:** System runs 24/7 unattended. Operator can fix issues from anywhere.

| Task | Definition of Done |
|------|-------------------|
| Cloudflare Tunnel | `cloudflared` runs on boot; exposes `/api/health` to public URL |
| GitHub Actions watchdog | 30-min schedule; sends Telegram alert on 2 consecutive failures |
| Remote restart | `workflow_dispatch` triggers safe daemon restart |
| Backup cron | Daily DB backup to external storage; 7-day rotation |
| SSH hardening | Key-only auth; port 8022; no password |
| Log rotation | 5MB rotation; 5 backups; redacted credentials |
| Thermal guard | Render pauses if phone > 45°C; resumes when cool |

**Validation:** Unplug phone from charger. Let it run for 48 hours. Verify GitHub Actions shows all green. Post 2 videos autonomously. Reboot phone remotely via GitHub Actions. Verify daemon restarts and schedules resume.

**Git commit:** `feat: watchdog, remote access, backups, thermal guard, hardening`

---

## 4. Actual Progress Tracker

| Phase | Status | Tests | Device Validated | Key Commits |
|-------|--------|-------|------------------|-------------|
| 0 Foundation | ✅ Complete | — | ✅ Yes | `98c238e` |
| 1 Core Engine | ✅ Complete | 25 passing | ✅ Yes | `b3f49cd`, `e3ad578` |
| 2 Quran Fetch | ✅ Complete | 58 passing (incl. 4 integration) | ✅ Yes | `b881c1a` → `1b36eed` |
| 3 Render | 🔄 In Progress | — | ❌ No | — |
| 4 Content ID | ⏳ Not started | — | ❌ No | — |
| 5 Platform Workers | ⏳ Not started | — | ❌ No | — |
| 6 Admin Panel | ⏳ Not started | — | ❌ No | — |
| 7 Hardening | ⏳ Not started | — | ❌ No | — |

> **Current test count:** 58 tests passing (25 unit/integration from Phase 0–1 + 4 Quran fetch integration tests + 29 existing integration tests).

---

## 5. Testing Strategy

### 5.1 Test Pyramid

```
          /\
         /  \
   Device /    \  Slow; on real phone; validates ARM/Termux reality
  Tests  /______\
        /        \
  Integration /          \  Medium; SQLite + FastAPI client; no real network
    Tests    /____________\
             /              \
       Unit /                \  Fast; pure Python; runs on laptop in < 2s
       Tests/__________________\
```

### 5.2 Unit Tests (70% of test suite)
Run on laptop. No I/O.

| Module | What to Test |
|--------|-------------|
| `plugins/base.py` | RenderResult validation, hook signatures |
| `plugins/quran/identify.py` | Regex patterns against sample titles, fuzzy match scoring |
| `plugins/quran/caption.py` | Jinja2 template rendering, truncation logic |
| `core/lock.py` | File lock acquire/release, timeout behavior, concurrency |
| `storage.py` | Budget calculation, cleanup suggestions |
| `notifications.py` | Message formatting, redaction |

### 5.3 Integration Tests (25% of test suite)
Run on laptop. SQLite in-memory or temp file. FastAPI `TestClient`.

| Flow | What to Test |
|------|-------------|
| Pipeline CRUD | Create → update → delete → verify cascade |
| Ingredient lifecycle | Fetch → pending → approve → render → ready |
| Render queue | Lock prevents concurrent renders; status transitions correct |
| Post dedup | Attempt double-post → 409 or skipped |
| Settings | Update threshold → fetch triggers or pauses |

### 5.4 Device Tests (5% of test suite — but highest value)
Run **only on Termux.** Marked with `@pytest.mark.device`.

| Test | Why It Must Run on Device |
|------|--------------------------|
| FFmpeg render | ARM encode speed, thermal behavior, filtergraph correctness |
| yt-dlp fetch | YouTube may block non-residential IPs; ARM binary compatibility |
| Whisper.cpp | Model load time, transcription accuracy on phone speaker |
| Instagrapi login | Session file paths, Android file permissions |
| YouTube upload | Quota consumption, OAuth refresh token on ARM |
| 48-hour soak | Memory leaks, scheduler drift, Android Doze behavior |

### 5.5 Manual Test Checklist (Per Phase)
Each phase ships with a `PHASE_N_CHECKLIST.md`:

```markdown
## Phase 3 Checklist
- [ ] Fetch 10 clips from test channel
- [ ] Approve 5, reject 2, leave 3 pending
- [ ] Fetch 20 backgrounds
- [ ] Verify storage usage matches file sizes
- [ ] Render 1 video with image slideshow
- [ ] Render 1 video with video background
- [ ] Verify both are 1080×1920, 30fps, H.264
- [ ] Verify thumbnails are 1280×720 JPEG
- [ ] Confirm render lock: start 2 renders simultaneously → 1 queues
- [ ] Phone temperature stays < 50°C during render
```

---

## 6. Git Strategy

### 6.1 Branching Model

```
main
├── phase/0-foundation
├── phase/1-core-engine
├── phase/2-quran-fetch
├── phase/3-render-pipeline
├── phase/4-content-id
├── phase/5-platform-workers
├── phase/6-admin-ui
└── phase/7-watchdog
```

- **`main`** is always deployable to Termux.
- **Phase branches** live until validated on device, then squash-merged to `main`.
- **Hotfixes** branch from `main`, merge back immediately.
- **No long-lived feature branches.** If a phase takes > 2 weeks, split it.

### 6.2 Commit Convention

```
feat: add ffmpeg colorkey filter for black background removal
fix: prevent duplicate renders when APScheduler misfires
test: add device test for youtube upload quota tracking
docs: update bootstrap script for termux-api dependency
refactor: extract render lock into context manager
chore: bump yt-dlp to 2024.04.x
```

**Rule:** Every commit must pass `pytest tests/unit/` on the author's laptop.

### 6.3 Merge Criteria (Definition of Done)

Before any phase branch merges to `main`:

1. [ ] All unit tests pass.
2. [ ] All integration tests pass.
3. [ ] Device tests pass on target phone.
4. [ ] Admin panel is usable for that phase's features (even if ugly).
5. [ ] `bootstrap.sh` can install from a clean Termux state.
6. [ ] No `print()` statements; only structured logging.
7. [ ] `.env.example` updated if new secrets required.
8. [ ] Conception docs updated if architecture changed.

### 6.4 Release Tags

Tag `main` after each phase merge:

```
v0.1.0-phase0   # Foundation
v0.2.0-phase1   # Core Engine
...
v0.8.0-phase7   # Watchdog + Hardening
v1.0.0          # First autonomous 30-day run complete
```

---

## 7. Risk Mitigation per Phase

| Phase | Risk | Mitigation |
|-------|------|------------|
| 0 | FFmpeg won't compile/run on ARM | Spike first. If it fails, project stops here. |
| 0 | Bootstrap script fails on clean Termux | Test on wiped Termux data monthly. |
| 1 | APScheduler loses jobs on reboot | Add startup recovery job. Test by killing process mid-render. |
| 2 | yt-dlp broken by YouTube change | Pin version; weekly update cron; fetch failure alerts admin. |
| 2 | Pexels returns inappropriate images | Strict blocklist + manual approval gate. Never auto-approve. |
| 3 | Phone overheats during render | Thermal sensor check before render; `ultrafast` preset fallback. |
| 3 | FFmpeg filtergraph produces garbled output | Render a test video after every filter change. Visual inspection. |
| 4 | Whisper.cpp accuracy too low | Keep metadata regex as primary; Whisper is fallback only. |
| 5 | YouTube API quota exhausted | Track units per upload; alert at 70%; hard stop at 95%. |
| 5 | Instagram account banned | Use burner account for testing; warm up with manual posts first. |
| 6 | Alpine.js too complex for phone browser | Keep UI server-rendered where possible; Alpine only for reactive widgets. |
| 7 | Cloudflare Tunnel stops | GitHub Actions watchdog detects it; operator SSHs via Tailscale to restart. |

---

## 8. Post-v1.0 Expansion Order

After the Quran pipeline runs autonomously for 30 days:

1. **Hadith image plugin** — Tests `image_compose` render mode; no FFmpeg.
2. **Multi-pipeline coordination** — Two pipelines sharing one worker; queue fairness.
3. **Best-time-to-post** — Pull YouTube analytics; adjust cron per worker.
4. **Plugin marketplace** — Git-based plugin install from admin panel.
5. **Meta Graph API** — Facebook/Instagram official API if available.

---

## 9. Summary: Why This Order?

| Approach | Why Rejected | Our Approach |
|----------|-------------|--------------|
| **Backend-first** | You build 80% of the code before discovering FFmpeg doesn't work on the phone. | **Vertical slice** — validate the riskiest layer (render) in Week 1. |
| **Frontend-first** | Beautiful UI for a pipeline that cannot produce videos. | **Minimal UI first** — plain HTML until Phase 6. Functional > pretty. |
| **Big-bang integration** | Everything hooks together at the end; debugging is impossible. | **Slice-by-slice** — each phase is a working app. |
| **Mock-heavy testing** | Mocks hide the fact that YouTube API rejects your OAuth flow. | **Real APIs + device tests** — mocks only for unit tests. |
| **Commit everything to main** | Broken code reaches the phone; hard to bisect failures. | **Phase branches** — `main` is always stable. |

**The golden rule:** If it doesn't render, fetch, and post on the phone, it doesn't merge to `main`.
