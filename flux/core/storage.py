"""Storage budget tracker and disk management."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StorageBudget:
    """Represents current storage usage relative to the configured budget."""
    total_budget_bytes: int
    used_bytes: int
    free_bytes: int
    percent_used: float
    is_critical: bool  # e.g., >95% of budget used
    is_warning: bool   # e.g., >80% of budget used


def _get_dir_size(path: str | Path) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _get_dir_size(entry.path)
    except OSError as e:
        logger.warning("Failed to calculate size for %s: %s", path, e)
    return total


def get_storage_budget() -> StorageBudget:
    """Calculate Flux storage usage against the configured budget."""
    budget_bytes = settings.storage_budget_gb * 1024 * 1024 * 1024
    storage_path = Path(settings.storage_path)
    
    used_bytes = 0
    if storage_path.exists():
        used_bytes = _get_dir_size(storage_path)
        
    # Also include base_path if it's different and exists (for DB, logs, etc.)
    base_path = Path(settings.base_path)
    if base_path.exists() and base_path.resolve() != storage_path.resolve():
        # Prevent counting the same directory twice if one is inside the other
        try:
            if not str(storage_path.resolve()).startswith(str(base_path.resolve())):
                used_bytes += _get_dir_size(base_path)
        except OSError:
            pass

    free_bytes = max(0, budget_bytes - used_bytes)
    percent_used = (used_bytes / budget_bytes * 100) if budget_bytes > 0 else 0.0

    return StorageBudget(
        total_budget_bytes=budget_bytes,
        used_bytes=used_bytes,
        free_bytes=free_bytes,
        percent_used=percent_used,
        is_critical=percent_used >= 95.0,
        is_warning=percent_used >= 80.0,
    )


def get_system_disk_usage() -> dict[str, Any]:
    """Get the physical disk usage where the storage path resides."""
    storage_path = Path(settings.storage_path)
    
    # Fallback to current directory if storage path doesn't exist yet
    check_path = storage_path if storage_path.exists() else Path.cwd()
    
    try:
        usage = shutil.disk_usage(str(check_path))
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "percent_used": (usage.used / usage.total) * 100 if usage.total > 0 else 0,
        }
    except OSError as e:
        logger.error("Failed to get disk usage for %s: %s", check_path, e)
        return {
            "total_bytes": 0,
            "used_bytes": 0,
            "free_bytes": 0,
            "percent_used": 0,
        }
