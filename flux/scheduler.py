"""APScheduler setup for Flux.

Jobs persist in SQLite so they survive daemon restarts.
Only one instance of each job type runs at a time.
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Return the global scheduler instance."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    return _scheduler


def init_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    Uses SQLite job store for persistence.
    Must be started after the asyncio event loop is running.
    """
    global _scheduler

    if _scheduler is not None:
        return _scheduler

    # Use sync SQLite URL for APScheduler job store
    jobstore_url = settings.database_url
    # APScheduler needs a sync driver; strip aiosqlite if present
    if "+aiosqlite" in jobstore_url:
        jobstore_url = jobstore_url.replace("+aiosqlite", "")

    jobstores = {
        "default": SQLAlchemyJobStore(url=jobstore_url),
    }

    job_defaults = {
        "coalesce": True,  # Missed jobs run once, not multiple times
        "max_instances": 1,  # Only one instance of each job at a time
        "misfire_grace_time": 3600,  # 1 hour grace for misfires
    }

    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        job_defaults=job_defaults,
        timezone="UTC",
    )
    logger.info("Scheduler initialized with SQLite jobstore")

    return _scheduler


def shutdown_scheduler(wait: bool = True) -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=wait)
        _scheduler = None
        logger.info("Scheduler shut down")
