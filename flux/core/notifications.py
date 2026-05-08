"""Telegram notification service for system alerts and digests.

Handles immediate alerts for critical errors, and compiles daily/weekly
digests of system activity.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.config import settings
from flux.logger import get_logger
from flux.models import ActivityLog, Ingredient, PlatformWorker, PostRecord, ProducedContent

logger = get_logger(__name__)

# In-memory rate limiting to prevent notification floods
_last_alert_times: dict[str, datetime] = {}
COOLDOWN_MINUTES = 60


async def _send_telegram_message(text: str, alert_type: str | None = None) -> bool:
    """Send an HTML-formatted message via Telegram Bot API."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.debug("Skipping Telegram alert (credentials not configured): %s", text.split("\n")[0])
        return False
        
    if alert_type:
        now = datetime.now(timezone.utc)
        last_time = _last_alert_times.get(alert_type)
        if last_time and (now - last_time).total_seconds() < (COOLDOWN_MINUTES * 60):
            logger.debug("Skipping Telegram alert '%s' due to cooldown", alert_type)
            return False
        _last_alert_times[alert_type] = now

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    def _sync_request():
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except urllib.error.URLError as e:
            logger.error("Failed to send Telegram alert: %s", e)
            return False

    return await asyncio.to_thread(_sync_request)


# ---------------------------------------------------------------------------
# Immediate Alerts
# ---------------------------------------------------------------------------

async def send_alert_worker_failed(worker_name: str, platform: str, error_msg: str) -> None:
    """Alert when a platform worker fails to post."""
    text = (
        f"🚨 <b>Worker Failed</b>\n"
        f"<b>Worker:</b> {worker_name} ({platform})\n"
        f"<b>Error:</b> <code>{error_msg}</code>\n"
        f"<i>Automated posting is likely halted for this worker.</i>"
    )
    await _send_telegram_message(text, alert_type=f"worker_failed_{worker_name}")


async def send_alert_storage_critical(percent_used: float, used_mb: float, free_mb: float) -> None:
    """Alert when storage budget usage exceeds 95%."""
    text = (
        f"⚠️ <b>Storage Critical</b>\n"
        f"<b>Usage:</b> {percent_used:.1f}%\n"
        f"<b>Used:</b> {used_mb:.1f} MB\n"
        f"<b>Free:</b> {free_mb:.1f} MB\n"
        f"<i>Please free up space or increase STORAGE_BUDGET_GB.</i>"
    )
    await _send_telegram_message(text, alert_type="storage_critical")


async def send_alert_render_failed(pipeline_id: str, error_msg: str, consecutive_failures: int) -> None:
    """Alert when FFmpeg render fails multiple times."""
    if consecutive_failures < 3:
        return  # Only alert on repeated failures to reduce noise

    text = (
        f"🚨 <b>Render Failing</b>\n"
        f"<b>Pipeline:</b> {pipeline_id}\n"
        f"<b>Failures:</b> {consecutive_failures} consecutive\n"
        f"<b>Latest Error:</b> <code>{error_msg}</code>\n"
    )
    await _send_telegram_message(text, alert_type=f"render_failed_{pipeline_id}")


async def send_alert_db_error(error_msg: str) -> None:
    """Alert when a critical database operation fails."""
    text = (
        f"💥 <b>Database Error</b>\n"
        f"<b>Error:</b> <code>{error_msg}</code>\n"
        f"<i>The system may be unstable.</i>"
    )
    await _send_telegram_message(text, alert_type="db_error")


async def send_alert_verse_backlog(backlog_count: int) -> None:
    """Alert when many rendered videos are missing verse identification."""
    if backlog_count < 10:
        return
        
    text = (
        f"⚠️ <b>Verse ID Backlog</b>\n"
        f"<b>Count:</b> {backlog_count} videos missing identification.\n"
        f"<i>Check AI quotas or regex patterns.</i>"
    )
    await _send_telegram_message(text, alert_type="verse_backlog")


