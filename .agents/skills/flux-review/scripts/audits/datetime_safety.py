"""Datetime safety audit — detect timezone-naive datetime usage."""

from __future__ import annotations

import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


FORBIDDEN_PATTERNS = [
    (r"datetime\.now\(\)", "datetime.now()", "datetime.now(timezone.utc)"),
    (r"datetime\.today\(\)", "datetime.today()", "datetime.now(timezone.utc).date()"),
    (r"datetime\.utcnow\(\)", "datetime.utcnow()", "datetime.now(timezone.utc)"),
]

# time.time() is allowed for performance/uptime, flagged otherwise
TIME_TIME_PATTERN = r"time\.time\(\)"


class DatetimeSafetyAudit(BaseAudit):
    """Flag naive datetime usage that ignores timezones."""

    name = "datetime_safety"
    description = "Naive datetime.now(), .utcnow(), .today(), unsafe time.time()"
    file_extensions = {".py"}

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []

        for pattern, raw, replacement in FORBIDDEN_PATTERNS:
            for lineno, line in self.find_pattern(lines, pattern):
                findings.append(self.finding(
                    "WARNING", filepath, lineno,
                    f"Naive time usage: `{raw}`. Use timezone-aware: `{replacement}`.",
                    suggestion=f"Replace with `{replacement}` or use app-configured timezone.",
                ))

        # time.time() — only flag if NOT used for uptime/perf
        content_lower = content.lower()
        is_perf_context = any(kw in content_lower for kw in ("uptime", "elapsed", "_start_time"))
        if not is_perf_context:
            for lineno, line in self.find_pattern(lines, TIME_TIME_PATTERN):
                findings.append(self.finding(
                    "INFO", filepath, lineno,
                    "time.time() used outside perf/uptime context. "
                    "Consider timezone-aware datetime if this represents a wall-clock timestamp.",
                ))

        return findings
