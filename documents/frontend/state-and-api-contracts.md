# Frontend State And API Contracts

## Purpose
This document defines how the Flux admin frontend should organize state and communicate with backend APIs during the rebuild.

It includes current routes used by the admin frontend and future contracts needed to satisfy the conception archive.

## State Shape
```js
{
  route: {
    view: "dashboard",
    pipelineId: null,
    workerId: null,
    tab: null
  },
  entities: {
    pipelines: {},
    workers: {},
    posts: {},
    plugins: {},
    settings: {},
    activity: []
  },
  lists: {
    pipelineIds: [],
    workerIds: [],
    postIds: [],
    pluginIds: []
  },
  view: {
    filters: {},
    sort: {},
    pagination: {},
    selectedIds: [],
    modal: null
  },
  operation: {
    active: false,
    id: null,
    label: null,
    target: null,
    startedAt: null,
    elapsedMs: 0,
    status: "idle",
    steps: [],
    error: null,
    result: null
  },
  status: {
    health: null,
    loading: {},
    errors: {},
    lastRefresh: {}
  }
}
```

## Store Rules
- State changes go through action functions.
- Views subscribe to store updates and re-render their owned region.
- Components receive data from views and do not read the store directly.
- Derived values live in selectors, not scattered across templates.
- Route changes update state before the view renders.

## API Client Rules
The API client should provide:
- `getJson(url, options)`
- `postJson(url, body, options)`
- `putJson(url, body, options)`
- `deleteJson(url, options)`

Each helper should:
- add JSON headers where needed
- parse JSON error bodies where possible
- return a consistent error shape
- support timeouts
- report request start and finish to the operation/status layer when appropriate

Standard error shape:
```js
{
  message: "Human readable error",
  status: 500,
  details: {},
  endpoint: "/api/example"
}
```

## Current Admin API Surface
These endpoints are already part of the current admin frontend contract:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | System health summary |
| `GET /api/system/dashboard` | Dashboard metrics and summary data |
| `GET /api/system/activity` | Recent backend activity |
| `GET /api/system/settings` | System settings |
| `PUT /api/system/settings/{key}` | Update one setting |
| `GET /api/pipelines` | List pipelines |
| `GET /api/pipelines/{id}` | Pipeline detail |
| `GET /api/pipelines/{id}/stats` | Pipeline metrics |
| `POST /api/pipelines/{id}/trigger` | Trigger a pipeline run |
| `GET /api/pipelines/{id}/ingredients` | Pipeline ingredients |
| `POST /api/pipelines/{id}/ingredients/approve` | Approve ingredients |
| `POST /api/pipelines/{id}/ingredients/reject` | Reject ingredients |
| `GET /api/pipelines/{id}/ingredients/{ingredient_id}/preview` | Preview one ingredient |
| `GET /api/pipelines/{id}/production` | Generated production content |
| `POST /api/pipelines/{id}/production/{content_id}/identify` | Identify or assign generated content |
| `GET /api/pipelines/{id}/production/{content_id}/stream` | Stream generated media |
| `GET /api/workers` | List platform workers |
| `GET /api/workers/{id}` | Worker detail |
| `GET /api/pipelines/{id}/workers` | Pipeline worker assignments |
| `POST /api/pipelines/{id}/workers/{worker_id}` | Assign worker to pipeline |
| `DELETE /api/pipelines/{id}/workers/{worker_id}` | Remove worker from pipeline |

## Future API Contracts
These contracts are needed for a frontend that fully satisfies the conception docs:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/posts` | Post history across platforms |
| `GET /api/posts/{id}` | Post detail and platform publish status |
| `GET /api/plugins` | Installed plugin list and health |
| `GET /api/plugins/{id}` | Plugin detail, settings, and capabilities |
| `POST /api/plugins/{id}/validate` | Validate plugin configuration |
| `GET /api/system/diagnostics` | Deep diagnostics beyond basic health |
| `POST /api/system/diagnostics/run` | Trigger diagnostics |
| `GET /api/operations/{id}` | Long-running operation status |
| `GET /api/operations/{id}/events` | Operation log or event stream |

Future endpoints must be hidden behind backend-pending UI until implemented.

## Operation Contract
Every backend action that may take more than one second should use a shared operation model.

Minimum synchronous fallback:
```js
{
  label: "Trigger pipeline",
  target: "Quran daily video",
  startedAt: 1710000000000,
  status: "running",
  steps: [
    { label: "Request sent", status: "done" },
    { label: "Waiting for backend response", status: "running" }
  ]
}
```

Future asynchronous response:
```json
{
  "operation_id": "op_123",
  "status": "queued",
  "links": {
    "status": "/api/operations/op_123",
    "events": "/api/operations/op_123/events"
  }
}
```

Future operation status:
```json
{
  "id": "op_123",
  "status": "running",
  "percent": 45,
  "current_step": "Rendering video",
  "started_at": "2026-05-01T00:00:00Z",
  "finished_at": null,
  "logs": [],
  "result": null,
  "error": null
}
```

## Rendering Rules
- A route renders from state, not from direct API response objects.
- On initial load, views show skeleton or compact loading state.
- On refresh failure with existing data, keep stale data visible and show a stale notice.
- On refresh failure without existing data, show an error state with retry.
- On unsupported future backend features, show backend-pending UI.

## Security And Data Safety
- Escape all server-provided text before rendering.
- Never inject backend HTML directly.
- Do not expose secrets from settings responses.
- Do not log full API responses in production UI.
- Confirm destructive actions.
