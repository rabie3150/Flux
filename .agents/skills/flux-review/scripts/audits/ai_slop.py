"""AI slop detection audit — catch lazy AI-generated code patterns.

Targets the most common failure modes of AI coding assistants:
- Generic/meaningless variable names
- Over-commented obvious code (comment restates the code)
- Boilerplate abstractions that add indirection without value
- Single-letter variables outside tight loops
- Functions that do nothing (empty or pass-only bodies)
- Redundant type comments when type hints exist
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


# Variable names that are too generic and signal lazy AI code
GENERIC_NAMES = {
    "data", "result", "results", "response", "res", "ret",
    "value", "values", "val", "vals",
    "item", "items", "element", "elements", "elem",
    "obj", "object", "thing", "stuff",
    "temp", "tmp", "foo", "bar", "baz",
    "info", "output", "input",
    "handle", "process", "do_stuff", "handle_stuff",
    "my_var", "my_list", "my_dict", "my_func",
    "x", "y", "z", "a", "b", "c", "d",
}

# Names that are fine in specific contexts (don't flag these)
CONTEXT_ALLOWED = {
    # Loop variables
    "i", "j", "k", "n", "x", "y", "z",
    # Common short names in comprehensions
    "v", "k", "f", "e", "p", "w", "r",
}

# Patterns for comments that just restate the code
OBVIOUS_COMMENT_PATTERNS = [
    # "# Import X" above an import
    (r"^\s*#\s*[Ii]mport", r"^\s*(from|import)\s"),
    # "# Set X to Y" or "# Initialize X"
    (r"^\s*#\s*(Set|Initialize|Init|Create|Define|Declare)\s", None),
    # "# Return X"
    (r"^\s*#\s*[Rr]eturn\s", r"^\s*return\s"),
    # "# Loop through/over X" or "# Iterate over X"
    (r"^\s*#\s*(Loop|Iterate)\s+(through|over)", r"^\s*for\s"),
    # "# Check if X"
    (r"^\s*#\s*[Cc]heck\s+if\s", r"^\s*if\s"),
    # "# Increment X" or "# Decrement X"
    (r"^\s*#\s*(Increment|Decrement)\s", None),
    # "# Call X" or "# Calling X"
    (r"^\s*#\s*[Cc]all(ing)?\s", None),
    # "# Get X from Y" or "# Fetch X"
    (r"^\s*#\s*(Get|Fetch|Retrieve)\s+the\s", None),
    # "# Print X"
    (r"^\s*#\s*[Pp]rint\s", r"^\s*print\("),
]

# Docstrings that are just restating the function name
LAZY_DOCSTRING_PATTERNS = [
    r"^This (function|method|class) (does|performs|handles|processes|is used to)\s",
    r"^(Handle|Process|Do|Perform|Execute|Run)\s+\w+\.?$",
    r"^A? ?(simple|basic|helper|utility) (function|method|class)\s",
]


class AISlopAudit(BaseAudit):
    """Detect patterns of lazy AI-generated code that add noise without value."""

    name = "ai_slop"
    description = "Generic names, over-commenting, boilerplate abstractions, empty bodies"
    file_extensions = {".py"}

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_generic_names(filepath, content))
        findings.extend(self._check_obvious_comments(filepath, lines))
        findings.extend(self._check_empty_bodies(filepath, content))
        findings.extend(self._check_lazy_docstrings(filepath, content))
        findings.extend(self._check_redundant_type_comments(filepath, lines))
        return findings

    def _check_generic_names(self, filepath: Path, content: str) -> list[Finding]:
        """Flag top-level functions/variables with meaninglessly generic names."""
        findings: list[Finding] = []
        tree = self.parse_ast(content)
        if tree is None:
            return findings

        for node in ast.iter_child_nodes(tree):
            # Top-level function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name_lower = node.name.lower()
                if name_lower in GENERIC_NAMES:
                    findings.append(self.finding(
                        "WARNING", filepath, node.lineno,
                        f"Generic function name `{node.name}`. "
                        f"What does it actually do? Use a descriptive name.",
                    ))
                # Check for unused parameters (defined but never referenced in body)
                findings.extend(self._check_unused_params(filepath, node, content))

            # Top-level assignments
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.lower() in GENERIC_NAMES:
                        # Allow in test files
                        if "test" in filepath.stem:
                            continue
                        findings.append(self.finding(
                            "INFO", filepath, node.lineno,
                            f"Generic variable name `{target.id}`. Consider a more "
                            f"descriptive name that explains what this holds.",
                        ))

        return findings

    def _check_unused_params(
        self, filepath: Path, func_node: ast.FunctionDef | ast.AsyncFunctionDef, content: str
    ) -> list[Finding]:
        """Flag function parameters that are never used in the function body."""
        findings: list[Finding] = []

        # Get all parameter names
        param_names: set[str] = set()
        for arg in func_node.args.args:
            if arg.arg not in ("self", "cls"):
                param_names.add(arg.arg)
        for arg in func_node.args.kwonlyargs:
            param_names.add(arg.arg)

        if not param_names:
            return findings

        # Get all Name nodes referenced in the function body
        referenced: set[str] = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Name):
                referenced.add(node.id)

        # Subtract param definitions from references (params appear as Name nodes too)
        # A param is "used" if it appears as a Name load in the body
        unused = param_names - referenced
        # Also check string references (e.g., **kwargs forwarding, getattr)
        func_source = ast.get_source_segment(content, func_node) or ""
        unused = {p for p in unused if p not in func_source}

        for param in sorted(unused):
            # Skip common callback/protocol params
            if param.startswith("_") or param in ("args", "kwargs"):
                continue
            findings.append(self.finding(
                "WARNING", filepath, func_node.lineno,
                f"Parameter `{param}` in `{func_node.name}()` is never used. "
                f"Dead parameter — remove it or prefix with `_` if intentional.",
            ))

        return findings

    def _check_obvious_comments(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """Flag comments that just restate what the next line of code does."""
        findings: list[Finding] = []

        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped.startswith("#") or stripped == "#":
                continue
            # Skip shebangs, encoding declarations, type: ignore
            if stripped.startswith("#!") or "coding:" in stripped or "type:" in stripped:
                continue
            # Skip section dividers
            if stripped.startswith("# ---") or stripped.startswith("# ==="):
                continue

            # Check each obvious pattern
            next_line = lines[lineno] if lineno < len(lines) else ""
            for comment_pattern, code_pattern in OBVIOUS_COMMENT_PATTERNS:
                if re.search(comment_pattern, stripped):
                    if code_pattern is None or re.search(code_pattern, next_line):
                        findings.append(self.finding(
                            "INFO", filepath, lineno,
                            f"Comment restates the code: `{stripped[:60]}...`. "
                            f"Comments should explain *why*, not *what*.",
                        ))
                    break

        return findings

    def _check_empty_bodies(self, filepath: Path, content: str) -> list[Finding]:
        """Flag functions with empty bodies (just pass or ...) that aren't ABCs."""
        findings: list[Finding] = []
        tree = self.parse_ast(content)
        if tree is None:
            return findings

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            body = node.body
            # Skip if it has a docstring + pass/ellipsis (protocol/ABC pattern)
            real_stmts = [
                s for s in body
                if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
            ]

            if len(real_stmts) == 0:
                # Only has docstring — fine for ABCs/protocols
                continue
            if len(real_stmts) == 1:
                stmt = real_stmts[0]
                is_pass = isinstance(stmt, ast.Pass)
                is_ellipsis = (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is ...
                )
                if is_pass or is_ellipsis:
                    # Check if it's an abstract method or protocol
                    decorators = [
                        d for d in node.decorator_list
                        if (isinstance(d, ast.Name) and d.id == "abstractmethod")
                        or (isinstance(d, ast.Attribute) and d.attr == "abstractmethod")
                    ]
                    if decorators:
                        continue  # ABC pattern, totally fine

                    # Check if parent is a class with ABC/Protocol base
                    # (We can't easily determine this from walking, so skip
                    # functions inside classes named *Base or *Protocol)
                    findings.append(self.finding(
                        "WARNING", filepath, node.lineno,
                        f"Function `{node.name}()` has an empty body (pass/...). "
                        f"Is this a stub that was never implemented?",
                    ))

        return findings

    def _check_lazy_docstrings(self, filepath: Path, content: str) -> list[Finding]:
        """Flag docstrings that just restate the function name."""
        findings: list[Finding] = []
        tree = self.parse_ast(content)
        if tree is None:
            return findings

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if not node.body:
                continue

            first = node.body[0]
            if not isinstance(first, ast.Expr):
                continue
            if not isinstance(first.value, ast.Constant) or not isinstance(first.value.value, str):
                continue

            docstring = first.value.value.strip().split("\n")[0]  # First line only
            for pattern in LAZY_DOCSTRING_PATTERNS:
                if re.match(pattern, docstring, re.IGNORECASE):
                    findings.append(self.finding(
                        "INFO", filepath, first.lineno,
                        f"Lazy docstring: `{docstring[:50]}...`. "
                        f"Describe the *purpose* and *behavior*, not just the existence.",
                    ))
                    break

        return findings

    def _check_redundant_type_comments(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """Flag `# type: X` comments when proper type hints exist on the same line."""
        findings: list[Finding] = []
        for lineno, line in enumerate(lines, 1):
            # Has a type comment
            if "# type:" not in line or "# type: ignore" in line:
                continue
            # Also has a type annotation
            if ": " in line.split("#")[0] and "=" in line:
                findings.append(self.finding(
                    "INFO", filepath, lineno,
                    "Redundant `# type:` comment — line already has type annotations. "
                    "Remove the comment.",
                ))
        return findings
