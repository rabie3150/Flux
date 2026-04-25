# Flux — Decision Log (Architecture Decision Records)

This document records major architectural decisions made during the conception phase. Each record follows the ADR format: **Context, Decision, Consequences.**

---

## ADR-001: Product Name — "Flux"

**Status:** Accepted  
**Context:** The app needed a name that reflects its nature: mostly idle, with periodic bursts of activity. The original name "Quran Shorts Autoposter" was too specific to one content type.  
**Decision:** Rename to **Flux**. It evokes flow, change, and the idle-to-active cycle. It is short, memorable, and not tied to any religion or content type.  
**Consequences:** All documentation and code references must use "Flux." The Quran pipeline becomes one plugin among many.

---

## ADR-002: Runtime — Android Phone via Termux

**Status:** Accepted  
**Context:** The operator wants to avoid cloud costs and use existing hardware. An old Android phone is available.  
**Decision:** Run Flux on Debian inside Termux on the Android phone. No cloud VPS.  
**Consequences:**
- (+) Zero recurring cost.
- (+) Physical control over data.
- (-) Limited CPU/storage compared to a server.
- (-) Must manage Android battery/Doze behaviour.
- (-) No systemd, no Docker.

---

## ADR-003: Database — SQLite

**Status:** Accepted  
**Context:** Single-node, single-operator system. No need for concurrent writes from multiple clients.  
**Decision:** Use SQLite as the sole database. SQLAlchemy ORM + Alembic for migrations.  
**Consequences:**
- (+) Zero setup, zero background process.
- (+) Survives reboots; file is on persistent storage.
- (+) Perfect fit for APScheduler's SQLite job store.
- (-) No read replicas, no horizontal scaling.
- (-) WAL mode required for concurrent reads during writes.

---

## ADR-004: Plugin Architecture for Content Types

**Status:** Accepted  
**Context:** The operator explicitly wants to add non-Quran content in the future without rewriting the app.  
**Decision:** Implement a plugin system where each content type (Quran, Hadith, News, etc.) is a Python package implementing a `ContentPlugin` interface. The core engine orchestrates; plugins execute.  
**Consequences:**
- (+) True extensibility — new pipelines without core changes.
- (+) Clean separation of concerns.
- (-) Plugin API must be carefully versioned.
- (-) Plugins run with full process privileges (no sandbox).
- (-) Slightly more complexity than a monolithic script.

---

## ADR-005: Web Framework — FastAPI

**Status:** Accepted  
**Context:** Need a lightweight web server for admin panel and API. Must run well on ARM with limited RAM.  
**Decision:** Use FastAPI with Uvicorn. Admin UI is vanilla HTML + Alpine.js (no build step).  
**Consequences:**
- (+) Async-native, performant.
- (+) Auto-generated OpenAPI docs.
- (+) No frontend build pipeline required.
- (-) Less "batteries included" than Django (no built-in auth/admin).
- (-) Operator must implement auth if needed later.

---

## ADR-006: Scheduler — APScheduler (not cron/systemd)

**Status:** Accepted  
**Context:** Termux has no systemd and no reliable system cron. Android may kill background processes.  
**Decision:** Use APScheduler with SQLiteJobStore for all scheduling. Jobs persist in the database and resume after process restart.  
**Consequences:**
- (+) Pure Python, no system dependency.
- (+) Job state survives reboots and crashes.
- (+) Supports cron expressions, intervals, and date triggers.
- (-) Scheduler runs inside the main process — if the process dies, no jobs run until restart.
- (-) Must handle "stuck" jobs after unclean shutdown.

---

## ADR-007: Social Posting — Official APIs First, Unofficial as Fallback

**Status:** Accepted  
**Context:** Platforms have varying API availability. YouTube and Telegram have excellent official APIs. Instagram, TikTok, and X have restrictions.  
**Decision:** Always prefer official APIs. Use unofficial libraries (Instagrapi, TikTokApi) as fallbacks. **Selenium is not viable on Termux** (no Chrome/Chromium package) and is excluded from the architecture.  
**Consequences:**
- (+) Lower ban risk for official APIs.
- (+) More stable and documented.
- (-) Unofficial methods may break without warning.
- (-) Requires careful rate-limiting and session management.
- (-) Some platforms (TikTok) may remain unreliable.

---

