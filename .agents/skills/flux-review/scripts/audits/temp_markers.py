"""Temporary code markers audit — TODO, FIXME, HACK, TEMP, XXX, etc."""

from __future__ import annotations

import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


# Markers and their severity
CRITICAL_MARKERS = {"BROKEN", "DEBUGME"}
WARNING_MARKERS = {"TODO", "FIXME", "HACK", "TEMP", "XXX"}
ALL_MARKERS = CRITICAL_MARKERS | WARNING_MARKERS


class TempMarkersAudit(BaseAudit):
    """Detect temporary code markers that should be resolved before commit."""

    name = "temp_markers"
    description = "TODO, FIXME, HACK, TEMP, XXX, BROKEN, DEBUGME markers"

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []

        for marker in ALL_MARKERS:
            # Match in comments: # ..., // ..., /* ...
            pattern = rf"#.*\b{marker}\b|//.*\b{marker}\b|/\*.*\b{marker}\b"
            for lineno, line in self.find_pattern(lines, pattern, flags=re.IGNORECASE):
                severity = "CRITICAL" if marker in CRITICAL_MARKERS else "WARNING"
                findings.append(self.finding(
                    severity, filepath, lineno,
                    f"Temporary marker '{marker}' found. "
                    f"Remove or convert to tracked issue.",
                    suggestion="Create a GitHub issue and reference it, or resolve the TODO now.",
                ))

        return findings
