# Flux — Technical Feasibility Study

This document assesses whether the proposed architecture can be built and run within the target environment: a Debian system inside Termux on an old Android phone.

---

## 1. Environment Profile: Termux on Android

### 1.1 Typical Hardware (2019–2021 Mid-Range Phone)

| Resource | Typical Spec | Flux Requirement | Verdict |
|----------|--------------|------------------|---------|
| CPU | ARM octa-core 2.0 GHz | FFmpeg encoding, Python async | Sufficient |
| RAM | 4–6 GB | SQLite + FastAPI + APScheduler + 1 FFmpeg | Tight but viable |
| Storage | 64–128 GB internal | 5 GB budget for app + media | Comfortable |
| Network | Wi-Fi 5 / 4G | API calls, uploads, SSH | Sufficient |
| Battery | 4,000–5,000 mAh | 24/7 daemon + overnight renders | Needs charging strategy |

### 1.2 Termux Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| No systemd / no real `cron` | Cannot use system cron | APScheduler with SQLite job store handles all scheduling |
| Android Doze / app killing | Termux process may be killed | Termux:WakeLock + Termux:Boot + ignore battery optimizations |
| No root required (preferred) | Cannot bind port < 1024 | Use port 8000+ |
| Filesystem access via `/storage/emulated/0` | Media stored on shared storage | All media paths use external storage; DB on internal |
| No Docker | Cannot containerize | Run directly in Python venv |
| Package repository limited | Some libs need compilation | Prefer pure-Python or wheels with ARM builds |

---

## 2. Component Feasibility Matrix

### 2.1 Core Stack

| Component | Choice | Feasibility | Notes |
|-----------|--------|-------------|-------|
| **Python 3.11** | Termux `pkg install python` | **High** | Available, no compilation needed |
| **FastAPI + Uvicorn** | `pip install fastapi uvicorn[standard]` | **High** | Lightweight, async, works on ARM |
| **SQLite** | Python stdlib `sqlite3` | **High** | Zero setup, survives reboots |
| **SQLAlchemy 2.0** | `pip install sqlalchemy` | **High** | ORM + Alembic for migrations |
| **APScheduler** | `pip install apscheduler` | **High** | SQLite job store tested on ARM |
| **Jinja2** | `pip install Jinja2` | **High** | Templating engine for captions |
| **Pydantic** | `pip install pydantic` | **High** | Settings validation, API models |

### 2.2 Media Processing

| Component | Choice | Feasibility | Notes |
|-----------|--------|-------------|-------|
| **FFmpeg** | Termux `pkg install ffmpeg` | **High** | Termux package is well-maintained; H.264 encoding works |
| **FFmpeg colorkey** | Built-in filter | **High** | Deterministic black-screen removal; no ML |
| **FFmpeg zoompan** | Built-in filter | **High** | Ken Burns effect via filtergraph |
| **yt-dlp** | Termux `pkg install yt-dlp` | **High** | Actively maintained; bypasses YouTube changes quickly |
| **whisper.cpp** | Compile from source | **Medium** | ARM build available; tiny model ~75 MB; transcription ~1× real-time on ARM |
| **Pillow** | `pip install Pillow` | **High** | Image manipulation for thumbnails if needed |

### 2.3 External APIs

| API | Purpose | Limits | Feasibility |
|-----|---------|--------|-------------|
| **quran.com API v4** | Verse text, translations | No key, generous | **High** |
| **alquran.cloud** | Fallback verse data | Free, no auth | **High** |
| **Pexels API** | Background images/videos | 200 req/hr | **High** |
| **Unsplash API** | Backup images | 50 req/hr | **High** |
| **YouTube Data API v3** | Uploads | 10,000 units/day | **High** (2 channels × 1/day = ~3,200 units) |
| **Telegram Bot API** | Channel posting | Effectively unlimited | **High** |

### 2.4 Social Media Posting

| Platform | Method | Risk | Feasibility |
|----------|--------|------|-------------|
| **YouTube** | Official Data API v3 | Low (official) | **High** |
| **Telegram** | Official Bot API | Low (official) | **High** |
| **Instagram** | `instagrapi` (unofficial) | Medium (ban possible) | **Medium** — requires careful rate limiting, session management |
| **TikTok** | `TikTokApi` (unofficial) | Medium (ban possible) | **Medium** — Limited automation; no browser fallback on Termux |
| **X / Twitter** | API v2 free tier | Medium | **Medium** — free tier limits; text-only fallback if media upload fails |

**Mitigation for unofficial methods:**
- Post at human-plausible hours (not 03:47).
- Random delays 30–120s between actions.
- One session per account; no parallel logins.
- Keep frequency <= 1/day per account.
- Store session cookies; reuse rather than re-login.
- **No Selenium fallback on Termux** — Chrome/Chromium is not available in Termux. Browser automation is not viable on this platform.

---

## 3. Risky Assumptions & Validation

### Assumption 1: "An old phone can run FFmpeg 24/7 without dying."
- **Validation:** FFmpeg encoding is CPU-intensive and generates heat.
- **Mitigation:** Single encode at a time. Thermal throttling is handled by Android kernel; we add software pause at 45°C. Overnight encoding while charging and phone is stationary.
- **Fallback:** If phone overheats consistently, reduce output resolution to 720p or use `-preset ultrafast`.

