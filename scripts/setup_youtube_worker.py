"""Set up a YouTube worker with credentials and link to a pipeline.

Usage:
    python scripts/setup_youtube_worker.py
    python scripts/setup_youtube_worker.py --creds secrets/youtube_credentials.json
    python scripts/setup_youtube_worker.py --name "Quran Shorts Channel"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

DEFAULT_CREDS = _PROJECT_ROOT / "secrets" / "youtube_credentials.json"


async def setup_worker(
    creds_path: Path,
    display_name: str,
    pipeline_name: str | None,
    schedule_cron: str,
) -> None:
    from flux.core.crypto import encrypt_dict
    from flux.db import AsyncSessionLocal, init_db
    from flux.models import Pipeline, PipelineWorker, PlatformWorker

    from sqlalchemy import select

    # ── Load credentials ──────────────────────────────────────────────
    if not creds_path.exists():
        print(f"[ERROR] Credentials file not found: {creds_path}")
        print("  Run: python scripts/youtube_auth.py --secrets secrets/client_secret.json")
        sys.exit(1)

    with open(creds_path) as f:
        creds_dict = json.load(f)

    if not creds_dict.get("refresh_token"):
        print("[ERROR] Credentials file is missing 'refresh_token'. Re-run youtube_auth.py.")
        sys.exit(1)

    # ── Initialize DB ─────────────────────────────────────────────────
    await init_db()

    async with AsyncSessionLocal() as db:
        # ── Check for existing YouTube worker with same name ──────────
        result = await db.execute(
            select(PlatformWorker).where(
                PlatformWorker.platform == "youtube",
                PlatformWorker.display_name == display_name,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"[INFO] YouTube worker '{display_name}' already exists (ID: {existing.id})")
            print("[INFO] Updating credentials...")
            existing.credentials_json = encrypt_dict(creds_dict)
            existing.connection_strategy = "official"
            existing.schedule_cron = schedule_cron
            await db.commit()
            worker = existing
        else:
            # Create new worker
            worker = PlatformWorker(
                platform="youtube",
                display_name=display_name,
                connection_strategy="official",
                credentials_json=encrypt_dict(creds_dict),
                schedule_cron=schedule_cron,
                enabled=True,
            )
            db.add(worker)
            await db.commit()
            await db.refresh(worker)
            print(f"[OK] Created YouTube worker: {display_name} (ID: {worker.id})")

        # ── Link to pipeline ──────────────────────────────────────────
        if pipeline_name:
            result = await db.execute(
                select(Pipeline).where(Pipeline.name.ilike(f"%{pipeline_name}%"))
            )
            pipeline = result.scalar_one_or_none()

            if not pipeline:
                # List available pipelines
                all_pipes = await db.execute(select(Pipeline))
                pipes = all_pipes.scalars().all()
                if pipes:
                    print(f"\n[WARN] No pipeline matching '{pipeline_name}'. Available:")
                    for p in pipes:
                        print(f"  - {p.name} (ID: {p.id})")
                else:
                    print("\n[WARN] No pipelines exist yet. Create one first.")
            else:
                # Check if already linked
                result = await db.execute(
                    select(PipelineWorker).where(
                        PipelineWorker.pipeline_id == pipeline.id,
                        PipelineWorker.worker_id == worker.id,
                    )
                )
                link = result.scalar_one_or_none()

                if link:
                    print(f"[INFO] Worker already linked to pipeline '{pipeline.name}'")
                else:
                    link = PipelineWorker(
                        pipeline_id=pipeline.id,
                        worker_id=worker.id,
                    )
                    db.add(link)
                    await db.commit()
                    print(f"[OK] Linked worker to pipeline: {pipeline.name}")

        # ── Summary ───────────────────────────────────────────────────
        print(f"\n{'='*50}")
        print(f"  Worker ID:    {worker.id}")
        print(f"  Platform:     {worker.platform}")
        print(f"  Strategy:     {worker.connection_strategy}")
        print(f"  Display Name: {worker.display_name}")
        print(f"  Schedule:     {worker.schedule_cron or 'manual only'}")
        print(f"  Enabled:      {worker.enabled}")
        print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description="Create a YouTube worker and store OAuth credentials."
    )
    parser.add_argument(
        "--creds",
        type=Path,
        default=DEFAULT_CREDS,
        help=f"Path to youtube_credentials.json. Default: {DEFAULT_CREDS}",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="YouTube Channel",
        help="Display name for the worker. Default: 'YouTube Channel'",
    )
    parser.add_argument(
        "--pipeline",
        type=str,
        default="quran",
        help="Pipeline name to link to (fuzzy match). Default: 'quran'",
    )
    parser.add_argument(
        "--cron",
        type=str,
        default="0 8 * * *",
        help="Cron schedule for auto-posting. Default: '0 8 * * *' (daily at 08:00 UTC)",
    )

    args = parser.parse_args()
    asyncio.run(setup_worker(args.creds, args.name, args.pipeline, args.cron))


if __name__ == "__main__":
    main()
