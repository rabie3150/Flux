# Frontend View Map

## Purpose
This document defines the screens, windows, and user flows for the Flux admin frontend rebuild.

## Global Shell
Every screen uses the same shell:
- Sidebar navigation: Dashboard, Pipelines, Workers, Posts, System, Plugins, Activity.
- Topbar: current route, selected pipeline/platform context, refresh state, active operation state.
- Toast stack: short success and failure messages.
- Operation panel: persistent progress feedback for backend work.

## Dashboard
Primary question: What needs attention right now?

Data:
- `/api/health`
- `/api/system/dashboard`
- `/api/system/activity`

Main regions:
- Health strip: API, database, scheduler, plugins, workers.
- Attention queue: failed jobs, stuck workers, rejected ingredients, unpublished posts.
- Pipeline summary: pipeline cards or compact rows with platform status.
- Worker summary: platform workers and last run.
- Recent activity: latest backend events.

Required states:
- Loading skeleton for initial fetch.
- Empty state when no pipelines exist.
- Error state when health or dashboard calls fail.
- Stale indicator when refresh fails after previous data exists.

## Pipelines
Primary question: Which pipeline am I operating?

Data:
- `/api/pipelines`
- `/api/pipelines/{id}/stats`

Main regions:
- Filter bar: status, content type, platform, plugin.
- Pipeline table: name, plugin, platforms, ingredient status, production status, latest run.
- Row actions: open workbench, trigger pipeline, view activity.

Required states:
- Empty state with setup guidance.
- Per-row loading for trigger actions.
- Clear disabled state when backend capability is not available.

## Pipeline Workbench
Primary question: What is happening inside this pipeline, from source to platform output?

Route:
- `#/pipelines/{pipeline_id}`

Tabs:
- Overview
- Ingredients
- Production
- Workers
- Settings

Shared context header:
- Pipeline name
- Plugin/content type
- Target platforms
- Last run
- Current operation
- Primary action: trigger pipeline

## Pipeline Workbench: Overview
Data:
- `/api/pipelines/{id}`
- `/api/pipelines/{id}/stats`
- `/api/system/activity`

Main regions:
- Stage flow: source, ingredients, approval, production, platform assignment, publish.
- Metrics: pending ingredients, approved ingredients, generated content, platform coverage.
- Latest output: recent content cards with preview actions.
- Activity: filtered by pipeline.

## Pipeline Workbench: Ingredients
Data:
- `/api/pipelines/{id}/ingredients`
- `/api/pipelines/{id}/ingredients/{ingredient_id}/preview`
- `/api/pipelines/{id}/ingredients/approve`
- `/api/pipelines/{id}/ingredients/reject`

Main regions:
- Ingredient queue table.
- Preview modal or side panel.
- Bulk approve/reject actions.
- Per-item status, source, and validation feedback.

Required states:
- Preview loading state.
- Rejection confirmation.
- Bulk action progress.

## Pipeline Workbench: Production
Data:
- `/api/pipelines/{id}/production`
- `/api/pipelines/{id}/production/{content_id}/identify`
- `/api/pipelines/{id}/production/{content_id}/stream`

Main regions:
- Generated content table.
- Media preview window.
- Platform assignment status.
- Identify/rebuild actions when backend supports them.

Required states:
- Stream unavailable state.
- Missing media state.
- Action progress for identify and render calls.

## Pipeline Workbench: Workers
Data:
- `/api/pipelines/{id}/workers`
- `/api/pipelines/{id}/workers/{worker_id}`
- `/api/workers`

Main regions:
- Assigned worker list by platform.
- Available worker picker.
- Assignment health and last run.
- Add/remove assignment actions.

Required states:
- No workers for platform.
- Worker unavailable.
- Assignment conflict.

## Pipeline Workbench: Settings
Data:
- `/api/pipelines/{id}`
- Future pipeline settings endpoints.

Main regions:
- Source configuration summary.
- Platform targeting.
- Schedule policy.
- Caption/template policy.
- Safety and approval policy.

Until backend settings endpoints exist, this view should show read-only current data plus backend-pending panels.

## Workers
Primary question: Are platform workers ready to publish?

Data:
- `/api/workers`

Main regions:
- Platform filter.
- Worker table: handle, platform, status, last run, assigned pipelines, health.
- Row actions: open detail, assign pipeline, pause/resume when backend exists.

Required states:
- No workers configured.
- Platform auth missing.
- Worker action pending.

## Worker Detail
Primary question: What is this worker responsible for and is it healthy?

Data:
- `/api/workers/{id}`
- `/api/pipelines/{id}/workers`
- Future worker log and schedule endpoints.

Tabs:
- Overview
- Schedule
- Captions
- Pipelines
- Logs

Until backend endpoints exist, missing tabs show backend-pending panels.

## Posts
Primary question: What content has been generated, scheduled, or published?

Data:
- Future `/api/posts`
- Future `/api/posts/{id}`

Main regions:
- Post table: content, pipeline, platform, worker, status, published URL, timestamps.
- Filters: platform, pipeline, status, date.
- Preview modal.

Current behavior:
- Show backend-pending state until post history endpoints exist.

## System
Primary question: Is Flux configured and healthy?

Data:
- `/api/health`
- `/api/system/settings`
- `/api/system/settings/{key}`
- Future diagnostics endpoints.

Tabs:
- Health
- Settings
- Storage
- Sources
- Security

Main actions:
- Refresh health.
- Save settings.
- Run diagnostics when backend exists.

## Plugins
Primary question: Which content engines are available and healthy?

Data:
- Current plugin data from dashboard/settings if available.
- Future `/api/plugins`
- Future `/api/plugins/{id}`

Main regions:
- Installed plugin list.
- Plugin detail panel.
- Capability matrix: source, render, caption, platform support.
- Validation status.

Current behavior:
- Show installed information when available.
- Show backend-pending panels for install/update workflows.

## Activity
Primary question: What did the backend just do?

Data:
- `/api/system/activity`
- Future operation/job logs.

Main regions:
- Search and filters.
- Event list.
- Operation detail drawer.
- Error detail expansion.

Required states:
- Live refresh indicator.
- Paused refresh state.
- Empty log state.
- Error detail with copyable text when available.
