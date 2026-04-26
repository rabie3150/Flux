---
name: flux-review
description: >
  Review code, plans, and changes in the Flux content automation app.
  Use when asked to review, audit, inspect, check, or verify code, diffs,
  pull requests, architecture decisions, or implementation plans.
  Runs automated audits and enforces project-specific quality gates.
---

# Flux Review Skill

## Automated Audit (Run First)

Before any manual review, run the audit runner:

```bash
python .agents/skills/flux-review/scripts/runner.py
```

### CLI Options

| Flag | Description |
|------|-------------|
| `--audit NAME` | Run only named audit(s). Repeatable. |
| `--severity WARNING` | Minimum severity to display (INFO / WARNING / CRITICAL). |
| `--json` | Machine-readable JSON output for CI. |
| `--fix-suggestions` | Include fix suggestions in output. |

### Available Audits

| Audit | File | What It Checks |
|-------|------|----------------|
| `file_structure` | `audits/file_structure.py` | Files >800 lines, functions/classes >100 lines |
| `temp_markers` | `audits/temp_markers.py` | TODO, FIXME, HACK, TEMP, XXX, BROKEN, DEBUGME |
| `datetime_safety` | `audits/datetime_safety.py` | Naive datetime.now(), .utcnow(), .today(), time.time() |
| `hardcoded_values` | `audits/hardcoded_values.py` | Hardcoded colors, paths, secrets |
| `code_hygiene` | `audits/code_hygiene.py` | print() in production code, inline styles in HTML |
| `error_handling` | `audits/error_handling.py` | Bare except, except/pass, HTTPException without logging, missing backoff |
| `logging_hygiene` | `audits/logging_hygiene.py` | Direct logging calls, missing get_logger, logger.py self-check |
| `ai_slop` | `audits/ai_slop.py` | Generic names, over-commenting, empty bodies, lazy docstrings |
| `consistency` | `audits/consistency.py` | Mixed naming, import styles, string quotes, async patterns |
| `dead_code` | `audits/dead_code.py` | Unused imports, unreachable code, never-read variables |
| `duplication` | `audits/duplication.py` | Near-duplicate code blocks (>5 lines) within a file |
| `api_contract` | `audits/api_contract.py` | Response models, status codes, missing docstrings |

### Adding New Audits

Create a new `.py` file in `scripts/audits/`. Extend `BaseAudit`:

```python
from runner import BaseAudit, Finding

class MyNewAudit(BaseAudit):
    name = "my_new_audit"
    description = "What this audit checks"
    file_extensions = {".py"}  # optional filter

    def check(self, filepath, content, lines):
        findings = []
        # ... your checks ...
        return findings
```

It will be auto-discovered by the runner — no registration needed.

**If audit reports CRITICAL findings, review stops until fixed.**

## Review Checklist

### 1. Consistency
- [ ] New code follows patterns from existing similar files.
- [ ] Naming matches project conventions (snake_case, PascalCase, etc.).
- [ ] No reinvented utilities — existing helpers reused.

### 2. File Size
- [ ] No file exceeds 800 lines.
- [ ] No function/class exceeds 100 lines.
- [ ] If refactored, old code properly removed (no dead code).

### 3. Temporary Code
- [ ] No unmarked temporary code.
- [ ] All `# TEMP:` and `# FIXME:` markers have GitHub issues or are resolved.
- [ ] No `_temp_` prefixed functions left in production.

### 4. Hardcoded Values
- [ ] No hex colors outside `vars.css`.
- [ ] No filesystem paths outside config/bootstrap.
- [ ] No API keys, tokens, or secrets in source.
- [ ] No magic numbers without named constants.

### 5. Time & Timezones
- [ ] No `datetime.now()`, `datetime.utcnow()`, `datetime.today()`.
- [ ] All datetime operations use timezone-aware objects.
- [ ] Cron schedules respect app timezone setting.

### 6. Error Handling
- [ ] No bare `except:` or `except Exception: pass`.
- [ ] Specific exception types caught.
- [ ] Errors logged with context, not swallowed.
- [ ] Retry logic uses exponential backoff, not infinite loops.

### 7. Tests
- [ ] Unit tests for pure logic.
- [ ] Integration tests for DB + API flows.
- [ ] Device tests marked with `@pytest.mark.device` if Termux-specific.
- [ ] No tests that always pass (mock returns success → test proves nothing).

### 8. Documentation
- [ ] `.env.example` updated if new settings.
- [ ] Conception docs updated if architecture changed.
- [ ] Inline comments explain "why", not "what".

## Review Verdict

```
APPROVE    → All checks pass, audit clean.
CHANGES    → Warnings exist but no critical. Author can merge after fixing.
BLOCK      → Critical findings or audit failures. Must fix before merge.
```

## Plan Review

For architecture/plan reviews (not code diffs):
- Check against conception docs: does plan contradict PRD or ADRs?
- Verify feasibility: does it assume a library feature that doesn't exist?
- Check layer correctness: fix root cause, not symptom.
- Check scope: does it change 8 files when 1–2 would suffice?
