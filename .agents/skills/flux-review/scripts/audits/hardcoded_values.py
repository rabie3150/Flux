"""Hardcoded values audit — colors, paths, secrets, magic numbers."""

from __future__ import annotations

import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


# --- Color patterns ---
COLOR_PATTERNS = [
    r"#[0-9a-fA-F]{3}\b",
    r"#[0-9a-fA-F]{6}\b",
    r"#[0-9a-fA-F]{8}\b",
    r"rgb\(\s*\d+",
    r"rgba\(\s*\d+",
    r"hsl\(\s*\d+",
]
COLOR_FILE_TYPES = {".py", ".html", ".js", ".css", ".ts", ".vue", ".jsx", ".tsx"}

# --- Hardcoded path patterns ---
PATH_PATTERNS = [
    r"/storage/emulated/",
    r"/home/[^/]+/",
    r"C:\\\\Users\\\\",
    r"C:\\\\",
]
PATH_ALLOW_FILENAMES = {"config", "bootstrap", "start", "settings"}

# --- Secret patterns ---
SECRET_PATTERNS = [
    r"(api[_-]?key|token|password|secret|client[_-]?secret)\s*=\s*[\"'][^\"']{8,}[\"']",
]
SECRET_SKIP_FILES = {".env.example", "audit.py", "runner.py"}
SECRET_PLACEHOLDER_WORDS = {"example", "your", "placeholder", "changeme", "xxx"}


class HardcodedValuesAudit(BaseAudit):
    """Detect hardcoded colors, filesystem paths, and secrets."""

    name = "hardcoded_values"
    description = "Hardcoded colors, paths, secrets"

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_colors(filepath, lines))
        findings.extend(self._check_paths(filepath, lines))
        findings.extend(self._check_secrets(filepath, lines))
        return findings

    def _check_colors(self, filepath: Path, lines: list[str]) -> list[Finding]:
        if filepath.suffix not in COLOR_FILE_TYPES:
            return []
        # Skip CSS variable definition files — that's where colors SHOULD live
        if filepath.name == "vars.css" or (filepath.name == "index.html" and "static/admin" in filepath.as_posix()):
            return []

        findings: list[Finding] = []
        for pattern in COLOR_PATTERNS:
            for lineno, line in self.find_pattern(lines, pattern):
                # Allow colors in comments that are examples
                stripped = line.strip()
                if stripped.startswith(("#", "//", "/*")) and "example" in stripped.lower():
                    continue
                # Allow CSS custom property declarations (--var: #color)
                if "--" in line and ":" in line and filepath.suffix == ".css":
                    continue
                findings.append(self.finding(
                    "WARNING", filepath, lineno,
                    "Hardcoded color detected. Move to `static/admin/css/vars.css` "
                    "or a centralized theme config.",
                ))
        return findings

    def _check_paths(self, filepath: Path, lines: list[str]) -> list[Finding]:
        # Skip the audit scripts themselves
        if filepath.name in ("audit.py", "runner.py") or "audits/" in filepath.as_posix():
            return []
        # Skip config/bootstrap files where paths are expected
        if any(kw in filepath.stem.lower() for kw in PATH_ALLOW_FILENAMES):
            return []

        findings: list[Finding] = []
        for pattern in PATH_PATTERNS:
            for lineno, line in self.find_pattern(lines, pattern):
                findings.append(self.finding(
                    "WARNING", filepath, lineno,
                    "Hardcoded path detected. Use `settings.STORAGE_PATH` or config-driven paths.",
                    suggestion="Move to .env / config.py and reference via settings.",
                ))
        return findings

    def _check_secrets(self, filepath: Path, lines: list[str]) -> list[Finding]:
        if filepath.name in SECRET_SKIP_FILES:
            return []

        findings: list[Finding] = []
        for pattern in SECRET_PATTERNS:
            for lineno, line in self.find_pattern(lines, pattern, flags=re.IGNORECASE):
                line_lower = line.lower()
                if any(word in line_lower for word in SECRET_PLACEHOLDER_WORDS):
                    continue
                findings.append(self.finding(
                    "CRITICAL", filepath, lineno,
                    "Potential hardcoded secret. Move to `.env` and use `settings.XXX`.",
                    suggestion="Never commit credentials. Use environment variables.",
                ))
        return findings
