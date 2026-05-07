# Frontend Rebuild Plan

## Purpose
This document is the planning contract for the next Flux admin frontend rebuild. It translates the frozen conception archive into a frontend architecture before more UI work starts.

The conception archive stays frozen. This plan lives under `documents/frontend/` because it is the active frontend engineering plan.

## Product Direction
Flux is an operator console, not a landing page. The UI must help one operator understand content pipelines, platform workers, generated posts, plugin health, and system state with the least possible friction.

The most important rule from the conception archive is: every meaningful screen must answer "What pipeline?" and "What platform?" within two seconds.

The downloaded Stitch package in `C:\Users\Rabie\Downloads\stitch_clean_minimalist_design\` is now the visual reference for this rebuild. See `documents/frontend/stitch-design-adoption.md` for the screen-by-screen adoption plan.

## Design Principles
- Pipeline-first: the pipeline is the main organizing object.
- Platform-aware: TikTok, YouTube, Instagram, and future platforms need visible status and separation.
- Operator-grade feedback: every API call that triggers backend work must show progress, elapsed time, result, and failure details.
- Future-proof but honest: planned backend features can appear as disabled or pending states, never fake data.
- No god files: routing, state, API, views, and reusable components must be split.
- No build step for now: keep the static FastAPI-served frontend unless the project formally chooses a framework.
- Dense, calm interface: this is an operational tool, so use compact tables, tabs, filters, status pills, and clear actions.

## Proposed File Structure
```text
flux/static/admin/
  index.html
  css/
    vars.css              # design tokens only
    base.css              # reset, typography, form defaults
    layout.css            # app shell, sidebar, topbar, split panes
    components.css        # reusable component styles
    views.css             # view-specific layout
    responsive.css        # mobile and narrow viewport behavior
  js/
    main.js               # bootstraps the app
    router.js             # route/view selection and URL state
    state/
      store.js            # app state, subscriptions, selectors
      initial-state.js
    api/
      client.js           # fetch wrapper, errors, timeouts
      endpoints.js        # endpoint names and request helpers
    actions/
      operations.js       # long-running backend action handling
      pipelines.js
      workers.js
      settings.js
      plugins.js
      posts.js
    views/
      dashboard.js
      pipelines.js
      pipeline-workbench.js
      workers.js
      worker-detail.js
      posts.js
      system.js
      plugins.js
      activity.js
    components/
      app-shell.js
      topbar.js
      sidebar.js
      tabs.js
      toolbar.js
      data-table.js
      modal.js
      status-pill.js
      metric-card.js
      operation-panel.js
      empty-state.js
      error-state.js
      backend-pending.js
    utils/
      dom.js
      escape.js
      format.js
      time.js
```

## View Strategy
The rebuild should use one app shell with routed views. Each view owns its layout and calls reusable components for common UI.

Core views:
- Dashboard: command center for health, pipeline attention, worker activity, and recent operations.
- Pipelines: list of all content pipelines with filters and platform coverage.
- Pipeline Workbench: the main workspace for one pipeline, with tabs for overview, ingredients, production, workers, and settings.
- Workers: platform worker fleet health and assignments.
- Worker Detail: one worker's schedule, account state, captions, assigned pipelines, and logs.
- Posts: generated and published post history with platform status.
- System: health checks, settings, storage, diagnostics, and API/service state.
- Plugins: installed plugin health, plugin configuration, and future plugin marketplace hooks.
- Activity: searchable operation log and backend event stream.

## State Strategy
The frontend should keep state explicit and boring:
- `route`: current view, selected pipeline, selected worker, active tab.
- `entities`: cached pipelines, workers, posts, plugins, settings, activity.
- `view`: filters, sort, pagination, modal state, selected rows.
- `operation`: active backend action, elapsed time, progress steps, final result.
- `status`: health, loading flags, last refresh timestamps, recoverable errors.

Views read state through selectors. Actions mutate state through one store API. Components should not perform raw fetch calls.

## Backend Feedback Strategy
Current backend actions are mostly synchronous HTTP calls. The frontend must still show:
- action name and target
- elapsed time
- current step
- disabled duplicate action buttons
- success or failure summary
- latest activity refresh while the operation runs

Future backend work should add operation or job endpoints:
- `POST /api/operations` or route-specific triggers return an `operation_id`
- `GET /api/operations/{id}` returns status, percent, current step, logs, and result links
- `GET /api/operations/{id}/events` can become SSE later

Until those endpoints exist, the frontend uses a synchronous fallback operation panel.

## Component Rules
- Components render HTML from data and emit events. They do not own global state.
- Components must support loading, empty, error, and backend-pending states.
- Buttons that trigger backend work must have disabled and busy states.
- Tables must support at least empty, loading, error, and row action states.
- Modals are reserved for focused inspection or confirmation, not primary navigation.
- Avoid nested cards. Use cards only for repeated entities, modals, and compact metrics.

## Implementation Phases
1. Foundation: create the file structure, router, store, API client, shell, and base components.
2. Dashboard and pipelines: rebuild the dashboard and pipeline list around real API data.
3. Pipeline workbench: add tabs for overview, ingredients, production, workers, and settings.
4. Workers and posts: build worker fleet views and post history with future-safe pending states.
5. System and plugins: expose system health, settings, diagnostics, and plugin status.
6. Operation progress: replace synchronous-only feedback with job progress when backend support exists.
7. Polish and QA: desktop/mobile visual pass, keyboard/focus pass, loading/error pass, and code audit.

## Acceptance Criteria
- No frontend source file should become a new god file.
- No inline styles or inline event handlers.
- CSS colors should live in `vars.css` unless they are one-off semantic states.
- Every API-backed view has loading, empty, error, and stale-data states.
- Every backend action gives visible progress feedback.
- Desktop and mobile layouts are tested in the in-app browser.
- `node --check` passes for all JavaScript files.
- Existing Flux review audits pass without frontend warnings.
