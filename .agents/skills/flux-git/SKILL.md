---
name: flux-git
description: >
  Git workflow, commits, and releases for the Flux content automation app.
  Use when asked to commit, push, tag, branch, merge, or manage version control
  for the Flux project. Enforces conventional commits, atomic changes, and
  clean history.
---

# Flux Git Skill

## Branching Model

```
main
  └── phase/N-short-name   (e.g., phase/0-foundation, phase/3-render)
  └── hotfix/short-desc
```

- `main` is always deployable to Termux.
- Phase branches merge to `main` via squash merge after device validation.
- Never commit directly to `main`.

## Commit Convention

Format: `<type>: <description>`

Types:
- `feat` — new feature
- `fix` — bug fix
- `test` — adding or fixing tests
- `docs` — documentation only
- `refactor` — code change that neither fixes nor adds feature
- `chore` — tooling, deps, config
- `perf` — performance improvement

Rules:
- Subject ≤ 72 characters.
- Imperative mood: "add" not "added".
- Body explains WHY if subject isn't obvious.
- Reference issue/phase if applicable: `feat: add ffmpeg render lock (phase-3)`

Examples:
```
feat: add sqlite wal mode for concurrent reads during writes
fix: prevent duplicate posts when scheduler misfires after reboot
test: add device test for youtube upload quota tracking
refactor: extract render pipeline into plugin method
chore: bump yt-dlp to 2024.04.x
docs: update bootstrap script for termux-api dependency
```

## Pre-Commit Checklist

Before every commit:
- [ ] `pytest tests/unit/` passes.
- [ ] Audit script passes: `python .agents/skills/flux-review/scripts/audit.py`
- [ ] No secrets in diff (`git diff --cached | grep -i "token\|key\|secret"`).
- [ ] `.env` is not staged.
- [ ] Commit is atomic: one logical change, not a mixed bag.

## Commit Size Rules

- **Small:** 1–3 files, ≤200 lines. Ideal.
- **Medium:** 4–6 files, ≤500 lines. Acceptable if tightly related.
- **Large:** >6 files or >500 lines. Split into multiple commits.

## Squash Merge

When merging a phase branch to `main`:
```bash
git checkout main
git merge --squash phase/N-name
git commit -m "feat: phase N — description"
git tag v0.N.0
```

## Tagging

Tag `main` after each phase:
- `v0.1.0-phase0` — Foundation
- `v0.2.0-phase1` — Core Engine
- ...
- `v1.0.0` — First autonomous 30-day run

## Forbidden

- `git push --force` to `main`.
- Committing `.env`, `*.db`, or media files.
- Commit messages like "fix stuff" or "WIP" or "asdf".
- Mixing feature changes with unrelated refactors in one commit.
