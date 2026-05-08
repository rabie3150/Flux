"""System hardening utilities — backup, thermal guard, and health checks.

Provides:
    - Automated SQLite backup with rotation (7-day retention)
    - Thermal sensor check before CPU-intensive renders (Android/Linux)
    - Rich health check with subsystem status
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Database backup
# ---------------------------------------------------------------------------

_BACKUP_RETENTION_DAYS = 7
_BACKUP_DIR_NAME = "backups"


def _get_db_path() -> Path | None:
    """Extract the actual file path from the SQLite URL."""
    url = settings.database_url
    # Handle both sync and async URLs
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            return Path(url[len(prefix):])
    return None


def _backup_dir() -> Path:
    """Return the backup directory, creating it if needed."""
    backup_dir = Path(settings.storage_path) / _BACKUP_DIR_NAME
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_db_backup() -> Path | None:
    """Create a timestamped SQLite backup using the .backup command.

    Returns the path to the backup file, or None on failure.
    Uses sqlite3 CLI for a safe online backup (doesn't lock the WAL).
    """
    db_path = _get_db_path()
    if not db_path or not db_path.exists():
        logger.error("Cannot backup: database file not found at %s", db_path)
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = _backup_dir() / f"app-{timestamp}.db"

    try:
        # Try sqlite3 CLI backup first (safe online backup)
        result = subprocess.run(
            ["sqlite3", str(db_path), f".backup '{backup_path}'"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info("DB backup created: %s (%.1f MB)", backup_path, size_mb)
            return backup_path
        else:
            logger.warning(
                "sqlite3 CLI backup failed (rc=%d): %s. Falling back to file copy.",
                result.returncode,
                result.stderr.strip(),
            )
    except FileNotFoundError:
        logger.warning("sqlite3 CLI not found. Falling back to file copy.")
    except subprocess.TimeoutExpired:
        logger.error("sqlite3 backup timed out after 60s")
    except Exception as exc:
        logger.warning("sqlite3 backup failed: %s. Falling back to file copy.", exc)

    # Fallback: simple file copy (safe enough for WAL mode in most cases)
    try:
        shutil.copy2(str(db_path), str(backup_path))
        # Also copy WAL and SHM if they exist
        for suffix in ("-wal", "-shm"):
            wal_file = Path(str(db_path) + suffix)
            if wal_file.exists():
                shutil.copy2(str(wal_file), str(backup_path) + suffix)

        size_mb = backup_path.stat().st_size / (1024 * 1024)
        logger.info("DB backup created (file copy): %s (%.1f MB)", backup_path, size_mb)
        return backup_path
    except Exception as exc:
        logger.error("DB backup failed completely: %s", exc)
        return None


def cleanup_old_backups() -> int:
    """Delete backups older than _BACKUP_RETENTION_DAYS. Returns count deleted."""
    backup_dir = _backup_dir()
    cutoff = datetime.now(timezone.utc).timestamp() - (_BACKUP_RETENTION_DAYS * 86400)
    deleted = 0

    for f in backup_dir.glob("app-*.db*"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        except OSError as exc:
            logger.warning("Failed to delete old backup %s: %s", f, exc)

    if deleted:
        logger.info("Cleaned up %d old backup(s)", deleted)
    return deleted


async def run_backup_job() -> dict:
    """APScheduler-compatible backup job. Creates backup and cleans old ones."""
    logger.info("Running scheduled DB backup...")
    backup_path = create_db_backup()
    deleted = cleanup_old_backups()
    
    # Also run DB data retention cleanup
    cleanup_stats = await cleanup_database()
    
    return {
        "backup": str(backup_path) if backup_path else None,
        "cleaned": deleted,
        "db_cleanup": cleanup_stats,
    }


# ---------------------------------------------------------------------------
# Data Retention
# ---------------------------------------------------------------------------

async def cleanup_database() -> dict[str, int]:
    """Apply data retention policies to the database.
    
    - Delete rejected ingredients older than 7 days
    - Delete activity logs older than 30 days
    - Clear render logs from produced content older than 7 days
    """
    from flux.db import AsyncSessionLocal
    from flux.models import Ingredient, ActivityLog, ProducedContent
    from sqlalchemy import delete, update
    import time
    
    now = time.time()
    seven_days_ago = datetime.fromtimestamp(now - (7 * 86400), tz=timezone.utc)
    thirty_days_ago = datetime.fromtimestamp(now - (30 * 86400), tz=timezone.utc)
    
    stats = {"rejected_ingredients_deleted": 0, "activity_logs_deleted": 0, "render_logs_cleared": 0}
    
    try:
        async with AsyncSessionLocal() as db:
            # 1. Delete rejected ingredients > 7 days
            stmt_ing = delete(Ingredient).where(
                Ingredient.status == "rejected",
                Ingredient.created_at < seven_days_ago
            )
            res_ing = await db.execute(stmt_ing)
            stats["rejected_ingredients_deleted"] = res_ing.rowcount
            
            # 2. Delete activity logs > 30 days
            stmt_act = delete(ActivityLog).where(
                ActivityLog.timestamp < thirty_days_ago
            )
            res_act = await db.execute(stmt_act)
            stats["activity_logs_deleted"] = res_act.rowcount
            
            # 3. Clear render logs > 7 days
            stmt_ren = update(ProducedContent).where(
                ProducedContent.render_log.isnot(None),
                ProducedContent.created_at < seven_days_ago
            ).values(render_log=None)
            res_ren = await db.execute(stmt_ren)
            stats["render_logs_cleared"] = res_ren.rowcount
            
            await db.commit()
            
        logger.info(
            "Data retention cleanup complete: %d rejected ingredients deleted, "
            "%d old activity logs deleted, %d old render logs cleared.",
            stats["rejected_ingredients_deleted"],
            stats["activity_logs_deleted"],
            stats["render_logs_cleared"]
        )
    except Exception as exc:
        logger.error("Data retention cleanup failed: %s", exc)
        
    return stats


# ---------------------------------------------------------------------------
# Thermal guard
# ---------------------------------------------------------------------------

# Thermal zone paths on Linux/Android
_THERMAL_PATHS = [
    Path("/sys/class/thermal/thermal_zone0/temp"),    # Most common
    Path("/sys/devices/virtual/thermal/thermal_zone0/temp"),
]

# Default thresholds in °C
THERMAL_WARN_C = 55  # Log a warning
THERMAL_BLOCK_C = 65  # Block render entirely


def read_cpu_temp() -> float | None:
    """Read CPU temperature in °C from sysfs.

    Returns None if the thermal sensor is unavailable (Windows, macOS, or
    no access to sysfs).
    """
    for path in _THERMAL_PATHS:
        try:
            raw = path.read_text().strip()
            # Value is in millidegrees on most Android/Linux systems
            temp_raw = int(raw)
            # Heuristic: if value > 1000, it's millidegrees
            if temp_raw > 1000:
                return temp_raw / 1000.0
            return float(temp_raw)
        except (FileNotFoundError, PermissionError, ValueError, OSError):
            continue
    return None


def check_thermal_safe(
    warn_c: float = THERMAL_WARN_C,
    block_c: float = THERMAL_BLOCK_C,
) -> tuple[bool, float | None]:
    """Check if the device is thermally safe for a render.

    Returns:
        (is_safe, temperature_c) — is_safe is False if temp >= block_c,
        temperature_c is None if the sensor is unavailable.
    """
    temp = read_cpu_temp()
    if temp is None:
        # No sensor available (Windows, macOS) — allow render
        logger.debug("Thermal sensor not available (non-Linux or no access)")
        return True, None

    if temp >= block_c:
        logger.warning(
            "🌡️ CPU temperature %.1f°C exceeds block threshold (%.0f°C) — render BLOCKED",
            temp, block_c,
        )
        return False, temp

    if temp >= warn_c:
        logger.warning(
            "🌡️ CPU temperature %.1f°C exceeds warning threshold (%.0f°C) — render allowed but device is hot",
            temp, warn_c,
        )

    return True, temp


# ---------------------------------------------------------------------------
# Rich health check
# ---------------------------------------------------------------------------

async def rich_health_check() -> dict:
    """Comprehensive health check with subsystem status.

    Returns a dict matching the conceived schema from doc 13-monitoring §2.1.
    """
    from flux.db import AsyncSessionLocal
    from flux.models import PlatformWorker
    from sqlalchemy import select, text

    checks: dict = {}

    # ── Database ──
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"fail: {exc}"

    # ── Scheduler ──
    try:
        from flux.scheduler import get_scheduler
        sched = get_scheduler()
        job_count = len(sched.get_jobs())
        checks["scheduler"] = f"ok ({job_count} jobs)"
    except RuntimeError:
        checks["scheduler"] = "not_initialized"
    except Exception as exc:
        checks["scheduler"] = f"fail: {exc}"

    # ── Storage ──
    try:
        from flux.core.storage import get_storage_budget
        budget = get_storage_budget()
        
        if budget.is_critical:
            checks["storage"] = f"critical: {budget.percent_used:.0f}% of budget used"
        elif budget.is_warning:
            checks["storage"] = f"warn: {budget.percent_used:.0f}% of budget used"
        else:
            checks["storage"] = f"ok ({budget.percent_used:.0f}% of budget used)"
    except Exception as exc:
        checks["storage"] = f"fail: {exc}"

    # ── Thermal ──
    temp = read_cpu_temp()
    if temp is not None:
        if temp >= THERMAL_BLOCK_C:
            checks["thermal"] = f"critical: {temp:.0f}°C"
        elif temp >= THERMAL_WARN_C:
            checks["thermal"] = f"warn: {temp:.0f}°C"
        else:
            checks["thermal"] = f"ok ({temp:.0f}°C)"
    else:
        checks["thermal"] = "n/a"

    # ── Workers ──
    worker_checks = {}
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(PlatformWorker))
            workers = result.scalars().all()
            for w in workers:
                if not w.enabled:
                    worker_checks[w.display_name] = "paused"
                elif w.last_error_message:
                    worker_checks[w.display_name] = f"error: {w.last_error_message[:80]}"
                else:
                    worker_checks[w.display_name] = "ok"
    except Exception as exc:
        worker_checks["_error"] = str(exc)
    checks["workers"] = worker_checks

    # ── Overall status ──
    flat_values = []
    for v in checks.values():
        if isinstance(v, dict):
            flat_values.extend(v.values())
        else:
            flat_values.append(v)

    has_critical = any("fail" in str(v) or "critical" in str(v) for v in flat_values)
    has_warn = any("warn" in str(v) or "error" in str(v) or "paused" in str(v) for v in flat_values)

    if has_critical:
        status = "unhealthy"
    elif has_warn:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
