"""Logging and FFmpeg utilities."""

from __future__ import annotations

import asyncio
import logging
import sys
from collections import deque
from pathlib import Path
from typing import Any


# Thread-safe log buffer for TUI consumption
_log_buffer: deque[str] = deque(maxlen=500)


class TUILogHandler(logging.Handler):
    """Captures log records to a thread-safe deque for the TUI to display."""

    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(logging.Formatter("%(levelname)-8s | %(name)s | %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            _log_buffer.append(msg)
        except Exception:
            pass


def get_log_buffer() -> deque[str]:
    """Return the thread-safe log buffer deque."""
    return _log_buffer


def clear_log_buffer() -> None:
    _log_buffer.clear()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)

        # Also capture to TUI buffer
        logger.addHandler(TUILogHandler())
    logger.setLevel(logging.INFO)
    return logger


async def run_ffmpeg(
    *args: str,
    timeout: float = 300.0,
    on_stderr: Any = None,
) -> tuple[int, str, str]:
    """Run FFmpeg. Returns (returncode, stdout, stderr).

    Args:
        on_stderr: Optional callback(line: str) invoked for each stderr line.
    """
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + list(args)
    logger = get_logger("ffmpeg")
    logger.debug("cmd: %s", " ".join(cmd))

    proc = None
    try:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            logger.error("FFmpeg not found in PATH")
            return -1, "", "FFmpeg not found in PATH"

        async def _read_stdout() -> bytes:
            return await proc.stdout.read()

        async def _read_stderr() -> list[str]:
            """Read stderr, splitting on \r or \n for live progress lines."""
            lines: list[str] = []
            buffer = b""
            while True:
                try:
                    chunk = await asyncio.wait_for(proc.stderr.read(2048), timeout=2.0)
                except asyncio.TimeoutError:
                    if proc.returncode is not None:
                        break
                    continue
                if not chunk:
                    break
                buffer += chunk
                # FFmpeg -stats uses \r; errors use \n
                while b"\r" in buffer or b"\n" in buffer:
                    # Find earliest delimiter
                    r_pos = buffer.find(b"\r")
                    n_pos = buffer.find(b"\n")
                    if r_pos == -1:
                        pos = n_pos
                        delim = b"\n"
                    elif n_pos == -1:
                        pos = r_pos
                        delim = b"\r"
                    else:
                        pos = min(r_pos, n_pos)
                        delim = b"\r" if r_pos < n_pos else b"\n"
                    line = buffer[:pos].decode("utf-8", errors="replace")
                    buffer = buffer[pos + len(delim):]
                    if line.strip():
                        lines.append(line + "\n")
                        if on_stderr:
                            on_stderr(line.strip())
            # Flush remaining
            if buffer:
                line = buffer.decode("utf-8", errors="replace").strip()
                if line:
                    lines.append(line + "\n")
                    if on_stderr:
                        on_stderr(line)
            return lines

        try:
            stdout_data, stderr_lines = await asyncio.wait_for(
                asyncio.gather(_read_stdout(), _read_stderr()),
                timeout=timeout,
            )
            stdout = stdout_data.decode("utf-8", errors="replace")
            stderr = "".join(stderr_lines)

            # Wait for the process to actually terminate so returncode is populated
            await proc.wait()

            return (
                proc.returncode or 0,
                stdout,
                stderr,
            )
        except asyncio.TimeoutError:
            logger.error("FFmpeg timed out after %.0fs", timeout)
            return -1, "", f"FFmpeg timed out after {timeout}s"
    finally:
        if proc and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass


async def extract_thumbnail(
    video_path: str,
    output_path: str,
    *,
    time_sec: float = 2.0,
    width: int = 1080,
    height: int = 1920,
) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    args = [
        "-ss",
        str(time_sec),
        "-i",
        video_path,
        "-vframes",
        "1",
        "-q:v",
        "2",
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        output_path,
    ]
    code, _stdout, stderr = await run_ffmpeg(*args)
    if code != 0:
        raise RuntimeError(f"Thumbnail extraction failed: {stderr[:500]}")
    if not Path(output_path).exists():
        raise RuntimeError(f"Thumbnail missing: {output_path}")
    return output_path
