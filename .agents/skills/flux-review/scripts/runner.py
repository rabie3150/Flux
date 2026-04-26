#!/usr/bin/env python3
"""
Flux Project Audit Runner

Modular audit framework that auto-discovers audit plugins from the audits/
directory.  Each audit extends BaseAudit and implements a `check` method.

Usage:
    python runner.py                        # Run all audits
    python runner.py --audit file_structure  # Run one audit
    python runner.py --severity WARNING     # Filter by min severity
    python runner.py --json                 # Machine-readable output
"""

from __future__ import annotations

import argparse
import ast
import importlib
import importlib.util
import json
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# ============================================================================
# CONSTANTS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]
AUDITS_DIR = Path(__file__).resolve().parent / "audits"

SOURCE_EXTENSIONS = {".py", ".html", ".js", ".ts", ".jsx", ".tsx", ".vue", ".css"}
EXCLUDE_DIRS = {"venv", ".venv", "node_modules", "__pycache__", ".git", ".pytest_cache", ".ruff_cache", ".kilo", ".agents"}

SEVERITY_RANK = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}

ANSI = {
    "CRITICAL": "\033[91m",
    "WARNING":  "\033[93m",
    "INFO":     "\033[94m",
    "PASS":     "\033[92m",
    "DIM":      "\033[90m",
    "BOLD":     "\033[1m",
    "RESET":    "\033[0m",
}


# ============================================================================
# FINDING MODEL
# ============================================================================

@dataclass
class Finding:
    """Single audit finding."""

    severity: str        # CRITICAL | WARNING | INFO
    filepath: str        # Relative to project root
    line: int            # 1-indexed
    message: str         # Human-readable
    audit_name: str      # Which audit produced this
    suggestion: str = "" # Optional fix hint

    @property
    def rank(self) -> int:
        return SEVERITY_RANK.get(self.severity, 0)


# ============================================================================
# BASE AUDIT
# ============================================================================

class BaseAudit(ABC):
    """Abstract base for all audit checks.

    Subclass this and implement ``check()`` to create a new audit.
    Place the file in ``scripts/audits/`` and it will be auto-discovered.
    """

    name: str = "unnamed"
    description: str = ""
    file_extensions: set[str] = SOURCE_EXTENSIONS

    # ---- abstract ----

    @abstractmethod
    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        """Run the audit on a single file.

        Args:
            filepath: Absolute path to the file.
            content:  Full file text.
            lines:    Pre-split lines (no trailing newline).

        Returns:
            List of findings (may be empty).
        """

    # ---- helpers available to all audits ----

    def finding(
        self,
        severity: str,
        filepath: Path,
        line: int,
        message: str,
        suggestion: str = "",
    ) -> Finding:
        """Convenience factory that fills in ``audit_name`` automatically."""
        rel = _relative_path(filepath)
        return Finding(
            severity=severity,
            filepath=rel,
            line=line,
            message=message,
            audit_name=self.name,
            suggestion=suggestion,
        )

    def find_pattern(
        self,
        lines: list[str],
        pattern: str,
        *,
        flags: int = 0,
    ) -> list[tuple[int, str]]:
        """Return ``[(lineno, line_text), ...]`` for every line matching *pattern*."""
        compiled = re.compile(pattern, flags)
        return [(i, line) for i, line in enumerate(lines, 1) if compiled.search(line)]

    @staticmethod
    def parse_ast(content: str) -> ast.Module | None:
        """Parse Python source to AST, return None on syntax error."""
        try:
            return ast.parse(content)
        except SyntaxError:
            return None

    def applies_to(self, filepath: Path) -> bool:
        """Return True if this audit should run on *filepath*."""
        return filepath.suffix in self.file_extensions

    @staticmethod
    def is_in_main_block(lines: list[str], lineno: int, lookback: int = 10) -> bool:
        """Check if *lineno* (1-indexed) sits inside an ``if __name__`` block."""
        start = max(0, lineno - lookback - 1)
        for line in lines[start:lineno - 1]:
            if "if __name__" in line:
                return True
        return False


