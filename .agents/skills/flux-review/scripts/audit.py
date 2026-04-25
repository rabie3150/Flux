#!/usr/bin/env python3
"""
Flux Project Audit Runner
Scans the codebase for consistency issues, temporary code, hardcoded values,
and forbidden patterns. Run after the test suite and before every commit.

Usage:
    python audit.py [--fix-suggestions]
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]  # Up from .agents/skills/flux-review/scripts/
MAX_FILE_LINES = 800
MAX_FUNCTION_LINES = 100
TEMP_MARKERS = ["TODO", "FIXME", "HACK", "TEMP", "XXX", "BROKEN", "DEBUGME"]
TIMEZONE_FORBIDDEN = [
    r"datetime\.now\(\)",
    r"datetime\.today\(\)",
    r"datetime\.utcnow\(\)",
    r"time\.time\(\)",
]
COLOR_PATTERNS = [
    r"#[0-9a-fA-F]{3}\b",
    r"#[0-9a-fA-F]{6}\b",
    r"#[0-9a-fA-F]{8}\b",
    r"rgb\(\s*\d+",
    r"rgba\(\s*\d+",
    r"hsl\(\s*\d+",
]
SECRET_PATTERNS = [
    r"(api[_-]?key|token|password|secret|client[_-]?secret)\s*=\s*[\"'][^\"']{8,}[\"']",
]
HARDCODED_PATH_PATTERNS = [
    r"/storage/emulated/",
    r"/home/[^/]+/",
    r"C:\\\\Users\\\\",
    r"C:\\\\",
]
INLINE_STYLE_PATTERN = r'style\s*=\s*["\']'

SEVERITY = {
    "CRITICAL": "\033[91m",   # Red
    "WARNING": "\033[93m",    # Yellow
    "INFO": "\033[94m",       # Blue
    "PASS": "\033[92m",       # Green
    "RESET": "\033[0m",
}


# ============================================================================
# AUDIT CHECKS
# ============================================================================

def check_file_size(filepath: Path) -> List[Tuple[str, int, str]]:
    """Flag files exceeding MAX_FILE_LINES."""
    findings = []
    lines = filepath.read_text(encoding="utf-8").splitlines()
    if len(lines) > MAX_FILE_LINES:
        findings.append((
            "WARNING",
            1,
            f"File has {len(lines)} lines (max {MAX_FILE_LINES}). "
            f"Refactor: extract classes/functions into separate modules.",
        ))
    return findings


def check_function_sizes(filepath: Path) -> List[Tuple[str, int, str]]:
    """Flag functions/classes exceeding MAX_FUNCTION_LINES."""
    findings = []
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body_lines = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
            if body_lines > MAX_FUNCTION_LINES:
                findings.append((
                    "WARNING",
                    node.lineno,
                    f"'{node.name}' is {body_lines} lines (max {MAX_FUNCTION_LINES}). "
                    f"Refactor: extract helper functions or split class.",
                ))
    return findings


def check_temp_markers(filepath: Path) -> List[Tuple[str, int, str]]:
    """Detect temporary code markers."""
    findings = []
    text = filepath.read_text(encoding="utf-8")
    for marker in TEMP_MARKERS:
        pattern = rf"#.*\b{marker}\b|//.*\b{marker}\b|/\*.*\b{marker}\b"
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(pattern, line, re.IGNORECASE):
                findings.append((
                    "CRITICAL" if marker in ("BROKEN", "DEBUGME") else "WARNING",
                    lineno,
                    f"Temporary marker '{marker}' found. Remove or convert to tracked issue.",
                ))
    return findings


def check_timezone_issues(filepath: Path) -> List[Tuple[str, int, str]]:
    """Detect naive datetime usage."""
    findings = []
    text = filepath.read_text(encoding="utf-8")
    for pattern in TIMEZONE_FORBIDDEN:
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(pattern, line):
                # Allow time.time() for uptime/performance calculations
                if "time.time()" in line and ("uptime" in text.lower() or "_START_TIME" in text or "elapsed" in text.lower()):
                    continue
                findings.append((
                    "WARNING",
                    lineno,
                    f"Naive time usage: '{pattern}'. Use timezone-aware datetime: "
                    f"`datetime.now(timezone.utc)` or app-configured timezone.",
                ))
    return findings


def check_hardcoded_colors(filepath: Path) -> List[Tuple[str, int, str]]:
    """Detect hardcoded colors in Python/HTML/JS files."""
    findings = []
    if filepath.suffix not in (".py", ".html", ".js", ".css", ".ts", ".vue", ".jsx", ".tsx"):
        return findings
    text = filepath.read_text(encoding="utf-8")
    for pattern in COLOR_PATTERNS:
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(pattern, line):
                # Allow colors in comments if they are examples
                if line.strip().startswith("#") and "Example" in line:
                    continue
                findings.append((
                    "WARNING",
                    lineno,
                    f"Hardcoded color detected. Move to `static/admin/css/vars.css` "
                    f"or a centralized theme config.",
                ))
    return findings


def check_hardcoded_paths(filepath: Path) -> List[Tuple[str, int, str]]:
    """Detect hardcoded filesystem paths."""
    findings = []
    # Skip the audit script itself (it defines path regex patterns)
    if filepath.name == "audit.py":
        return findings
    text = filepath.read_text(encoding="utf-8")
    for pattern in HARDCODED_PATH_PATTERNS:
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(pattern, line):
                # Allow paths in config files and bootstrap scripts
                if "config" in filepath.name or "bootstrap" in filepath.name or "start" in filepath.name:
                    continue
                findings.append((
                    "WARNING",
                    lineno,
                    f"Hardcoded path detected. Use `settings.STORAGE_PATH` or config-driven paths.",
                ))
    return findings


def check_secrets(filepath: Path) -> List[Tuple[str, int, str]]:
    """Detect potential hardcoded secrets."""
    findings = []
    if filepath.name in (".env.example", "audit.py"):
        return findings
    text = filepath.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(pattern, line, re.IGNORECASE):
                # Allow example placeholders
                if "example" in line.lower() or "your" in line.lower() or "placeholder" in line.lower():
                    continue
                findings.append((
                    "CRITICAL",
                    lineno,
                    f"Potential hardcoded secret. Move to `.env` and use `settings.XXX`.",
                ))
    return findings


def check_inline_styles(filepath: Path) -> List[Tuple[str, int, str]]:
    """Detect inline style attributes in HTML templates."""
    findings = []
    if filepath.suffix not in (".html", ".js", ".jsx", ".tsx", ".vue"):
        return findings
    text = filepath.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.search(INLINE_STYLE_PATTERN, line):
            findings.append((
                "WARNING",
                lineno,
                f"Inline style detected. Use CSS classes from the design system instead.",
            ))
    return findings


def check_print_statements(filepath: Path) -> List[Tuple[str, int, str]]:
    """Detect print() in production code."""
    findings = []
    if filepath.name in ("audit.py", "bootstrap.py"):
        return findings
    text = filepath.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.search(r"\bprint\s*\(", line):
            # Allow prints in __main__ blocks
            if 'if __name__' in text.splitlines()[max(0, lineno-5):lineno]:
                continue
            findings.append((
                "WARNING",
                lineno,
                f"print() in production code. Use `logging.getLogger(__name__)`.",
            ))
    return findings


# ============================================================================
# MAIN RUNNER
# ============================================================================

def get_source_files() -> List[Path]:
    """Collect all source files to audit."""
    files = []
    for ext in (".py", ".html", ".js", ".ts", ".jsx", ".tsx", ".vue", ".css"):
        files.extend(PROJECT_ROOT.rglob(f"*{ext}"))
    # Exclude venv, node_modules, __pycache__, .git
    exclude = {"venv", ".venv", "node_modules", "__pycache__", ".git", ".pytest_cache"}
    return [
        f for f in files
        if not any(part in exclude for part in f.parts)
    ]


def run_audit() -> int:
    parser = argparse.ArgumentParser(description="Flux Project Audit")
    parser.add_argument("--fix-suggestions", action="store_true", help="Print fix steps")
    args = parser.parse_args()

    files = get_source_files()
    total_critical = 0
    total_warning = 0
    total_info = 0

    print(f"\n{'='*70}")
    print(f" FLUX PROJECT AUDIT")
    print(f" Root: {PROJECT_ROOT}")
    print(f" Files scanned: {len(files)}")
    print(f"{'='*70}\n")

    for filepath in sorted(files):
        rel = filepath.relative_to(PROJECT_ROOT)
        findings = []
        findings.extend(check_file_size(filepath))
        findings.extend(check_function_sizes(filepath))
        findings.extend(check_temp_markers(filepath))
        findings.extend(check_timezone_issues(filepath))
        findings.extend(check_hardcoded_colors(filepath))
        findings.extend(check_hardcoded_paths(filepath))
        findings.extend(check_secrets(filepath))
        findings.extend(check_inline_styles(filepath))
        findings.extend(check_print_statements(filepath))

        if not findings:
            continue

        print(f"\n{rel}")
        print("-" * len(str(rel)))
        for severity, lineno, message in findings:
            color = SEVERITY.get(severity, SEVERITY["RESET"])
            reset = SEVERITY["RESET"]
            print(f"  {color}[{severity}]{reset} L{lineno}: {message}")
            if severity == "CRITICAL":
                total_critical += 1
            elif severity == "WARNING":
                total_warning += 1
            else:
                total_info += 1

    print(f"\n{'='*70}")
    print(" SUMMARY")
    print(f"{'='*70}")
    c_color = SEVERITY["CRITICAL"] if total_critical else SEVERITY["RESET"]
    w_color = SEVERITY["WARNING"] if total_warning else SEVERITY["RESET"]
    r = SEVERITY["RESET"]
    print(f"  {c_color}Critical: {total_critical}{r}")
    print(f"  {w_color}Warnings: {total_warning}{r}")
    print(f"  Info:     {total_info}")

    if total_critical == 0 and total_warning == 0:
        print(f"\n  {SEVERITY['PASS']}[PASS] All checks passed.{SEVERITY['RESET']}")
        return 0

    if total_critical > 0:
        print(f"\n  {SEVERITY['CRITICAL']}[BLOCK] Fix {total_critical} critical issue(s) before committing.{SEVERITY['RESET']}")
        print("\n  Fix order:")
        print("    1. Fix all CRITICAL findings (secrets, temp markers, broken code).")
        print("    2. Fix WARNING findings (file size, naive datetime, hardcoded values).")
        print("    3. Re-run: python .agents/skills/flux-review/scripts/audit.py")
        return 1

    print(f"\n  {SEVERITY['WARNING']}[WARN] {total_warning} warning(s) found. Recommended to fix before commit.{SEVERITY['RESET']}")
    return 0 if total_critical == 0 else 1


if __name__ == "__main__":
    sys.exit(run_audit())
