# Flux — Monitoring, Observability & Alerting Strategy

## 1. Philosophy

Flux is a single-node system, so "monitoring" does not mean Prometheus + Grafana. It means:

1. **Self-awareness:** The daemon knows its own health and reports it.
2. **External validation:** Something outside the phone confirms the phone is alive.
3. **Actionable alerts:** Every notification includes what happened and what to do.
4. **Minimal noise:** Steady-state success is silent; only exceptions and summaries are noisy.

---

## 2. Health Check Model

### 2.1 Health Endpoint

```
GET /api/health
```

```json
{
  "status": "healthy",
  "uptime_seconds": 1209600,
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "scheduler": "ok",
    "storage": "ok",
    "plugins": {
      "quran_shorts": "ok"
    },
    "workers": {
      "youtube_ch1": "ok",
      "telegram_main": "ok",
      "instagram_main": "paused — last error: session expired"
    }
  },
  "timestamp": "2026-04-25T18:00:00Z"
}
```

**Status values:** `healthy` | `degraded` | `unhealthy`

- `degraded`: One or more non-critical subsystems down (e.g., one worker paused, storage > 80%).
- `unhealthy`: Critical subsystem down (DB unreachable, all workers failed, storage > 95%).

### 2.2 Internal Health Job

Runs every 5 minutes via APScheduler:

```python
async def health_check():
    checks = {}
    
    # DB
    try:
        await db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"fail: {e}"
    
    # Storage
    usage = get_storage_usage()
    if usage.percent > 95:
        checks["storage"] = f"critical: {usage.percent}%"
    elif usage.percent > 80:
        checks["storage"] = f"warn: {usage.percent}%"
    else:
        checks["storage"] = "ok"
    
    # Workers
    for worker in await get_all_workers():
        if worker.last_error_at and worker.last_error_at > now - timedelta(hours=24):
            checks["workers"][worker.id] = f"error: {worker.last_error_message}"
        else:
            checks["workers"][worker.id] = "ok"
    
    # Store in DB for trend analysis
    await db.insert_health_snapshot(checks)
    
    # Alert if degraded/unhealthy
    if any("fail" in v or "critical" in v for v in flatten(checks)):
        await notify_telegram("Health check FAILED", checks)
```

---

## 3. External Monitoring (Watchdog)

### 3.1 GitHub Actions Watchdog Configuration

`.github/workflows/watchdog.yml` runs every 30 minutes. It `curl`s the phone's public health endpoint (Cloudflare Tunnel URL) from `ubuntu-latest`.

| Setting | Value |
|---------|-------|
| Trigger | `schedule: - cron: '*/30 * * * *'` + `workflow_dispatch` |
| URL | `${{ secrets.FLUX_PUBLIC_URL }}/api/health` |
| Timeout | 30 seconds |
| Alert after | 1 failure (HTTP != 200) |
| Notification | Telegram bot message via `curl` in workflow |

### 3.2 What the Watchdog Detects

- Phone is offline (no response).
- Daemon crashed (port not listening).
- Cloudflare Tunnel down (unreachable).
- Home internet outage.

### 3.3 What the Watchdog Cannot Detect

- Daemon is running but jobs are stuck (scheduler deadlock).
- Content pipeline is broken (fetches fail silently).
- Renders are failing but daemon is healthy.

**These are covered by internal health checks and Telegram alerts.**

---

## 4. Logging Strategy

### 4.1 Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| `DEBUG` | Development only; disabled in production | "Fetching page 3 of Pexels results" |
| `INFO` | Major lifecycle events | "Render started for video_id=abc123" |
| `WARNING` | Recoverable issues | "Pexels rate limit approached, backing off" |
| `ERROR` | Failures requiring attention | "Instagram post failed: 403 Forbidden" |
| `CRITICAL` | System-level failures | "Database connection lost, shutting down" |

### 4.2 Log Format

```
2026-04-25 08:30:15 [INFO] [pipeline:quran_daily] [worker:youtube_ch1] Post published: video_id=abc123 platform_post_id=xyz789
```

Structured fields for easy parsing:
- Timestamp (local timezone)
- Level
- Context (pipeline, worker, job ID)
- Message
- Optional metadata JSON

### 4.3 Log Storage

| Location | Retention | Size cap |
|----------|-----------|----------|
| `/storage/emulated/0/Flux/logs/app.log` | 7 days | 5 MB per file, 5 backups |
| SQLite `activity_log` table | 30 days | No hard cap (rows are small) |
| FFmpeg render logs | 7 days | Per-render log, auto-deleted with video |

### 4.4 Log Redaction

All log messages pass through a redaction filter:

```python
REDACT_PATTERNS = [
    (r'Bearer\s+\S+', 'Bearer [REDACTED]'),
    (r'bot\d+:[A-Za-z0-9_-]+', '[BOT_TOKEN_REDACTED]'),
    (r'client_secret\S+', '[CLIENT_SECRET_REDACTED]'),
]
```

---

## 5. Alerting Rules

### 5.1 Immediate Alerts (Send Telegram within 60 seconds)