# ============================================================================
# FILE COLLECTION
# ============================================================================

def collect_source_files() -> list[Path]:
    """Return all source files under PROJECT_ROOT, excluding vendored dirs."""
    files: list[Path] = []
    for ext in SOURCE_EXTENSIONS:
        files.extend(PROJECT_ROOT.rglob(f"*{ext}"))
    return [
        f for f in files
        if not any(part in EXCLUDE_DIRS for part in f.parts)
    ]


# ============================================================================
# AUDIT DISCOVERY
# ============================================================================

def discover_audits() -> list[BaseAudit]:
    """Import every module in audits/ and instantiate all BaseAudit subclasses."""
    instances: list[BaseAudit] = []
    if not AUDITS_DIR.is_dir():
        return instances

    # Ensure audit plugins can `from runner import BaseAudit, Finding`
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    # Register this module so `import runner` resolves inside submodules
    sys.modules.setdefault("runner", sys.modules[__name__])

    for py_file in sorted(AUDITS_DIR.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        module_name = f"audits.{py_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            print(f"  {ANSI['WARNING']}[WARN]{ANSI['RESET']} Failed to load audit {py_file.name}: {exc}")
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseAudit)
                and attr is not BaseAudit
            ):
                instances.append(attr())

    return instances


# ============================================================================
# REPORTING
# ============================================================================

def _relative_path(filepath: Path) -> str:
    """Return path relative to PROJECT_ROOT as posix string."""
    try:
        return filepath.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(filepath)


def print_report(findings: list[Finding], *, file_count: int, audit_names: list[str]) -> None:
    """Pretty-print the audit report with ANSI colors."""
    r = ANSI["RESET"]

    print(f"\n{'=' * 70}")
    print(f" {ANSI['BOLD']}FLUX PROJECT AUDIT{r}")
    print(f" Root:    {PROJECT_ROOT}")
    print(f" Files:   {file_count}")
    print(f" Audits:  {', '.join(audit_names)}")
    print(f"{'=' * 70}")

    if not findings:
        print(f"\n  {ANSI['PASS']}[PASS] All checks passed.{r}\n")
        return

    # Group by file
    by_file: dict[str, list[Finding]] = {}
    for f in findings:
        by_file.setdefault(f.filepath, []).append(f)

    for fpath in sorted(by_file):
        print(f"\n{ANSI['BOLD']}{fpath}{r}")
        print(f"{ANSI['DIM']}{'-' * len(fpath)}{r}")
        for f in sorted(by_file[fpath], key=lambda x: x.line):
            color = ANSI.get(f.severity, r)
            print(f"  {color}[{f.severity}]{r} L{f.line}: {f.message}")
            if f.suggestion:
                print(f"           {ANSI['DIM']}-> {f.suggestion}{r}")

    # Summary
    crit = sum(1 for f in findings if f.severity == "CRITICAL")
    warn = sum(1 for f in findings if f.severity == "WARNING")
    info = sum(1 for f in findings if f.severity == "INFO")

    print(f"\n{'=' * 70}")
    print(f" {ANSI['BOLD']}SUMMARY{r}")
    print(f"{'=' * 70}")
    cc = ANSI["CRITICAL"] if crit else r
    wc = ANSI["WARNING"] if warn else r
    print(f"  {cc}Critical: {crit}{r}")
    print(f"  {wc}Warnings: {warn}{r}")
    print(f"  Info:     {info}")

    if crit > 0:
        print(f"\n  {ANSI['CRITICAL']}[BLOCK] Fix {crit} critical issue(s) before committing.{r}")
        print(f"\n  Fix order:")
        print(f"    1. Fix all CRITICAL findings (secrets, broken markers, leaked creds).")
        print(f"    2. Fix WARNING findings (file size, naive datetime, hardcoded values).")
        print(f"    3. Re-run: python .agents/skills/flux-review/scripts/runner.py")
    elif warn > 0:
        print(f"\n  {ANSI['WARNING']}[WARN] {warn} warning(s) found. Recommended to fix before commit.{r}")

    print()


