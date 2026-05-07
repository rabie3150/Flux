# UI Components Documentation

## Overview
The Flux Admin Panel is a single-page application built with static HTML, vanilla JavaScript, and vanilla CSS. It provides an operator-console interface for pipeline review, production, worker management, posts, plugins, settings, and activity monitoring.

The current visual direction follows the downloaded Stitch clean minimalist design package: light neutral canvas, white sidebar, sticky topbar, electric-blue primary actions, compact status pills, white data panels, and dense operator tables.

## Files
| File | Purpose |
|------|---------|
| `flux/static/admin/index.html` | Static app shell, sidebar, topbar, modal mount, and asset links |
| `flux/static/admin/js/app.js` | State, API calls, event binding, workflow actions, and modal behavior |
| `flux/static/admin/js/ui.js` | HTML template functions for dashboard, pipelines, workers, posts, system, plugins, and activity |
| `flux/static/admin/css/vars.css` | Centralized CSS variables and color tokens |
| `flux/static/admin/css/app.css` | Base layout, panels, controls, cards, tables, and modal styles |
| `flux/static/admin/css/responsive.css` | Mobile and tablet responsive layout rules |
| `flux/main.py` | Mounts the static files at the `/admin` path |

## Key Concepts
- **Local State:** `flux/static/admin/js/app.js` keeps the current view, selected pipeline, selected worker, filters, and fetched API data in a single `state` object.
- **Polling:** Automatically refreshes dashboard stats and activity logs every 30 seconds.
- **Conception-Aligned Navigation:** The UI is divided into Dashboard, Pipelines, Workers, Posts, System, Plugins, and Activity.
- **Graceful Backend Gaps:** Frontend surfaces for future backend areas, such as `/api/posts`, render planned sections without breaking if the endpoint is not implemented yet.
- **Operation Feedback:** Fetch and render calls show a compact in-workbench progress banner with elapsed time and operator-facing backend phases. Raw content and pipeline IDs are hidden from normal UI copy, duplicate render controls are suppressed, and activity polling continues while the synchronous API request is in flight.
- **Stitch-Inspired Shell:** The app shell, dashboard cards, pipeline workbench, production queue metrics, worker cards, and data tables now mirror the approved Stitch reference while keeping Flux API/state wiring.

## UI Sections

### Dashboard
Displays global operational state:
- Total number of configured pipelines.
- Total number of platform workers.
- Ready queue count across all loaded pipelines.
- Review backlog from pending ingredients and verse-unknown renders.
- Attention Queue cards linking directly to Review, Identify, Ready, and Worker workflows.

### Pipelines
Workbench view for managing automation streams.
- **Actions:** Create new pipeline, toggle enabled status, delete pipeline.
- **Fields:** Name, Plugin ID, Status, Created Date.
- **Tabs:** Overview, Ingredients, Production, Workers, Settings.
- **Core flow:** Review ingredients -> Produce/render -> Identify metadata -> Ready queue.
- **Fetch/render feedback:** `triggerFetch()` and `triggerRender()` in `flux/static/admin/js/app.js` call `startOperation()` before awaiting the backend response. The operation panel is rendered by `operationTemplate()` in `flux/static/admin/js/ui.js`.
- **Ingredient selection:** The Ingredients tab supports Select All, Clear, Invert, Ctrl/Cmd-click toggle, Shift-click range selection, Ctrl/Cmd+A to select all visible ingredients, and Escape to clear selection.
- **Detected verses:** The Production tab renders verse ranges (`surah:ayah-end`), cached Arabic text in an RTL block, and translation/caption text when available from the production API.
- **Compact production table:** Multi-verse items show as a single-row summary with the range, surah name, spaced reference summary, and one-line Arabic preview. Full multi-ayah Arabic text remains available through the preview/assignment surfaces. The table uses compact stats, short rendered times with full timestamps in tooltips, humanized statuses, and icon-only row actions.
- **Manual verse overrides:** Assign Verse posts manual metadata with `identified_by: manual` and `manual_override: true`. The backend overwrites AI-selected `surah`, `ayah`, and `ayah_end`; blank end ayah clears any stale AI range.

### Platform Workers
Worker list and detail view for social media accounts.
- **Actions:** Create worker, toggle enabled status, delete worker.
- **Fields:** Platform (YouTube, Telegram, etc.), Name, Schedule (Cron), Status.
- **Tabs:** Overview, Schedule, Caption, Pipelines, Logs.
- **Pipeline attachments:** Uses existing pipeline-worker API endpoints to attach/detach workers where backend support exists.

### Posts
Post log surface for Phase 5 publishing. If `/api/posts` is not available, the page shows a backend-pending state instead of failing.

### System
Health, diagnostics, storage, source, caption, timezone, and retention controls. Settings are saved through `PUT /api/system/settings/{key}`.

### Plugins
Installed plugin inventory derived from known plugins and configured pipelines. The page is ready for future plugin registry/install backend work.

### Recent Activity
Log table showing the last 10 system events.
- **Fields:** Timestamp, Level (Info/Warn/Error), Event Type, Message.

## Styling
- **Theme:** Stitch-inspired light operator-console palette defined in `flux/static/admin/css/vars.css`.
- **Responsive:** Mobile-friendly sidebar and responsive grids in `flux/static/admin/css/responsive.css`.
- **Color Coding:** Statuses use centralized semantic tokens for ok, warning, danger, info, and paused states.

## Development
To modify the UI shell, edit `flux/static/admin/index.html`. For behavior, edit `flux/static/admin/js/app.js`. For markup templates, edit `flux/static/admin/js/ui.js`. For theme tokens, edit `flux/static/admin/css/vars.css`; avoid hardcoded colors in other frontend files.