# ---------------------------------------------------------------------------
# Digests
# ---------------------------------------------------------------------------

async def _get_daily_stats(db: AsyncSession) -> dict[str, Any]:
    """Gather statistics for the last 24 hours."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    # Posts
    posts_res = await db.execute(
        select(PostRecord.status, func.count(PostRecord.id))
        .where(PostRecord.created_at >= yesterday)
        .group_by(PostRecord.status)
    )
    posts = {row[0]: row[1] for row in posts_res.all()}

    # Renders
    renders_res = await db.execute(
        select(ProducedContent.status, func.count(ProducedContent.id))
        .where(ProducedContent.rendered_at >= yesterday)
        .group_by(ProducedContent.status)
    )
    renders = {row[0]: row[1] for row in renders_res.all()}

    # Ingredients fetched
    ing_res = await db.execute(
        select(func.count(Ingredient.id))
        .where(Ingredient.created_at >= yesterday)
    )
    ingredients_fetched = ing_res.scalar_one() or 0

    return {
        "posts_published": posts.get("published", 0),
        "posts_failed": posts.get("failed", 0),
        "renders_success": renders.get("rendered", 0) + renders.get("ready", 0) + renders.get("published", 0),
        "renders_failed": renders.get("failed", 0),
        "ingredients_fetched": ingredients_fetched,
    }


async def send_daily_digest() -> None:
    """Compile and send the daily digest."""
    from flux.db import AsyncSessionLocal
    from flux.core.storage import get_storage_budget

    try:
        async with AsyncSessionLocal() as db:
            stats = await _get_daily_stats(db)
            
        storage = get_storage_budget()
        
        text = (
            f"📊 <b>Flux Daily Digest</b>\n"
            f"<i>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</i>\n\n"
            f"<b>Posts:</b> {stats['posts_published']} ✅ | {stats['posts_failed']} ❌\n"
            f"<b>Renders:</b> {stats['renders_success']} ✅ | {stats['renders_failed']} ❌\n"
            f"<b>Fetched:</b> {stats['ingredients_fetched']} items\n\n"
            f"<b>Storage:</b> {storage.percent_used:.1f}% ({storage.used_bytes / 1024 / 1024:.0f} MB)\n"
        )
        await _send_telegram_message(text)
        logger.info("Daily digest sent to Telegram")
    except Exception as e:
        logger.error("Failed to compile or send daily digest: %s", e)


async def send_weekly_digest() -> None:
    """Compile and send the weekly digest (storage trends, quotas)."""
    from flux.db import AsyncSessionLocal
    from flux.core.storage import get_storage_budget

    now = datetime.now(timezone.utc)
    last_week = now - timedelta(days=7)

    try:
        async with AsyncSessionLocal() as db:
            # Renders total
            renders_res = await db.execute(
                select(func.count(ProducedContent.id))
                .where(ProducedContent.rendered_at >= last_week)
            )
            total_renders = renders_res.scalar_one() or 0
            
            # Posts total
            posts_res = await db.execute(
                select(func.count(PostRecord.id))
                .where(PostRecord.published_at >= last_week)
            )
            total_posts = posts_res.scalar_one() or 0

        storage = get_storage_budget()
        
        text = (
            f"📈 <b>Flux Weekly Digest</b>\n"
            f"<i>{now.strftime('%Y-%m-%d')}</i>\n\n"
            f"<b>7-Day Activity:</b>\n"
            f"• {total_renders} total renders\n"
            f"• {total_posts} total posts\n\n"
            f"<b>Storage Trend:</b>\n"
            f"• Budget Used: {storage.percent_used:.1f}%\n"
            f"• Free Space: {storage.free_bytes / 1024 / 1024:.0f} MB\n"
        )
        await _send_telegram_message(text)
        logger.info("Weekly digest sent to Telegram")
    except Exception as e:
        logger.error("Failed to compile or send weekly digest: %s", e)
