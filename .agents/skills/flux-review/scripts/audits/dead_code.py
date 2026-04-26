"""Dead code audit — unused imports, unreachable code, never-called functions."""

from __future__ import annotations

import ast
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402

IMPLICIT_IMPORTS = {"annotations", "TYPE_CHECKING", "Base", "Optional", "Any"}
SIDE_EFFECT_MODULES = {"flux.plugins", "flux.models"}


class DeadCodeAudit(BaseAudit):
    """Detect dead code that should be cleaned up."""

    name = "dead_code"
    description = "Unused imports, unreachable code, never-read variables"
    file_extensions = {".py"}

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        tree = self.parse_ast(content)
        if tree is None:
            return findings
        findings.extend(self._check_unused_imports(filepath, tree, content))
        findings.extend(self._check_unreachable_code(filepath, tree))
        return findings

    def _check_unused_imports(self, filepath: Path, tree: ast.Module, content: str) -> list[Finding]:
        """Flag imports never referenced in the file body."""
        findings: list[Finding] = []
        if filepath.name == "__init__.py" or "test" in filepath.stem:
            return findings

        imported: list[tuple[str, int, str]] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    imported.append((name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "__future__":
                    continue
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported.append((name, node.lineno, f"{module}.{name}"))

        all_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                all_names.add(node.id)
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                all_names.add(node.value.id)

        for name, lineno, full in imported:
            if name in IMPLICIT_IMPORTS:
                continue
            if any(mod in full for mod in SIDE_EFFECT_MODULES):
                continue
            if name in all_names:
                continue
            if f'"{name}"' in content or f"'{name}'" in content:
                continue
            findings.append(self.finding(
                "WARNING", filepath, lineno,
                f"Import `{name}` (from `{full}`) appears unused. Remove or move to TYPE_CHECKING.",
            ))
        return findings

    def _check_unreachable_code(self, filepath: Path, tree: ast.Module) -> list[Finding]:
        """Flag code after unconditional return, raise, break, or continue."""
        findings: list[Finding] = []
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for i, stmt in enumerate(body):
                if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                    if i < len(body) - 1:
                        nxt = body[i + 1]
                        if isinstance(nxt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            continue
                        findings.append(self.finding(
                            "WARNING", filepath, nxt.lineno,
                            f"Unreachable code after `{type(stmt).__name__.lower()}` on L{stmt.lineno}.",
                        ))
                        break
        return findings
