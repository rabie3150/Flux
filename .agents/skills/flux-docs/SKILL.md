---
name: flux-docs
description: >
  Update and maintain documentation for the Flux content automation app.
  Use AFTER building, implementing, updating, or fixing any system, phase,
  feature, function, or component. Ensures living docs stay accurate and
  stale docs are detected. Never write system docs before the code exists.
---

# Flux Documentation Skill

## When to Use This Skill

Trigger AFTER any of these events:
- A phase is completed and merged to `main`
- A new system is implemented (backend, frontend, database, etc.)
- A new feature or function is added
- An important bug fix changes behavior
- Configuration or API changes
- Plugin architecture changes

**Never write docs before code.** Docs written against imagination become lies.

## Post-Implementation Doc Update Protocol

### Step 1: Identify Affected Systems

Map the change to the correct doc folder:

| Change Type | Update This Doc |
|-------------|----------------|
| New API endpoint | `documents/backend/api.md` |
| Database schema change | `documents/database/schema.md` + migration note |
| New table/column | `documents/database/schema.md` |
| New plugin or hook | `documents/plugins/plugin-interface.md` |
| Plugin-specific logic | `documents/plugins/{name}-plugin.md` |
| New admin page/component | `documents/frontend/ui-components.md` |
| New platform worker | `documents/platforms/{name}.md` |
| Scheduler job change | `documents/scheduler/jobs.md` |
| Logging change | `documents/logger/logging.md` |
| Error handling change | `documents/error-handler/error-classification.md` |
| Bootstrap/deploy change | `documents/devops/bootstrap.md` or `security.md` |

### Step 2: Write What Actually Exists

Read the code. Write docs that match the implementation exactly.

- Copy function signatures from the code, not from memory.
- Copy config keys from `config.py`, not from `.env.example`.
- Copy SQL schema from `db.py` or migrations, not from conception archive.
- Include actual file paths relative to project root.

### Step 3: Doc Template

Each system doc should follow this structure:

```markdown
# {System Name}

## Overview
1-paragraph summary of what this system does.

## Files
| File | Purpose |
|------|---------|
| `flux/core/x.py` | Main service |
| `flux/api/x.py` | API endpoints |

## Key Concepts
- Bullet points of important abstractions
- Include code snippets for critical functions

## Configuration
- Relevant env vars or settings

## API / Interface
- If exposed to other systems, document the contract

## Common Tasks
### How to X
Step-by-step for frequent operations

### How to Y
...
```

### Step 4: Check for Stale Docs

When updating one doc, check if related docs are now stale:

- New API endpoint? Check if `frontend/ui-components.md` references the old endpoint URL.
- New config var? Check if `devops/bootstrap.md` mentions setup steps.
- New error type? Check if `error-handler/error-classification.md` lists it.

### Step 5: Update INDEX

If adding a new doc file, add it to `documents/INDEX.md`.

## Doc Quality Rules

1. **Code first, docs second.** Never document planned features.
2. **No copy-paste from conception archive.** Conception docs are frozen. System docs reflect reality.
3. **Keep it under 500 lines.** If a system doc grows too large, split it.
4. **Include file paths.** Every referenced function/class must include its file path.
5. **Include types.** Function signatures should show type hints.
6. **No screenshots of code.** Use markdown code blocks.

## Audit: Detect Stale Documentation

Run this check periodically:

```bash
# Check for docs referencing non-existent files
grep -r "flux/" documents/ --include="*.md" | while read line; do
    file=$(echo "$line" | grep -oP 'flux/[a-zA-Z0-9_./]+')
    if [ -n "$file" ] && [ ! -f "$file" ]; then
        echo "STALE: $file referenced in docs but does not exist"
    fi
done
```

Also watch for:
- Function names in docs that don't exist in code
- API endpoints in docs not registered in routers
- Config keys in docs not in `config.py`
- Table names in docs not in migrations

## Forbidden

- Do not write docs for features that are "coming soon" or "planned."
- Do not duplicate conception archive content in living docs.
- Do not leave "TODO: document this" in system docs.
- Do not document internal helper functions unless they're reused across modules.
