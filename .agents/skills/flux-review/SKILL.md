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

Before any manual review, run the audit script:

```bash
python .agents/skills/flux-review/scripts/audit.py
```

This scans for:
- Files >800 lines
- Functions/classes >100 lines
- Temporary code markers (TODO, FIXME, HACK, TEMP, XXX)
- Naive datetime usage (`datetime.now()` without timezone)
- Hardcoded colors, paths, secrets
- Inline styles in HTML
- `print()` in production code

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
