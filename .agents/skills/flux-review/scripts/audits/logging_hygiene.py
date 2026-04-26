"""Logging hygiene audit — proper logger usage, log_activity, logger.py self-check."""

from __future__ import annotations

import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import BaseAudit, Finding  # noqa: E402


class LoggingHygieneAudit(BaseAudit):
    """Enforce structured logging patterns across the codebase."""

    name = "logging_hygiene"
    description = "Logger usage, direct logging calls, log_activity, logger.py self-check"
    file_extensions = {".py"}

    def check(self, filepath: Path, content: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        rel = filepath.relative_to(filepath.parents[len(filepath.parts) - 2]).as_posix()

        findings.extend(self._check_direct_logging(filepath, lines))
        findings.extend(self._check_file_should_log(filepath, content))
        findings.extend(self._check_log_activity_usage(filepath, content))

        # Special deep checks for specific files
        if filepath.name == "logger.py":
            findings.extend(self._check_logger_py(filepath, content))
        if filepath.name == "main.py":
            findings.extend(self._check_main_py(filepath, content))

        return findings

    def _check_direct_logging(self, filepath: Path, lines: list[str]) -> list[Finding]:
        """Direct `logging.info()` etc. should use a logger instance instead."""
        findings: list[Finding] = []
        pattern = r"\blogging\.(info|warning|error|debug|critical)\("
        for lineno, line in self.find_pattern(lines, pattern):
            findings.append(self.finding(
                "WARNING", filepath, lineno,
                f"Direct `logging.*()` call. Use a logger instance: "
                f"`logger = get_logger(__name__)`.",
                suggestion="Replace `logging.info(...)` with `logger.info(...)`.",
            ))
        return findings

    def _check_file_should_log(self, filepath: Path, content: str) -> list[Finding]:
        """API and core service files should import get_logger."""
        findings: list[Finding] = []
        path_str = filepath.as_posix()
        is_service_file = "api/" in path_str or "core/" in path_str
        if is_service_file and "def " in content and "get_logger" not in content:
            findings.append(self.finding(
                "WARNING", filepath, 1,
                "Service/API file has functions but no `get_logger` import. "
                "Production code should use structured logging.",
                suggestion="Add `from flux.logger import get_logger` and "
                           "`logger = get_logger(__name__)` at module level.",
            ))
        return findings

    def _check_log_activity_usage(self, filepath: Path, content: str) -> list[Finding]:
        """API and core files should use log_activity for audit trails."""
        findings: list[Finding] = []
        path_str = filepath.as_posix()
        is_service_file = "api/" in path_str or "core/" in path_str
        
        # Whitelist files that are purely utility/internal and don't need audit trails
        whitelist = {"lock.py", "crypto.py", "__init__.py", "system.py"}
        if filepath.name in whitelist:
            return findings

        if is_service_file and content.count("log_activity(") == 0:
            findings.append(self.finding(
                "INFO", filepath, 1,
                "No `log_activity()` calls. Consider adding audit-trail logging "
                "for user-facing operations.",
            ))
        return findings

    def _check_logger_py(self, filepath: Path, content: str) -> list[Finding]:
        """Deep self-check of the project's logger.py for robustness issues."""
        findings: list[Finding] = []

        # Redaction coverage
        required_redaction_patterns = [
            "password", "secret", "authorization", "cookie",
            "session", "refresh_token", "access_token",
        ]
        content_lower = content.lower()
        for pattern_name in required_redaction_patterns:
            if pattern_name not in content_lower:
                findings.append(self.finding(
                    "WARNING", filepath, 1,
                    f"Redaction pattern missing: `{pattern_name}`. "
                    f"Sensitive data may leak in logs.",
                ))

        # Exception traceback redaction
        if "formatException" in content:
            after_format = content.split("formatException")[1][:200]
            if "_redact" not in after_format:
                findings.append(self.finding(
                    "CRITICAL", filepath, 1,
                    "Exception tracebacks in JsonFormatter are NOT redacted — "
                    "tokens may leak in stack traces.",
                ))

        # log_activity metadata param actually used
        if "def log_activity(" in content:
            func_start = content.find("def log_activity(")
            func_end = content.find("\ndef ", func_start + 1)
            if func_end == -1:
                func_end = len(content)
            func_body = content[func_start:func_end]
            if "metadata" in func_body and func_body.count("metadata") <= 1:
                findings.append(self.finding(
                    "CRITICAL", filepath, 1,
                    "`log_activity()` accepts 'metadata' parameter but never uses it. "
                    "Audit trail data is silently dropped.",
                ))

        # setup_logging disk error handling
        if "setup_logging" in content:
            setup_start = content.find("def setup_logging")
            setup_end = content.find("\ndef ", setup_start + 1)
            if setup_end == -1:
                setup_end = len(content)
            setup_body = content[setup_start:setup_end]
            if "RotatingFileHandler" in setup_body and "try" not in setup_body:
                findings.append(self.finding(
                    "WARNING", filepath, 1,
                    "`setup_logging()` has no try/except around file handler setup — "
                    "crashes on unwritable log directory.",
                ))

        # warn -> warning normalization
        if "log_method = getattr(logger, level.lower()" in content:
            findings.append(self.finding(
                "WARNING", filepath, 1,
                "`log_activity()` uses `level.lower()` directly — 'warn' "
                "falls back to info instead of mapping to 'warning'.",
            ))

        return findings

    def _check_main_py(self, filepath: Path, content: str) -> list[Finding]:
        """Check main.py for startup/shutdown logging completeness."""
        findings: list[Finding] = []
        if "logger.info" in content and "logger.error" not in content:
            findings.append(self.finding(
                "INFO", filepath, 1,
                "main.py has info logs but no error logs in lifespan — "
                "initialization failures will be silent.",
            ))
        return findings
