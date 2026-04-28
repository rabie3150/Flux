# UI Components Documentation

## Overview
The Flux Admin Panel is a single-page application built with **Vanilla HTML and Alpine.js**. It provides a reactive interface for managing pipelines, ingredients, workers, and monitoring system activity.

## Files
| File | Purpose |
|------|---------|
| `flux/static/admin/index.html` | Main entry point containing HTML, CSS, and Alpine.js logic |
| `flux/main.py` | Mounts the static files at the `/admin` path |

## Key Concepts
- **Reactive State:** Uses Alpine.js to fetch data from the API and update the DOM automatically.
- **Polling:** Automatically refreshes dashboard stats and activity logs every 30 seconds.
- **Modular Sections:** The UI is divided into Dashboard, Pipelines, Workers, and Recent Activity.

## UI Sections

### Dashboard
Displays high-level statistics:
- Total number of configured pipelines.
- Total number of platform workers.

### Pipelines
Table view for managing automation streams.
- **Actions:** Create new pipeline, toggle enabled status, delete pipeline.
- **Fields:** Name, Plugin ID, Status, Created Date.

### Platform Workers
Table view for social media accounts.
- **Actions:** Create worker, toggle enabled status, delete worker.
- **Fields:** Platform (YouTube, Telegram, etc.), Name, Schedule (Cron), Status.

### Recent Activity
Log table showing the last 10 system events.
- **Fields:** Timestamp, Level (Info/Warn/Error), Event Type, Message.

## Styling
- **Theme:** Dark mode by default (#0f0f23).
- **Responsive:** Mobile-friendly layout using CSS flexbox and media queries.
- **Color Coding:** Statuses are color-coded (Green for Enabled/Success, Red for Disabled/Error).

## Development
To modify the UI, edit `flux/static/admin/index.html`. Changes are reflected immediately upon browser refresh if the FastAPI server is running with `--reload`.
