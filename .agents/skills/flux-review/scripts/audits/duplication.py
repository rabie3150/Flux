"""Duplication audit — detect copy-paste drift and repeated code blocks.

AI agents frequently duplicate logic across files instead of extracting
shared utilities. This catches near-identical code blocks.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402

MIN_BLOCK_SIZE = 7  # Minimum lines to consider a duplicate block
SIMILARITY_THRESHOLD = 0.8  # 80% similarity = flag


class DuplicationAudit(BaseAudit):
    """Detect duplicated code blocks within a single file."""

    name = "duplication"
    description = "Near-duplicate code blocks (>5 lines) within a file"
    file_extensions = {".py"}

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        if "test" in filepath.stem or "tests" in filepath.parts:
            return []
        findings: list[Finding] = []
        findings.extend(self._check_duplicate_blocks(filepath, lines))
        findings.extend(self._check_duplicate_except_handlers(filepath, lines))
        return findings

    def _normalize_line(self, line: str) -> str:
        """Normalize a line for comparison — strip whitespace and variable names."""
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return ""
        # Normalize string literals
        stripped = re.sub(r'"[^"]*"', '""', stripped)
        stripped = re.sub(r"'[^']*'", "''", stripped)
        return stripped

    def _check_duplicate_blocks(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """Find repeated blocks of non-empty lines within the same file."""
        findings: list[Finding] = []
        
        # Build list of (lineno, normalized_content) skipping empty/comment lines
        valid_lines = []
        for i, line in enumerate(lines, 1):
            norm = self._normalize_line(line)
            if norm:
                valid_lines.append((i, norm))

        if len(valid_lines) < MIN_BLOCK_SIZE:
            return findings

        # Sliding window: hash blocks of MIN_BLOCK_SIZE lines
        block_hashes: dict[str, list[int]] = {}
        for i in range(len(valid_lines) - MIN_BLOCK_SIZE + 1):
            block_content = "\n".join(item[1] for item in valid_lines[i:i + MIN_BLOCK_SIZE])
            h = hashlib.md5(block_content.encode()).hexdigest()
            # Store the original line number of the start of the block
            block_hashes.setdefault(h, []).append(valid_lines[i][0])

        for h, locations in block_hashes.items():
            if len(locations) <= 1:
                continue
            # Only flag first occurrence to reduce noise
            findings.append(self.finding(
                "WARNING", filepath, locations[0],
                f"Duplicate {MIN_BLOCK_SIZE}-line block appears {len(locations)} times "
                f"(lines {', '.join(str(l) for l in locations)}). "
                f"Extract into a shared helper function.",
            ))

        return findings

    def _check_duplicate_except_handlers(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """Flag multiple except blocks with identical bodies (common AI pattern)."""
        findings: list[Finding] = []
        except_blocks: dict[str, list[int]] = {}

        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith("except"):
                # Collect the except block body
                body_lines: list[str] = []
                j = i + 1
                if j < len(lines):
                    indent = len(lines[j]) - len(lines[j].lstrip()) if lines[j].strip() else 0
                    while j < len(lines):
                        line = lines[j]
                        if not line.strip():
                            j += 1
                            continue
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent < indent:
                            break
                        body_lines.append(self._normalize_line(line))
                        j += 1

                if body_lines:
                    body_hash = hashlib.md5("\n".join(body_lines).encode()).hexdigest()
                    except_blocks.setdefault(body_hash, []).append(i + 1)
            i += 1

        for h, locations in except_blocks.items():
            if len(locations) <= 1:
                continue
            findings.append(self.finding(
                "INFO", filepath, locations[0],
                f"Identical except-handler body repeated {len(locations)} times "
                f"(lines {', '.join(str(l) for l in locations)}). "
                f"Extract error handling into a shared function.",
            ))

        return findings
