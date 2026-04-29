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
| **Gemini AI API** | `google-generativeai` | **High** | Offloads identification logic to cloud; efficient for verse ID |
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
| **Gemini API** | Verse identification | Free tier available | **High** |

### 2.4 Social Media Posting

| Platform | Method | Risk | Feasibility |
|----------|--------|------|-------------|
| **YouTube** | Official Data API v3 | Low (official) | **High** |
| **Telegram** | Official Bot API | Low (official) | **High** |
| **Instagram** | `instagrapi` (unofficial) | Medium (ban possible) | **Medium** — requires careful rate limiting, session management |
| **TikTok** | `TikTokApi` (unofficial) | Medium (ban possible) | **Medium** — Limited automation; no browser fallback on Termux |
| **X / Twitter** | API v2 free tier | Medium | **Medium** — free tier limits; text-only fallback if media upload fails |

---

## 3. Risky Assumptions & Validation

### Assumption 1: "An old phone can run FFmpeg 24/7 without dying."
- **Validation:** FFmpeg encoding is CPU-intensive and generates heat.
- **Mitigation:** Single encode at a time. Thermal throttling is handled by Android kernel; we add software pause at 45°C. Overnight encoding while charging and phone is stationary.

### Assumption 2: "Gemini API can accurately identify verses from video/audio."
- **Validation:** Gemini Pro Vision / Gemini 1.5 Flash support video/audio input.
- **Mitigation:** Provide clear system instructions and few-shot examples. Fallback to metadata regex first. Manual review for low-confidence matches.

### Assumption 3: "Instagrapi will continue working on Termux."
- **Validation:** Unofficial libraries break when platforms update. Instagrapi is community-maintained.
- **Mitigation:** Pin to a known-good version. Maintain a fallback: if Instagrapi fails, log the error and queue for manual retry.

### Assumption 4: "GitHub Actions can act as a reliable watchdog."
- **Validation:** GitHub Actions free tier: 2,000 minutes/month. 
- **Plan:** Use GitHub Actions on a 30-minute schedule to `curl` the phone's public URL (`/api/health`).

---

## 4. Performance Benchmarks (Expected)

| Task | Expected Time on Mid-Range ARM | Notes |
|------|-------------------------------|-------|
| Download 1 Quran clip (yt-dlp) | 10–30s | Depends on video length and bandwidth |
| Download 10 background images | 5–15s | Small files, parallel fetch |
| Render 60s video (H.264 medium) | 3–5 minutes | CPU-bound; varies by preset |
| Extract thumbnail (FFmpeg) | < 2s | Fast seek + frame grab |
| Gemini AI identification | 5–15s | Network-bound; cloud processing |
| YouTube upload (60s video) | 30–120s | Network-bound |
| Telegram post | < 5s | Fast API |

... rest of document ...
