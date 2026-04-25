# Flux Documentation

Living documentation for the Flux content automation engine. Updated as code evolves.

## Structure

```
documents/
├── README.md              # This file
├── INDEX.md               # Quick lookup for all docs
├── backend/               # Core engine, API, plugin system
├── database/              # Schema, migrations, query patterns
├── frontend/              # Admin panel, UI components, wireframes
├── devops/                # Infrastructure, security, monitoring
├── scheduler/             # APScheduler jobs, cron expressions
├── logger/                # Logging strategy, rotation, redaction
├── error-handler/         # Error classification, retry, circuit breaker
├── platforms/             # Social media integrations (YouTube, Telegram, etc.)
├── plugins/               # Plugin architecture + reference implementations
└── conception_archive/    # Original conception phase docs (read-only archive)
```

## How to Use These Docs

- **Building a feature?** Read the system docs for the layer you're touching first.
- **Changing the database?** Update `database/schema.md` and add an Alembic migration.
- **Adding a new platform?** Copy `platforms/youtube.md` as a template.
- **Adding a new plugin?** Read `plugins/plugin-interface.md` and `plugins/quran-plugin.md`.
- **Debugging?** Check `error-handler/error-classification.md` for retry rules.
- **Deploying?** Follow `devops/bootstrap.md` and `devops/security.md`.

## Update Rules

1. **Code and docs move together.** Every PR that changes behavior must update the relevant system doc.
2. **No stale screenshots.** If the UI changes, update `frontend/wireframes.md`.
3. **Schema changes require doc updates.** If you add a table or column, update `database/schema.md`.
4. **Platform API changes?** Update the relevant `platforms/*.md` file.
5. **Conception archive is frozen.** Do not modify `conception_archive/`. It preserves the original design decisions.

## Quick Links

| I want to... | Read this |
|-------------|-----------|
| Understand the big picture | `conception_archive/01-prd.md` |
| Build a new API endpoint | `backend/api.md` + `backend/architecture.md` |
| Build a new admin page | `frontend/ui-components.md` |
| Add a database table | `database/schema.md` + `database/migrations.md` |
| Write a new plugin | `plugins/plugin-interface.md` |
| Connect a new social platform | `platforms/youtube.md` (template) |
| Fix a bug | `error-handler/error-classification.md` + `devops/monitoring.md` |
| Deploy to a new phone | `devops/bootstrap.md` |
