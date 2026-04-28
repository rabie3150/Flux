# Scheduler Documentation

## Overview
Flux uses **APScheduler** (AsyncIOScheduler) to manage periodic tasks like content fetching, rendering, and publishing. The scheduler is designed to be resilient, persisting jobs in the SQLite database so they survive application restarts and system reboots.

## Files
| File | Purpose |
|------|---------|
| `flux/scheduler.py` | Scheduler initialization, configuration, and lifecycle management |
| `flux/main.py` | Starts the scheduler during application startup (lifespan) |

## Key Concepts
- **Persistence:** Jobs are stored in the `apscheduler_jobs` table within the main SQLite database (`app.db`).
- **Single Instance:** Every job is configured with `max_instances=1` to prevent concurrent execution of the same task.
- **Misfire Handling:** `coalesce=True` ensures that if multiple runs of a job are missed (e.g., phone was off), it only runs once when the system resumes.
- **Grace Time:** A 1-hour `misfire_grace_time` allows jobs to run late if the system was temporarily unavailable.

## Configuration
The scheduler uses settings from `flux/config.py`:
- `database_url`: Used to connect the `SQLAlchemyJobStore`.
- `flux_env`: Influences logging verbosity for scheduler internals.

## API / Interface
### `init_scheduler() -> AsyncIOScheduler`
Initializes the global scheduler instance with the following defaults:
```python
job_defaults = {
    "coalesce": True,
    "max_instances": 1,
    "misfire_grace_time": 3600,
}
```

### `get_scheduler() -> AsyncIOScheduler`
Returns the active scheduler instance. Raises `RuntimeError` if not initialized.

### `shutdown_scheduler(wait: bool = True)`
Gracefully stops the scheduler and releases resources.

## Common Tasks
### Registering a New Job
Jobs are typically registered during pipeline initialization or worker startup.
```python
from flux.scheduler import get_scheduler

scheduler = get_scheduler()
scheduler.add_job(
    func, 
    'cron', 
    id='job_id', 
    replace_existing=True,
    **cron_args
)
```

### Monitoring Jobs
You can inspect the `apscheduler_jobs` table in `app.db` to see scheduled tasks and their next run times.
