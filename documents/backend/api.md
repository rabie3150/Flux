# API Documentation

## Overview
Flux exposes a RESTful API via FastAPI. The API is used by the Admin UI and can be used by external watchdog scripts or tools (e.g., GitHub Actions).

## Authentication
Currently, the API is bound to `127.0.0.1` and does not require authentication for local access. Remote access via GitHub Actions uses a bearer token configured in `FLUX_REMOTE_KEY`.

## Routers

### System (`/api/system`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Returns system health, uptime, and version. |
| `/api/system/dashboard` | GET | Returns aggregate stats for the dashboard. |
| `/api/system/activity` | GET | Returns recent activity logs (paginated). |

### Pipelines (`/api/pipelines`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/pipelines` | GET | List all configured pipelines. |
| `/api/pipelines` | POST | Create a new pipeline. |
| `/api/pipelines/{id}` | GET | Get details of a specific pipeline. |
| `/api/pipelines/{id}` | PUT | Update pipeline configuration or status. |
| `/api/pipelines/{id}` | DELETE | Delete a pipeline and its data. |
| `/api/pipelines/{id}/stats` | GET | Get stock levels and queue depth. |
| `/api/pipelines/{id}/trigger` | POST | Manually trigger fetch, render, or post. |

### Ingredients (`/api/ingredients`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ingredients` | GET | List ingredients with filtering (pipeline, status, type). |
| `/api/ingredients/{id}` | GET | Get ingredient details. |
| `/api/ingredients/{id}/status` | PUT | Approve or reject an ingredient. |
| `/api/ingredients/{id}` | DELETE | Delete an ingredient file and record. |

### Workers (`/api/workers`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workers` | GET | List all platform workers. |
| `/api/workers` | POST | Create a new platform worker (account). |
| `/api/workers/{id}` | GET | Get worker details. |
| `/api/workers/{id}` | PUT | Update worker config or credentials. |
| `/api/workers/{id}` | DELETE | Delete a worker. |

## Schemas
Most POST/PUT endpoints use Pydantic models for validation. See `flux/api/*.py` for specific field definitions.
