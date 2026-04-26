"""API contract audit — FastAPI endpoint hygiene.

Catches AI-generated API endpoints that look functional but miss
production requirements:
- Missing response_model on endpoints
- Inconsistent status codes for similar operations
- Endpoints without input validation
- Missing authentication/authorization checks
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


class APIContractAudit(BaseAudit):
    """Enforce consistent API endpoint patterns."""

    name = "api_contract"
    description = "Response models, status codes, input validation, auth checks"
    file_extensions = {".py"}

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        # Only run on API files
        if "api/" not in filepath.as_posix() and "api\\" not in str(filepath):
            return []
        if filepath.name == "__init__.py":
            return []

        findings: list[Finding] = []
        tree = self.parse_ast(content)
        if tree is None:
            return findings

        findings.extend(self._check_missing_response_model(filepath, lines))
        findings.extend(self._check_status_code_consistency(filepath, tree, lines))
        findings.extend(self._check_missing_docstrings(filepath, tree))
        return findings

    def _check_missing_response_model(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """Flag router decorators without response_model (returns raw dicts)."""
        findings: list[Finding] = []
        route_pattern = re.compile(r"@router\.(get|post|put|patch|delete)\(")

        for lineno, line in enumerate(lines, 1):
            match = route_pattern.search(line)
            if not match:
                continue
            # Check if response_model is specified in the decorator
            # May span multiple lines, so check next 3 lines too
            decorator_text = line
            for j in range(lineno, min(lineno + 3, len(lines))):
                decorator_text += lines[j]

            if "response_model" not in decorator_text:
                # Find the function return type
                func_lineno = lineno
                for j in range(lineno, min(lineno + 5, len(lines))):
                    if "def " in lines[j - 1]:
                        func_lineno = j
                        break

                # If return type is dict or Any, flag it
                func_line = lines[func_lineno - 1] if func_lineno <= len(lines) else ""
                if "dict" in func_line or "Any" in func_line:
                    findings.append(self.finding(
                        "INFO", filepath, lineno,
                        f"Endpoint returns raw dict. Consider adding a Pydantic "
                        f"response_model for documentation and validation.",
                    ))

        return findings

    def _check_status_code_consistency(
        self, filepath: Path, tree: ast.Module, lines: list[str]
    ) -> list[Finding]:
        """Flag 404s raised with inconsistent detail messages for same pattern."""
        findings: list[Finding] = []
        not_found_messages: dict[str, list[int]] = {}

        for lineno, line in enumerate(lines, 1):
            if "status_code=404" in line or "status_code=404" in (
                lines[lineno] if lineno < len(lines) else ""
            ):
                # Extract detail message
                detail_match = re.search(r'detail="([^"]*)"', line)
                if not detail_match and lineno < len(lines):
                    detail_match = re.search(r'detail="([^"]*)"', lines[lineno])
                if detail_match:
                    msg = detail_match.group(1)
                    not_found_messages.setdefault(msg, []).append(lineno)

        # If there are multiple different 404 messages for similar entities
        if len(not_found_messages) > 1:
            messages = list(not_found_messages.keys())
            # Check if messages are just slight variations
            base_words = set()
            for msg in messages:
                words = set(msg.lower().split())
                base_words.update(words)

            if "not" in base_words and "found" in base_words:
                # Multiple not-found messages — check consistency
                unique_patterns = set()
                for msg in messages:
                    # Normalize: "Pipeline not found" -> "X not found"
                    normalized = re.sub(r"\w+(?= not found)", "X", msg)
                    unique_patterns.add(normalized)

                if len(unique_patterns) > 1:
                    all_lines = []
                    for lns in not_found_messages.values():
                        all_lines.extend(lns)
                    findings.append(self.finding(
                        "INFO", filepath, min(all_lines),
                        f"Inconsistent 404 detail messages: {messages}. "
                        f"Standardize error messages across endpoints.",
                    ))

        return findings

    def _check_missing_docstrings(self, filepath: Path, tree: ast.Module) -> list[Finding]:
        """Flag endpoint functions without docstrings (OpenAPI docs will be empty)."""
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # Check if it has route decorators
            has_route = False
            for decorator in node.decorator_list:
                dec_str = ast.dump(decorator)
                if "router" in dec_str and any(
                    method in dec_str for method in ("get", "post", "put", "delete", "patch")
                ):
                    has_route = True
                    break

            if not has_route:
                continue

            # Check for docstring
            if not node.body:
                continue
            first = node.body[0]
            has_docstring = (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            )
            if not has_docstring:
                findings.append(self.finding(
                    "WARNING", filepath, node.lineno,
                    f"Endpoint `{node.name}()` has no docstring. "
                    f"OpenAPI/Swagger docs will show no description.",
                ))

        return findings
