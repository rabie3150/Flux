"""Error handling audit — bare except, swallowed errors, missing logging on error paths."""

from __future__ import annotations

import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


class ErrorHandlingAudit(BaseAudit):
    """Detect poor error handling patterns that hide bugs."""

    name = "error_handling"
    description = "Bare except, swallowed errors, error paths without logging"
    file_extensions = {".py"}

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_bare_except(filepath, lines))
        findings.extend(self._check_except_pass(filepath, lines))
        findings.extend(self._check_error_paths(filepath, lines))
        findings.extend(self._check_retry_without_backoff(filepath, content, lines))
        findings.extend(self._check_log_error_return_success(filepath, lines))
        return findings

    def _check_bare_except(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """Find bare `except:` or `except Exception:` without logging."""
        findings: list[Finding] = []
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped != "except:" and not stripped.startswith("except Exception:"):
                continue
            # Look ahead up to 5 lines for logging
            has_log = False
            for j in range(lineno, min(lineno + 5, len(lines))):
                if "logger" in lines[j] or "logging" in lines[j]:
                    has_log = True
                    break
            if not has_log:
                severity = "CRITICAL" if stripped == "except:" else "WARNING"
                findings.append(self.finding(
                    severity, filepath, lineno,
                    f"Bare except without logging: `{stripped}`. "
                    f"Errors are silently swallowed.",
                    suggestion="Catch specific exceptions and log with `logger.exception(...)`.",
                ))
        return findings

    def _check_except_pass(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """Find `except ...: pass` — the classic error swallower."""
        findings: list[Finding] = []
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped.startswith("except"):
                continue
            # Check if next non-empty line is just `pass`
            for j in range(lineno, min(lineno + 3, len(lines))):
                next_stripped = lines[j].strip()
                if not next_stripped:
                    continue
                if next_stripped == "pass":
                    findings.append(self.finding(
                        "CRITICAL", filepath, lineno,
                        "except/pass pattern detected — errors are completely silenced.",
                        suggestion="At minimum: `logger.exception('Context about what failed')`.",
                    ))
                break
        return findings

    def _check_error_paths(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """HTTPException raises should have preceding logger calls."""
        findings: list[Finding] = []
        for lineno, line in enumerate(lines, 1):
            if "HTTPException" not in line or "status_code" not in line:
                continue
            # Look back 5 lines for logger
            has_log = False
            start = max(0, lineno - 6)
            for j in range(start, lineno - 1):
                if "logger" in lines[j]:
                    has_log = True
                    break
            if not has_log:
                findings.append(self.finding(
                    "WARNING", filepath, lineno,
                    "HTTPException raised without preceding logger call. "
                    "Error context will be lost in production.",
                    suggestion="Add `logger.warning(...)` or `logger.error(...)` before the raise.",
                ))
        return findings

    def _check_retry_without_backoff(
        self, filepath: Path, content: str, lines: list[str]
    ) -> list[Finding]:
        """Flag retry loops that don't use exponential backoff."""
        findings: list[Finding] = []
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            # Look for `while True` or `for _ in range(` retry patterns
            is_retry = False
            if stripped == "while True:" and "retry" in content[max(0, lineno-5):].lower()[:200]:
                is_retry = True
            if re.search(r"for\s+_\s+in\s+range\(", stripped) and "retry" in stripped.lower():
                is_retry = True
            if re.search(r"for\s+attempt\s+in\s+range\(", stripped):
                is_retry = True

            if not is_retry:
                continue

            # Check next 20 lines for sleep with increasing delay
            block = "\n".join(lines[lineno:min(lineno + 20, len(lines))])
            has_backoff = any(kw in block for kw in (
                "backoff", "exponential", "** ", "sleep(delay", "sleep(wait",
                "*=", "**=", "<< ",
            ))
            if not has_backoff and "sleep" in block:
                findings.append(self.finding(
                    "WARNING", filepath, lineno,
                    "Retry loop with fixed sleep — use exponential backoff. "
                    "Fixed delays cause thundering herd under load.",
                    suggestion="Use `sleep(base_delay * 2 ** attempt)` or `tenacity` library.",
                ))
            elif not has_backoff and "sleep" not in block:
                findings.append(self.finding(
                    "CRITICAL", filepath, lineno,
                    "Retry loop with NO delay between attempts. "
                    "This will hammer the target service and may trigger rate limits.",
                    suggestion="Add `await asyncio.sleep(base_delay * 2 ** attempt)`.",
                ))
        return findings

    def _check_log_error_return_success(
        self, filepath: Path, lines: list[str]
    ) -> list[Finding]:
        """Flag pattern: log an error but return a success value (True, 200, etc.)."""
        findings: list[Finding] = []
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if not re.search(r"logger\.(error|exception|critical)\(", stripped):
                continue
            # Check next 3 lines for a success return
            for j in range(lineno, min(lineno + 3, len(lines))):
                next_line = lines[j].strip()
                if re.match(r"return\s+(True|200|\{\}|\[\]|None)$", next_line):
                    findings.append(self.finding(
                        "WARNING", filepath, lineno,
                        f"Logged error but returning success value (`{next_line}`). "
                        f"The caller won't know something went wrong.",
                        suggestion="Raise an exception or return an error indicator.",
                    ))
                    break
        return findings