### Assumption 2: "APScheduler SQLite job store survives Termux restarts cleanly."
- **Validation:** APScheduler persists job metadata in SQLite. If the process is killed mid-job, the job may be marked "executing."
- **Mitigation:** On daemon startup, scan for jobs stuck in "executing" > 1 hour and reset to "pending." Use `misfire_grace_time` of 1 hour for non-critical jobs.

### Assumption 3: "Instagrapi will continue working on Termux."
- **Validation:** Unofficial libraries break when platforms update. Instagrapi is community-maintained.
- **Mitigation:** Pin to a known-good version. Maintain a fallback: if Instagrapi fails, log the error and queue for manual retry. Monitor Instagrapi GitHub for breaking changes.
- **Fallback:** Instagram can be deferred to manual posting if automation breaks; the pipeline still produces the video.

### Assumption 4: "GitHub Actions can act as a reliable watchdog."
- **Validation:** GitHub Actions free tier: 2,000 minutes/month. A 15-second workflow every 30 minutes = ~48 runs/day × 30 × 0.25 min = **~360 minutes/month** — well within free tier.
- **Requirement:** The phone must be reachable from the public internet. Options: (1) Cloudflare Tunnel (free, stable URL, no open ports), (2) Router port forwarding + DDNS, (3) ngrok (free, URL changes on restart).
- **Plan:** Use GitHub Actions on a 30-minute schedule to `curl` the phone's public URL (`/api/health`). On failure, send Telegram alert. Also provide `workflow_dispatch` for manual remote commands.

### Assumption 5: "Reverse SSH / DDNS provides stable remote access."
- **Validation:** Home routers may change IP; NAT can be tricky; mobile data IPs are dynamic.
- **Mitigation:** Use Tailscale (free for personal use, WireGuard-based mesh) or ngrok (free tier with random URLs). Tailscale is preferred — it creates a stable virtual IP for the phone regardless of network.
- **Fallback:** GitHub Actions can send a webhook to trigger a cloud function that emails the current IP (if DDNS is used).

---

## 4. Performance Benchmarks (Expected)

| Task | Expected Time on Mid-Range ARM | Notes |
|------|-------------------------------|-------|
| Download 1 Quran clip (yt-dlp) | 10–30s | Depends on video length and bandwidth |
| Download 10 background images | 5–15s | Small files, parallel fetch |
| Render 60s video (H.264 medium) | 3–5 minutes | CPU-bound; varies by preset |
| Extract thumbnail (FFmpeg) | < 2s | Fast seek + frame grab |
| Whisper transcription (tiny model, 60s) | 30–60s | On-device, no network |
| YouTube upload (60s video) | 30–120s | Network-bound |
| Telegram post | < 5s | Fast API |
| Instagram post (Instagrapi) | 15–60s | Includes upload + processing wait |
| TikTok post (unofficial API) | 30–120s | Upload via mobile API endpoints |
| Dashboard page load | < 500ms | SQLite queries + static files |

---

## 5. Build vs. Buy Decisions

| Capability | Build | Buy/Use Existing | Rationale |
|------------|-------|------------------|-----------|
| Video rendering | — | **FFmpeg** | Mature, handles all requirements |
| Video downloading | — | **yt-dlp** | Industry standard; impossible to replicate |
| Scheduling | — | **APScheduler** | Perfect for single-node deployment |
| Database | — | **SQLite** | Zero admin overhead |
| Web framework | — | **FastAPI** | Modern, async, auto-docs |
| Admin UI | Build vanilla HTML + Alpine.js | — | No build step, lightweight |
| Auth / user management | **Defer** | — | Single operator; localhost-only for v1 |
| Cloud watchdog | — | **GitHub Actions** + **Cloudflare Tunnel** | Free, fulfills user requirement, stable URL |
| Reverse SSH | **Build script** | — | Simple bash script + Tailscale is better |
| Caption templates | **Build** | — | Domain-specific logic |
| Content plugins | **Build framework** | — | Core differentiator |

---

## 6. Go / No-Go Verdict

| Area | Verdict |
|------|---------|
| Core stack on Termux | **GO** — All components install and run on ARM |
| Video pipeline | **GO** — FFmpeg proven on Termux; performance acceptable |
| Social posting (YouTube + Telegram) | **GO** — Official APIs, reliable |
| Social posting (Instagram + TikTok + X) | **GO with caution** — Unofficial methods carry risk; acceptable for v1 with mitigations |
| Remote management | **GO** — Tailscale + SSH solves this elegantly |
| Watchdog / monitoring | **GO** — GitHub Actions on 30-min schedule (360 min/month) within free tier; requires Cloudflare Tunnel or port forwarding for reachability |
| Plugin architecture | **GO** — Python import system + abstract base classes are standard patterns |
| Multi-pipeline future | **GO** — Data model already isolates pipelines |

**Overall:** The project is technically feasible. The primary risks are thermal management during renders and reliance on unofficial APIs for some platforms. Both have clear mitigations.