## ADR-008: Credential Encryption — Fernet (AES-128 + HMAC)

**Status:** Accepted  
**Context:** Platform credentials (OAuth tokens, session cookies, bot tokens) must be stored securely on the device.  
**Decision:** Encrypt all credentials at rest using Fernet from the `cryptography` library. Master key from `FLUX_MASTER_KEY` environment variable.  
**Consequences:**
- (+) Strong encryption with minimal code.
- (+) Key rotation supported.
- (-) If master key is lost, all credentials are irrecoverable.
- (-) Key must be backed up securely (password manager).

---

## ADR-009: Remote Access — Tailscale Android App + SSH (not DDNS + Port Forwarding)

**Status:** Accepted  
**Context:** Operator needs remote management when away from home. Home router has dynamic IP; port forwarding is insecure and often blocked by CGNAT.  
**Decision:** Install Tailscale Android app (not a Termux package). It creates a WireGuard VPN tunnel. Termux inherits the tunnel. Operator SSHs to the Tailscale IP. Admin panel stays on `127.0.0.1` and is accessed via `ssh -L` port-forward.  
**Consequences:**
- (+) Works across Wi-Fi, 4G, and changing networks.
- (+) Zero-config firewall traversal.
- (+) Free for personal use.
- (+) Admin panel never exposed to LAN or public internet.
- (-) Requires Tailscale Android app running.
- (-) If Tailscale is down, remote access is unavailable (fallback: LAN only).

---

## ADR-010: Watchdog — GitHub Actions + Cloudflare Tunnel

**Status:** Accepted  
**Context:** Operator explicitly requested GitHub Actions as watchdog. Free tier is 2,000 minutes/month. A 15-second workflow every 30 minutes = ~360 minutes/month — well within limits. The phone has no public IP, so GitHub Actions cannot reach it directly.  
**Decision:** Use GitHub Actions on a 30-minute schedule as the primary watchdog. The phone runs `cloudflared` (Cloudflare Tunnel) to expose ONLY `/api/health` on a stable public URL. No router port forwarding needed. GitHub Actions `curl`s this URL. On failure, it sends a Telegram alert. Manual `workflow_dispatch` workflows provide remote commands.  
**Consequences:**
- (+) Fulfills user requirement exactly.
- (+) Free tier sufficient with short, infrequent runs.
- (+) Cloudflare Tunnel is free, stable, and doesn't require a VPS.
- (-) Requires Cloudflare account and `cloudflared` binary on phone.
- (-) If Cloudflare has an outage, watchdog appears failed even if phone is healthy (use Telegram self-pings as cross-check).

---

## ADR-011: Background Removal — FFmpeg colorkey (not AI/ML)

**Status:** Accepted  
**Context:** Quran clips have solid black backgrounds. Background removal could use ML (rembg, MODNet) or traditional filters.  
**Decision:** Use FFmpeg `colorkey` filter. The source material is deterministic (solid black); no ML is needed.  
**Consequences:**
- (+) Extremely fast and deterministic.
- (+) No ML model download or GPU needed.
- (+) Works on any FFmpeg build.
- (-) If source clips change (e.g., grey background), filter must be re-tuned.
- (-) Not generalizable to arbitrary backgrounds.

---

## ADR-012: Admin Panel Auth — None for v1 (localhost-only)

**Status:** Accepted  
**Context:** Single operator, admin panel bound to localhost. Adding auth adds complexity and attack surface.  
**Decision:** No username/password authentication on the admin panel for v1. Access control is network-level (localhost only). LAN access requires SSH port-forward. Remote access requires Tailscale + SSH port-forward.  
**Consequences:**
- (+) Zero friction for the operator.
- (+) No password to forget or leak.
- (-) Anyone on the LAN can access the panel.
- (-) If LAN is compromised, panel is exposed.
- Mitigation: Optional IP allowlist; future v2 may add simple token auth.

---

## ADR-013: Video Render Lock — Global Single Process

**Status:** Accepted  
**Context:** FFmpeg encoding is CPU-intensive. Older phones may overheat with concurrent encodes.  
**Decision:** Enforce a global render lock — only one FFmpeg process runs at a time across all pipelines.  
**Consequences:**
- (+) Prevents thermal throttling and OOM kills.
- (+) Predictable render times.
- (-) If multiple pipelines exist, they queue for the render slot.
- (-) Slows down total throughput if many pipelines are active.
- Mitigation: Fetch and post jobs can run in parallel; only render is serialized.

