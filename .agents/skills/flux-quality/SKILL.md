---
name: flux-quality
description: >
  Code quality, linting, and refactoring standards for the Flux app.
  Use when asked to lint, refactor, clean up, improve quality, or run code
  quality checks. Ensures the codebase stays maintainable as it grows.
---

# Flux Quality Skill

## Quality Gates

Run these checks after tests and before every commit:

### 1. Audit Script
```bash
python .agents/skills/flux-review/scripts/audit.py
```
Must pass with zero critical findings.

### 2. Ruff Lint
```bash
ruff check flux/ tests/ --select E,W,F,I,N,UP,B,C4,SIM
```
Fix all errors. Warnings are advisory.

### 3. Import Sorting
```bash
ruff check flux/ tests/ --select I --fix
```
Standard library → third-party → first-party (flux).

### 4. Type Hints
- All public functions must have type hints.
- `async def` return types required.
- Use `Optional[X]` or `X | None` (Python 3.10+).
- Avoid `Any` unless truly unavoidable.

### 5. Docstrings
- Public modules: module-level docstring.
- Public classes: class docstring.
- Public functions: args + return documented if non-obvious.
- Private functions (`_prefix`): docstring optional but encouraged.

## Refactoring Triggers

Refactor when any of these are true:

| Trigger | Action |
|---------|--------|
| File >800 lines | Extract module or split class |
| Function >100 lines | Extract helper functions |
| Class >300 lines | Split into composed objects |
| Duplicate code (3+ occurrences) | Extract shared utility |
| Deep nesting (>4 levels) | Extract early returns or helpers |
| Mixed abstraction levels | Separate orchestration from detail |

## Refactoring Safety Rules

1. **Never refactor and change behavior in the same commit.**
2. **Always have tests covering the code before refactoring.**
3. **Refactor in small steps:** extract method → test → extract class → test.
4. **If tests fail after refactor, revert and try smaller steps.**

## Dead Code Detection

Remove:
- Unused imports (ruff catches these).
- Unused variables (prefix with `_` if intentional).
- Commented-out code older than 1 commit.
- Functions with no callers (verify with grep).

## Performance Checks

- Database queries: use `EXPLAIN` if slow. Add indexes if filtering large tables.
- N+1 queries: use `selectinload` or `joinedload` in SQLAlchemy.
- Memory: don't load entire tables into memory. Use pagination.
- FFmpeg: reuse filtergraphs where possible. Avoid subprocess spam.

## Post-Quality Checklist

- [ ] Audit script passes.
- [ ] Ruff passes with no errors.
- [ ] All tests pass.
- [ ] No dead code.
- [ ] No performance regressions (check render times if applicable).
- [ ] Git diff reviewed: only intended changes staged.
- [ ] no temporary debug code left in (print statements, etc).