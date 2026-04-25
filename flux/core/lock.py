"""File-based render lock.

Prevents concurrent FFmpeg renders. Only one render may run at a time
across all pipelines (CPU and thermal constraint on mobile).
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from flux.config import settings

_LOCK_FILE: Path = Path(settings.storage_path) / ".flux-render.lock"


def _ensure_lock_dir() -> None:
    """Create lock file directory if it doesn't exist."""
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)


class LockBusyError(Exception):
    """Raised when the render lock is already held."""


def _acquire_unix(fd: int, timeout: float) -> bool:
    """Unix advisory lock via fcntl with optional timeout."""
    import fcntl

    if timeout <= 0:
        try:
            fcntl.flock(fd, fcntl.LOCK_NB | fcntl.LOCK_EX)
            return True
        except (OSError, BlockingIOError, IOError):
            return False

    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_NB | fcntl.LOCK_EX)
            return True
        except (OSError, BlockingIOError, IOError):
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)


def _release_unix(fd: int) -> None:
    """Release Unix advisory lock."""
    import fcntl

    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def _acquire_windows(timeout: float) -> tuple[bool, int | None]:
    """Windows lock via exclusive file creation."""
    deadline = time.monotonic() + timeout if timeout > 0 else 0
    while True:
        try:
            fd = os.open(
                str(_LOCK_FILE),
                os.O_CREAT | os.O_EXCL | os.O_RDWR,
            )
            return True, fd
        except FileExistsError:
            if timeout <= 0 or time.monotonic() >= deadline:
                return False, None
            time.sleep(0.1)


def _release_windows() -> None:
    """Release Windows lock by deleting lock file."""
    try:
        _LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


class RenderLock:
    """Cross-process file lock for render coordination.

    Unix (Termux/Linux/macOS): fcntl advisory locks.
    Windows: exclusive file creation (simplified).
    """

    def __init__(self) -> None:
        self._fd: int | None = None
        self._acquired = False

    async def acquire(self, timeout: float = 0.0) -> bool:
        """Try to acquire the lock. timeout=0 means non-blocking."""
        _ensure_lock_dir()

        if os.name == "nt":
            acquired, fd = _acquire_windows(timeout)
            if acquired:
                self._fd = fd
                self._acquired = True
            return acquired

        # Unix path
        try:
            self._fd = os.open(str(_LOCK_FILE), os.O_RDWR | os.O_CREAT, 0o666)
            acquired = _acquire_unix(self._fd, timeout=timeout)
            if acquired:
                self._acquired = True
                return True
        except OSError:
            pass

        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        return False

    def release(self) -> None:
        """Release the lock. Safe to call even if not acquired."""
        if not self._acquired:
            return

        if os.name != "nt" and self._fd is not None:
            _release_unix(self._fd)
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        elif os.name == "nt":
            _release_windows()

        self._acquired = False

    def __del__(self) -> None:
        if self._acquired:
            self.release()


@asynccontextmanager
async def render_lock_ctx(timeout: float = 0.0):
    """Async context manager for render lock.

    Usage:
        async with render_lock_ctx() as acquired:
            if acquired:
                await do_render()
    """
    lock = RenderLock()
    acquired = await lock.acquire(timeout=timeout)
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()