---

## ADR-014: Ingredient Approval — Required by Default

**Status:** Accepted  
**Context:** Automated content fetching from the internet risks inappropriate or incorrect material, especially for religious content.  
**Decision:** All fetched ingredients enter `pending` status. They cannot be used in production until explicitly approved. Auto-approve is opt-in per ingredient type.  
**Consequences:**
- (+) Content integrity guaranteed.
- (+) Operator maintains editorial control.
- (-) Requires operator attention after each fetch.
- (-) Pipeline cannot be fully hands-off.
- Mitigation: Telegram notifications with one-click approve links; bulk approve UI.

---

## ADR-015: Storage — External (Shared) + Internal Split

**Status:** Accepted  
**Context:** Media files are large. Termux internal storage is limited and deleted if app is uninstalled.  
**Decision:** Store all media (videos, images, logs) on external shared storage (`/storage/emulated/0/Flux/`). Store code, DB, and secrets in Termux internal (`~/flux/`).  
**Consequences:**
- (+) Media survives Termux reinstall.
- (+) Access from file manager for manual review.
- (+) Larger space available.
- (-) Slightly slower I/O than internal.
- (-) External storage is accessible to other apps (Android scoped storage mitigates).

---

## ADR-016: Caption Engine — Jinja2 Templates

**Status:** Accepted  
**Context:** Captions need variable substitution (verse ref, translation, hashtags) and platform-specific formatting.  
**Decision:** Use Jinja2 as the caption template engine. Per-platform overrides supported. Platform workers handle final truncation.  
**Consequences:**
- (+) Powerful, well-documented, familiar to Python developers.
- (+) Supports conditionals and loops for complex templates.
- (-) Operator must learn Jinja2 syntax for custom templates.
- (-) Overly complex templates could be slow (negligible for text).

---

## ADR-017: Notification Channel — Telegram Bot (Primary)

**Status:** Accepted  
**Context:** Operator needs alerts on the go. Email is slow; SMS is expensive; push notifications require app development.  
**Decision:** Use Telegram Bot API as the primary notification channel. All alerts, digests, and approvals route through a bot.  
**Consequences:**
- (+) Instant, free, global.
- (+) Supports rich formatting (Markdown, buttons).
- (+) Operator likely already uses Telegram.
- (-) Requires internet connectivity.
- (-) If Telegram is blocked in region, alternative needed (future: ntfy, email fallback).

---

## ADR-018: Programming Language — Python 3.11

**Status:** Accepted  
**Context:** Operator is comfortable with Python. Ecosystem has libraries for all required integrations.  
**Decision:** Use Python 3.11 as the sole implementation language.  
**Consequences:**
- (+) Rich ecosystem (FastAPI, SQLAlchemy, Pillow, Instagrapi).
- (+) Operator can debug and extend easily.
- (+) Async/await native support.
- (-) Slower than compiled languages for CPU-bound tasks (mitigated by FFmpeg for video).
- (-) GIL limits true parallelism (mitigated by process-based renders).

---

## ADR-019: Version Control — Git + GitHub

**Status:** Accepted  
**Context:** Code needs backup and version history. Operator may want to share or collaborate.  
**Decision:** Host code on GitHub (private repo). Use GitHub Actions for CI/CD and remote commands (not watchdog).  
**Consequences:**
- (+) Full version history.
- (+) Easy rollback via `git checkout`.
- (+) GitHub Actions for remote triggers.
- (-) `.env` and credentials must never be committed (enforced via `.gitignore`).
- (-) Private repo limits collaborators on free tier (but sufficient for 1–2 people).

---

## ADR-020: Database Migrations — Alembic

**Status:** Accepted  
**Context:** Schema will evolve as plugins and features are added.  
**Decision:** Use Alembic (SQLAlchemy's migration tool) for all schema changes.  
**Consequences:**
- (+) Reliable, testable schema evolution.
- (+) Plugin-specific tables can have their own migration scripts.
- (-) Adds dependency and CLI commands to learn.
- (-) Must run `alembic upgrade head` on every deploy.

---

*End of Decision Log. New ADRs added as architecture evolves.*
