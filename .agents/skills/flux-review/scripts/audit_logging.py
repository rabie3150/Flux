"""Flux logging audit script.

Checks:
- print() in production code
- Bare except: without logging
- Files that should log but don't (APIs, services)
- Error paths without logger.error / logger.exception
- Direct logging.* calls (should use logger instance)
- log_activity usage
- logger.py self-check (redaction coverage, exception handling)
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FLUX_DIR = PROJECT_ROOT / "flux"

CRITICAL = 3
WARNING = 2
INFO = 1

findings: list[tuple[int, str, str, int, str]] = []


def add(level: int, file: str, line: int, msg: str) -> None:
    findings.append((level, file, msg, line, ""))


def scan_file(path: Path) -> str:
    """Return file content."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def check_print_statements(content: str, rel_path: str) -> None:
    """Find print() in production code."""
    for i, line in enumerate(content.splitlines(), 1):
        if re.search(r"\bprint\(", line) and not line.strip().startswith("#"):
            add(CRITICAL, rel_path, i, f"print() found: {line.strip()}")


def check_bare_except(content: str, rel_path: str) -> None:
    """Find bare except: that doesn't log."""
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "except:" or stripped.startswith("except Exception:"):
            # Check next 3 lines for logging
            has_log = False
            for j in range(i, min(i + 5, len(lines) + 1)):
                if "logger" in lines[j - 1] or "logging" in lines[j - 1]:
                    has_log = True
                    break
            if not has_log:
                add(WARNING, rel_path, i, f"Bare except without logging: {line.strip()}")


def check_file_should_log(content: str, rel_path: str) -> None:
    """API and service files should import get_logger."""
    if "api/" in rel_path or "core/" in rel_path:
        if "def " in content and "get_logger" not in content:
            add(WARNING, rel_path, 1, f"File has functions but no get_logger import: {rel_path}")


def check_error_paths(content: str, rel_path: str) -> None:
    """HTTPException and error returns should have logger calls."""
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        if "HTTPException" in line and "status_code" in line:
            # Check preceding 5 lines for logger
            has_log = False
            for j in range(max(1, i - 5), i):
                if "logger" in lines[j - 1]:
                    has_log = True
                    break
            if not has_log:
                add(WARNING, rel_path, i, f"HTTPException without preceding logger call")


def check_direct_logging_calls(content: str, rel_path: str) -> None:
    """Direct logging.info() etc. should use logger instance."""
    for i, line in enumerate(content.splitlines(), 1):
        if re.search(r"\blogging\.(info|warning|error|debug|critical)\(", line):
            add(WARNING, rel_path, i, f"Direct logging.* call, use logger instance: {line.strip()}")


def check_log_activity_usage(content: str, rel_path: str) -> None:
    """Count log_activity calls."""
    count = content.count("log_activity(")
    if count == 0 and ("api/" in rel_path or "core/" in rel_path):
        add(INFO, rel_path, 1, f"No log_activity calls in {rel_path}")


def check_logger_py(content: str, rel_path: str) -> None:
    """Self-check logger.py for robustness issues."""
    # Check redaction patterns coverage
    patterns_found = {
        "password": False,
        "secret": False,
        "authorization": False,
        "cookie": False,
        "session": False,
        "refresh_token": False,
        "access_token": False,
    }
    for pattern_name in patterns_found:
        if pattern_name in content.lower():
            patterns_found[pattern_name] = True

    for name, found in patterns_found.items():
        if not found:
            add(WARNING, rel_path, 1, f"Redaction pattern missing: {name}")

    # Check if exception tracebacks are redacted
    if "formatException" in content and "_redact" not in content.split("formatException")[1][:200]:
        add(CRITICAL, rel_path, 1, "Exception tracebacks in JsonFormatter are NOT redacted — tokens may leak in stack traces")

    # Check if metadata param in log_activity is used
    if "def log_activity(" in content:
        func_start = content.find("def log_activity(")
        func_end = content.find("\ndef ", func_start + 1)
        if func_end == -1:
            func_end = len(content)
        func_body = content[func_start:func_end]
        if "metadata" in func_body and func_body.count("metadata") <= 1:
            # metadata only appears in signature, not body
            add(CRITICAL, rel_path, 1, "log_activity() accepts 'metadata' parameter but never uses it")

    # Check setup_logging for disk error handling
    if "setup_logging" in content:
        setup_start = content.find("def setup_logging")
        setup_end = content.find("\ndef ", setup_start + 1)
        if setup_end == -1:
            setup_end = len(content)
        setup_body = content[setup_start:setup_end]
        if "RotatingFileHandler" in setup_body and "try" not in setup_body:
            add(WARNING, rel_path, 1, "setup_logging() has no try/except around file handler setup — crashes on unwritable log dir")

    # Check for warn -> warning normalization
    if "log_method = getattr(logger, level.lower()" in content:
        add(WARNING, rel_path, 1, "log_activity() uses level.lower() directly — 'warn' falls back to info instead of mapping to 'warning'")


def check_main_py(content: str, rel_path: str) -> None:
    """Check main.py for startup/shutdown logging completeness."""
    if "logger.info" in content and "logger.error" not in content:
        add(INFO, rel_path, 1, "main.py has info logs but no error logs in lifespan — init failures silent")


def main() -> int:
    print("=" * 70)
    print(" FLUX LOGGING AUDIT")
    print("=" * 70)

    if not FLUX_DIR.exists():
        print(f"ERROR: flux/ directory not found at {FLUX_DIR}")
        return 1

    py_files = list(FLUX_DIR.rglob("*.py"))
    for py_file in py_files:
        rel = py_file.relative_to(PROJECT_ROOT).as_posix()
        content = scan_file(py_file)

        check_print_statements(content, rel)
        check_bare_except(content, rel)
        check_file_should_log(content, rel)
        check_error_paths(content, rel)
        check_direct_logging_calls(content, rel)
        check_log_activity_usage(content, rel)

        if rel == "flux/logger.py":
            check_logger_py(content, rel)
        if rel == "flux/main.py":
            check_main_py(content, rel)

    critical = [f for f in findings if f[0] == CRITICAL]
    warnings = [f for f in findings if f[0] == WARNING]
    infos = [f for f in findings if f[0] == INFO]

    for level, file, msg, line, _ in critical:
        print(f"\n  [CRITICAL] {file}:{line}")
        print(f"    {msg}")

    for level, file, msg, line, _ in warnings:
        print(f"\n  [WARNING] {file}:{line}")
        print(f"    {msg}")

    for level, file, msg, line, _ in infos:
        print(f"\n  [INFO] {file}:{line}")
        print(f"    {msg}")

    print("\n" + "=" * 70)
    print(f"  Critical: {len(critical)}")
    print(f"  Warnings: {len(warnings)}")
    print(f"  Info:     {len(infos)}")
    print("=" * 70)

    if critical:
        print("\n  [BLOCK] Critical findings must be fixed before next phase.")
        return 1
    if warnings:
        print("\n  [WARN] Warnings found. Recommended to fix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