def print_json(findings: list[Finding], *, file_count: int, audit_names: list[str]) -> None:
    """Print machine-readable JSON report."""
    crit = sum(1 for f in findings if f.severity == "CRITICAL")
    report = {
        "root": str(PROJECT_ROOT),
        "files_scanned": file_count,
        "audits": audit_names,
        "summary": {
            "critical": crit,
            "warnings": sum(1 for f in findings if f.severity == "WARNING"),
            "info": sum(1 for f in findings if f.severity == "INFO"),
        },
        "verdict": "BLOCK" if crit > 0 else "PASS",
        "findings": [asdict(f) for f in findings],
    }
    print(json.dumps(report, indent=2))


# ============================================================================
# MAIN
# ============================================================================

def run_audit(argv: Sequence[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Flux Project Audit Runner")
    parser.add_argument("--audit", action="append", default=[], help="Run only named audit(s). Repeatable.")
    parser.add_argument("--severity", default="INFO", choices=["INFO", "WARNING", "CRITICAL"], help="Minimum severity to report.")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON.")
    parser.add_argument("--fix-suggestions", action="store_true", help="Include fix suggestions in output.")
    args = parser.parse_args(argv)

    min_rank = SEVERITY_RANK[args.severity]

    # Discover audits
    all_audits = discover_audits()
    if not all_audits:
        print("ERROR: No audits discovered. Check audits/ directory.")
        return 1

    # Filter by name if requested
    if args.audit:
        selected = [a for a in all_audits if a.name in args.audit]
        unknown = set(args.audit) - {a.name for a in all_audits}
        if unknown:
            print(f"ERROR: Unknown audit(s): {', '.join(unknown)}")
            print(f"Available: {', '.join(a.name for a in all_audits)}")
            return 1
        audits = selected
    else:
        audits = all_audits

    # Collect files
    files = collect_source_files()

    # Run audits
    findings: list[Finding] = []
    for filepath in sorted(files):
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        file_lines = content.splitlines()

        for audit in audits:
            if not audit.applies_to(filepath):
                continue
            try:
                results = audit.check(filepath, content, file_lines)
                for f in results:
                    if 0 < f.line <= len(file_lines):
                        line_text = file_lines[f.line - 1].lower()
                        prev_text = file_lines[f.line - 2].lower() if f.line > 1 else ""
                        
                        # Check for global skip or specific skip
                        skip_global = "audit: skip" in line_text or "audit: skip" in prev_text
                        skip_specific = f"audit: skip {audit.name}" in line_text or f"audit: skip {audit.name}" in prev_text
                        
                        if skip_global or skip_specific:
                            continue
                    findings.append(f)
            except Exception as exc:  # noqa: BLE001
                findings.append(Finding(
                    severity="WARNING",
                    filepath=_relative_path(filepath),
                    line=0,
                    message=f"Audit '{audit.name}' crashed: {exc}",
                    audit_name=audit.name,
                ))

    # Filter by severity
    findings = [f for f in findings if f.rank >= min_rank]

    # Strip suggestions unless requested
    if not args.fix_suggestions:
        for f in findings:
            f.suggestion = ""

    # Report
    audit_names = [a.name for a in audits]
    if args.json_output:
        print_json(findings, file_count=len(files), audit_names=audit_names)
    else:
        print_report(findings, file_count=len(files), audit_names=audit_names)

    # Exit code
    has_critical = any(f.severity == "CRITICAL" for f in findings)
    return 1 if has_critical else 0


if __name__ == "__main__":
    sys.exit(run_audit())
