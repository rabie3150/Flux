"""File structure audit — file size and function/class size limits."""

from __future__ import annotations

import ast
from pathlib import Path

# Import from parent package via relative path hack (runner adds to sys.path)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


MAX_FILE_LINES = 800
MAX_FUNCTION_LINES = 100


class FileStructureAudit(BaseAudit):
    """Flag oversized files and functions that need refactoring."""

    name = "file_structure"
    description = "Files >800 lines, functions/classes >100 lines"

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []

        # --- File size ---
        if len(lines) > MAX_FILE_LINES:
            findings.append(self.finding(
                "WARNING", filepath, 1,
                f"File has {len(lines)} lines (max {MAX_FILE_LINES}). "
                f"Refactor: extract classes/functions into separate modules.",
                suggestion=f"Split into 2-3 focused modules of ~{len(lines) // 3} lines each.",
            ))

        # --- Function / class size (Python only) ---
        if filepath.suffix == ".py":
            tree = self.parse_ast(content)
            if tree:
                self._check_node_sizes(filepath, tree, findings)

        return findings

    def _check_node_sizes(
        self, filepath: Path, tree: ast.Module, findings: list[Finding],
    ) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            body_lines = (node.end_lineno - node.lineno + 1) if node.end_lineno else 0
            if body_lines > MAX_FUNCTION_LINES:
                kind = "Class" if isinstance(node, ast.ClassDef) else "Function"
                findings.append(self.finding(
                    "WARNING", filepath, node.lineno,
                    f"{kind} '{node.name}' is {body_lines} lines (max {MAX_FUNCTION_LINES}). "
                    f"Refactor: extract helper functions or split class.",
                    suggestion=f"Break into smaller methods — aim for <50 lines each.",
                ))
