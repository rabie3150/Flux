---
name: flux-build
description: >
  Build and implement features for the Flux content automation app.
  Use when asked to build, implement, create, add, or extend any code,
  page, component, API endpoint, plugin, or database model in the Flux project.
  Enforces consistency, prevents reinvention, and mandates context gathering
  before writing new code.
---

# Flux Build Skill

## Pre-Build Context Gathering (MANDATORY)

Before writing any new file, function, page, or component, gather context:

1. **Read existing similar implementations**
   - Find at least 2–3 existing files that do something similar.
   - Use `grep` or file search. Do not guess patterns.
   - Example: adding a new API endpoint? Read 2 existing endpoint files first.
   - Example: adding a new admin page? Read 2 existing HTML files first.

2. **Check for existing utilities**
   - Search `flux/core/`, `flux/plugins/base.py`, and `flux/platforms/base.py`.
   - If a helper exists, use it. Do not reinvent.
   - Common utilities: `flux/db.py`, `flux/config.py`, `flux/storage.py`, `flux/notifications.py`.

3. **Verify naming conventions**
   - Functions: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`
   - Database tables: `snake_case`, plural (`produced_content`, not `ProducedContent`)
   - API endpoints: `kebab-case` in URLs

4. **Check file size budget**
   - No file should exceed 800 lines.
   - If adding code pushes a file over 800 lines, refactor FIRST.
   - Extract into a new module or split the class.

## Build Rules

### Never Reinvent
- Check `flux/core/` and `flux/plugins/base.py` before writing generic logic.
- Check `static/admin/` for existing CSS/JS patterns before adding new frontend code.
- If you copy-paste code from one file to another, extract it into a shared utility.

### Temporary Code Protocol
- All temporary/debug code MUST be marked with `# TEMP: <reason>` or `# FIXME: <reason>`.
- Temporary functions MUST be prefixed with `_temp_`.
- Before declaring any task "done", remove all TEMP/FIXME markers or convert them to GitHub issues.

### Time Handling (FORBIDDEN PATTERNS)
- **NEVER** use `datetime.now()` without timezone.
- **NEVER** use `datetime.utcnow()` (deprecated).
- **NEVER** use `datetime.today()`.
- **ALWAYS** use `datetime.now(timezone.utc)` or `datetime.now(Config.TIMEZONE)`.
- Import from `flux.config` if app timezone is needed.

### Path Handling
- **NEVER** hardcode `/storage/emulated/0/Flux/` or `C:\` paths in business logic.
- **ALWAYS** use `settings.STORAGE_PATH` or `settings.DATABASE_URL`.
- Bootstrap scripts and `start.sh` are the ONLY files allowed to have hardcoded paths.

### UI/Frontend Consistency
- Admin panel uses **Alpine.js** + vanilla HTML. No React, no Vue build step.
- All colors come from `static/admin/css/vars.css`. No hex codes in inline styles or JS.
- All custom UI components (buttons, cards, modals) MUST reuse existing HTML/CSS patterns.
- If adding a new page, copy the layout structure from the most recently built page.

### Database Changes
- All schema changes require an Alembic migration.
- Run `alembic revision --autogenerate -m "description"` after model changes.
- Never modify existing migrations.

### Logging
- **NEVER** use `print()` in production code.
- Use `logger = logging.getLogger(__name__)` and `logger.info/warning/error()`.
- Redact secrets in log messages.

## Post-Build Checklist

Before saying "done":
- [ ] I read at least 2 similar existing files before coding.
- [ ] I checked for existing utilities and reused them.
- [ ] No file exceeds 800 lines (run `wc -l` if unsure).
- [ ] No `print()` statements.
- [ ] No naive `datetime.now()` calls.
- [ ] No hardcoded paths in business logic.
- [ ] No inline style attributes in HTML.
- [ ] Temporary code is marked with `# TEMP:` or `# FIXME:`.
- [ ] Unit tests added for pure logic.
- [ ] `.env.example` updated if new settings added.