| Condition | Severity | Message Template |
|-----------|----------|------------------|
| Worker permanently failed (3× retries) | Warning | "Worker `{name}` paused after 3 failures. Last error: `{error}`" |
| Storage >= 95% | Critical | "Storage CRITICAL: {used}/{total} GB. Fetch and render paused." |
| Storage >= 80% | Warning | "Storage warning: {used}/{total} GB. Consider enabling auto-delete." |
| Render failed 3× consecutive | Critical | "Render pipeline failing. Check FFmpeg logs." |
| Verse unknown backlog > 5 | Warning | "{count} videos need verse assignment. Review production queue." |
| Database connection error | Critical | "Database error: {error}. Daemon may restart." |
| GitHub Actions watchdog fails | Critical | "External watchdog: Flux unreachable. Check phone, tunnel, and internet." |

### 5.2 Digest Alerts (Batch and send daily at 09:00)

| Condition | Format |
|-----------|--------|
| Daily summary | "Yesterday: {n_fetched} fetched, {n_rendered} rendered, {n_posted} posted, {n_failed} failed." |
| Weekly quota | "YouTube quota: {used}/10,000 units ({percent}%). Resets in {hours}h." |
| Storage trend | "Storage: {used}/{total} GB ({percent}%). Trend: +{delta} GB this week." |

### 5.3 Silent Events (No alert)

- Single successful post.
- Single successful render.
- Routine fetch with 0 new items.
- Scheduled job starting (only log, no alert).

---

## 6. Metrics & Observability

### 6.1 Key Metrics Tracked

| Metric | Type | Source |
|--------|------|--------|
| `flux_posts_total` | Counter | `post_records` inserts |
| `flux_posts_failed` | Counter | `post_records` with status=failed |
| `flux_renders_total` | Counter | `produced_content` inserts |
| `flux_renders_duration_seconds` | Histogram | Render start → end timestamp |
| `flux_fetch_items_total` | Counter | `ingredients` inserts |
| `flux_storage_used_bytes` | Gauge | File system scan |
| `flux_worker_last_post_timestamp` | Gauge | `platform_workers.last_posted_at` |
| `flux_queue_depth` | Gauge | Count of `ready` videos |
| `flux_content_review_backlog` | Gauge | Count of `produced_content` items with `review_flag=true` in metadata |

### 6.2 Metrics Endpoint

```
GET /api/metrics
```

Returns Prometheus-compatible text (lightweight; no Prometheus server required). Operator can scrape manually or via simple script.

```
# HELP flux_posts_total Total posts attempted
# TYPE flux_posts_total counter
flux_posts_total{platform="youtube"} 42
flux_posts_total{platform="telegram"} 42

# HELP flux_storage_used_bytes Storage usage
# TYPE flux_storage_used_bytes gauge
flux_storage_used_bytes 3435973836
```

---

## 7. Dashboard Observability

The admin panel itself is the primary observability UI.

### 7.1 Real-Time Indicators

| Indicator | Location | Refresh |
|-----------|----------|---------|
| Daemon uptime | Dashboard header | Every 30s |
| Next scheduled action | Dashboard | Every 30s |
| Render progress | Pipeline detail | Every 10s (if rendering) |
| Worker status dots | Dashboard / Workers | Every 60s |
| Storage bar | Dashboard | Every 5 min |

### 7.2 Historical Views

- **Activity log:** Filterable table of all events.
- **Post history:** Calendar view of what was posted when.
- **Storage chart:** 7-day trend line (derived from daily snapshots).
- **Render time chart:** Average render duration over time.

---

## 8. On-Call Playbook (Operator Self-Help)

Since there is no operations team, the operator is the on-call engineer. Alerts must be self-resolving or clearly instructive.

| Alert | Diagnostic Command | Resolution |
|-------|-------------------|------------|
| "Flux unreachable" | Check GitHub Actions logs → SSH into phone → `ps aux | grep uvicorn` | `~/flux/start.sh` or reboot phone |
| "Worker paused" | Admin panel → Worker detail → check error log | Re-authenticate, fix credentials, or resume if transient |
| "Storage critical" | `df -h` or admin panel | Enable auto-delete, manually delete old renders, or expand budget |
| "Render failing" | `tail /storage/.../logs/ffmpeg/render_*.log` | Check FFmpeg command, reduce preset, check disk space |
| "Verse unknown backlog" | Admin panel → Production queue | Manually assign verse references |
| "Database error" | `sqlite3 app.db "PRAGMA integrity_check;"` | Restore from backup if corrupted |

---

## 9. Future Observability (v2.0+)

| Feature | Purpose |
|---------|---------|
| Structured JSON logs shipped to free cloud log aggregator (e.g., Logtail free tier) | Off-device log persistence |
| Custom metrics dashboard (Grafana via Docker on home NAS) | Rich visualizations |
| Mobile push notifications (via Pushover or ntfy) | Alternative to Telegram |
| Anomaly detection ("Your average post time increased 300%") | Early problem detection |
