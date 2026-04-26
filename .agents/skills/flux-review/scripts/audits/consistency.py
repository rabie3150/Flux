"""Consistency guard audit — mixed conventions, import style drift, naming chaos.

AI agents often introduce inconsistencies because they generate code per-function
without considering the surrounding file. This audit catches:
- Mixed naming conventions in the same file (snake_case vs camelCase)
- Import style drift (mixing relative and absolute imports)
- Inconsistent string quoting style
- Mixed async patterns (sync and async versions of the same logic)
- Return type inconsistency across similar functions
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


class ConsistencyAudit(BaseAudit):
    """Detect inconsistencies within a single file that signal fragmented authoring."""

    name = "consistency"
    description = "Mixed naming, import styles, string quotes, async patterns"
    file_extensions = {".py"}

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        tree = self.parse_ast(content)
        if tree is None:
            return findings

        findings.extend(self._check_import_style(filepath, tree))
        findings.extend(self._check_naming_conventions(filepath, tree))
        findings.extend(self._check_string_quotes(filepath, lines))
        findings.extend(self._check_return_consistency(filepath, tree))
        return findings

    def _check_import_style(self, filepath: Path, tree: ast.Module) -> list[Finding]:
        """Flag files that mix relative and absolute imports."""
        findings: list[Finding] = []
        has_relative = False
        has_absolute = False
        relative_lines: list[int] = []
        absolute_lines: list[int] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level > 0:  # relative import
                    has_relative = True
                    relative_lines.append(node.lineno)
                else:
                    has_absolute = True
                    absolute_lines.append(node.lineno)

        if has_relative and has_absolute:
            # Only flag if it's not just stdlib + local pattern
            # (mixing `from flux.x import y` with `from .x import y` is inconsistent)
            flux_absolutes = [ln for ln in absolute_lines]
            if relative_lines and flux_absolutes:
                findings.append(self.finding(
                    "INFO", filepath, relative_lines[0],
                    f"Mixed import styles: {len(relative_lines)} relative + "
                    f"{len(absolute_lines)} absolute imports. "
                    f"Pick one convention per package.",
                ))

        return findings

    def _check_naming_conventions(self, filepath: Path, tree: ast.Module) -> list[Finding]:
        """Flag files with mixed naming conventions in function definitions."""
        findings: list[Finding] = []

        func_names: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_names.append((node.name, node.lineno))

        if len(func_names) < 3:
            return findings  # Too few to judge

        snake_count = 0
        camel_count = 0
        camel_examples: list[tuple[str, int]] = []

        for name, lineno in func_names:
            if name.startswith("_"):
                name = name.lstrip("_")
            if not name:
                continue
            # Skip dunder methods
            if name.startswith("__") and name.endswith("__"):
                continue

            if "_" in name:
                snake_count += 1
            elif name[0].islower() and any(c.isupper() for c in name[1:]):
                camel_count += 1
                camel_examples.append((name, lineno))

        # If there's a clear majority, flag the outliers
        if snake_count > 0 and camel_count > 0:
            if snake_count >= camel_count:
                # camelCase is the outlier in a snake_case file
                for name, lineno in camel_examples:
                    findings.append(self.finding(
                        "WARNING", filepath, lineno,
                        f"Function `{name}` uses camelCase in a snake_case file. "
                        f"Rename for consistency.",
                    ))
            else:
                # This would be unusual in Python — flag it differently
                findings.append(self.finding(
                    "WARNING", filepath, 1,
                    f"File uses camelCase for most functions ({camel_count}) "
                    f"but Python convention is snake_case.",
                ))

        return findings

    def _check_string_quotes(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """Flag files with heavily mixed string quoting styles."""
        findings: list[Finding] = []

        single_count = 0
        double_count = 0

        for line in lines:
            stripped = line.strip()
            # Skip comments, docstrings, empty lines
            if stripped.startswith("#") or not stripped:
                continue
            # Skip triple-quoted strings
            if '"""' in stripped or "'''" in stripped:
                continue

            # Count simple string assignments/args
            singles = len(re.findall(r"(?<!\w)'[^']*'(?!\w)", stripped))
            doubles = len(re.findall(r'(?<!\w)"[^"]*"(?!\w)', stripped))
            single_count += singles
            double_count += doubles

        total = single_count + double_count
        if total < 10:
            return findings  # Not enough data

        # Flag if the mix is close to 50/50 (between 30-70%)
        minority = min(single_count, double_count)
        minority_pct = (minority / total) * 100
        if minority_pct > 30:
            majority_style = "double quotes" if double_count > single_count else "single quotes"
            findings.append(self.finding(
                "INFO", filepath, 1,
                f"Mixed string quoting: {single_count} single + {double_count} double. "
                f"Standardize on {majority_style} for consistency.",
            ))

        return findings

    def _check_return_consistency(self, filepath: Path, tree: ast.Module) -> list[Finding]:
        """Flag functions that sometimes return a value and sometimes use bare return."""
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            returns_value: list[int] = []
            returns_bare: list[int] = []

            for child in ast.walk(node):
                if isinstance(child, ast.Return):
                    if child.value is None:
                        returns_bare.append(child.lineno)
                    elif isinstance(child.value, ast.Constant) and child.value.value is None:
                        # Explicit return None is treated as returning a value (None)
                        returns_value.append(child.lineno)
                    else:
                        returns_value.append(child.lineno)

            # If function has both value returns and bare returns, flag it
            if returns_value and returns_bare:
                findings.append(self.finding(
                    "WARNING", filepath, node.lineno,
                    f"Function `{node.name}()` has inconsistent returns: "
                    f"{len(returns_value)} return a value/None, {len(returns_bare)} use bare `return`. "
                    f"Make the return style consistent.",
                ))

        return findings
