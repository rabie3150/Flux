"""Code hygiene audit — print() in production, inline styles in HTML."""

from __future__ import annotations

import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


INLINE_STYLE_PATTERN = r'style\s*=\s*["\']'
INLINE_STYLE_FILE_TYPES = {".html", ".js", ".jsx", ".tsx", ".vue"}

# Files where print() is acceptable
PRINT_ALLOW_FILES = {"audit.py", "runner.py", "bootstrap.py"}


class CodeHygieneAudit(BaseAudit):
    """Detect print() in production code and inline styles in templates."""

    name = "code_hygiene"
    description = "print() in production code, inline styles in HTML"

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_print(filepath, content, lines))
        findings.extend(self._check_inline_styles(filepath, lines))
        return findings

    def _check_print(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        if filepath.suffix != ".py":
            return []
        if filepath.name in PRINT_ALLOW_FILES:
            return []
        # Allow in audit scripts directory
        if "audits" in filepath.parts:
            return []

        findings: list[Finding] = []
        for lineno, line in self.find_pattern(lines, r"\bprint\s*\("):
            stripped = line.strip()
            # Skip commented-out prints
            if stripped.startswith("#"):
                continue
            # Allow in __main__ guard blocks
            if self.is_in_main_block(lines, lineno):
                continue
            findings.append(self.finding(
                "WARNING", filepath, lineno,
                f"print() in production code. Use `logging.getLogger(__name__)`.",
                suggestion="Replace with `logger.info(...)` or `logger.debug(...)`.",
            ))
        return findings

    def _check_inline_styles(self, filepath: Path, lines: list[str]) -> list[Finding]:
        if filepath.suffix not in INLINE_STYLE_FILE_TYPES:
            return []

        findings: list[Finding] = []
        for lineno, line in self.find_pattern(lines, INLINE_STYLE_PATTERN):
            findings.append(self.finding(
                "WARNING", filepath, lineno,
                "Inline style detected. Use CSS classes from the design system instead.",
                suggestion="Extract to a CSS class in the appropriate stylesheet.",
            ))
        return findings
