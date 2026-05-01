"""Scheduler job registration for platform workers.

On startup, reads all enabled workers with cron schedules and registers
APScheduler jobs. Re-registration happens when workers are created/updated.
"""

from __future__ import annotations

from flux.core.publish import publish_for_worker
from flux.db import AsyncSessionLocal
from flux.logger import get_logger
from flux.models import PlatformWorker
from flux.scheduler import get_scheduler
from sqlalchemy import select

logger = get_logger(__name__)

_JOB_PREFIX = "flux_worker_"


def _job_id(worker_id: str) -> str:
    return f"{_JOB_PREFIX}{worker_id}"


async def register_worker_jobs() -> None:
    """Register APScheduler cron jobs for all enabled workers."""
    try:
        scheduler = get_scheduler()
    except RuntimeError:
        logger.debug("Scheduler not initialized, skipping worker job registration")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PlatformWorker).where(
                PlatformWorker.enabled == True,
                PlatformWorker.schedule_cron.isnot(None),
            )
        )
        workers = result.scalars().all()

    # Remove stale worker jobs
    for job in scheduler.get_jobs():
        if job.id.startswith(_JOB_PREFIX):
            scheduler.remove_job(job.id)

    for worker in workers:
        job_id = _job_id(worker.id)
        try:
            scheduler.add_job(
                func=_run_publish,
                trigger="cron",
                id=job_id,
                replace_existing=True,
                ** _parse_cron(worker.schedule_cron),
                args=[worker.id],
            )
            logger.info("Scheduled worker job %s: %s", job_id, worker.schedule_cron)
        except ValueError as exc:
            logger.error("Invalid cron for worker %s: %s — %s", worker.id, worker.schedule_cron, exc)


def _parse_cron(cron: str) -> dict:
    """Parse a standard 5-field cron string into APScheduler kwargs."""
    parts = cron.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Cron must have 5 fields, got {len(parts)}: {cron}")
    minute, hour, day, month, day_of_week = parts
    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "day_of_week": day_of_week,
    }


async def _run_publish(worker_id: str) -> None:
    """Wrapper called by APScheduler."""
    try:
        await publish_for_worker(worker_id)
    except Exception:
        logger.exception("Unhandled exception in publish job for worker %s", worker_id)


async def refresh_worker_job(worker_id: str) -> None:
    """Re-register a single worker's job (call after create/update)."""
    try:
        scheduler = get_scheduler()
    except RuntimeError:
        return

    async with AsyncSessionLocal() as db:
        worker = await db.get(PlatformWorker, worker_id)
    if not worker or not worker.enabled or not worker.schedule_cron:
        # Remove job if worker disabled or has no schedule
        try:
            scheduler.remove_job(_job_id(worker_id))
        except Exception:
            pass
        return

    job_id = _job_id(worker_id)
    try:
        scheduler.add_job(
            func=_run_publish,
            trigger="cron",
            id=job_id,
            replace_existing=True,
            **_parse_cron(worker.schedule_cron),
            args=[worker.id],
        )
        logger.info("Refreshed worker job %s: %s", job_id, worker.schedule_cron)
    except ValueError as exc:
        logger.error("Invalid cron for worker %s: %s — %s", worker.id, worker.schedule_cron, exc)


async def remove_worker_job(worker_id: str) -> None:
    """Remove a worker's scheduled job."""
    try:
        scheduler = get_scheduler()
    except RuntimeError:
        return
    job_id = _job_id(worker_id)
    try:
        scheduler.remove_job(job_id)
        logger.info("Removed worker job %s", job_id)
    except Exception:
        pass  # Job may not exist
