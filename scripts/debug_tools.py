"""Debug utilities for Flux."""

import argparse
import asyncio
import os
import shutil
from pathlib import Path

from flux.config import settings
from flux.db import AsyncSessionLocal
from flux.models import Ingredient, ProducedContent
from sqlalchemy import delete

async def wipe_ingredients():
    """Wipe all ingredients and produced content from DB and delete files."""
    print("WARNING: This will delete ALL media and database records for ingredients and production.")
    confirm = input("Are you sure? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    async with AsyncSessionLocal() as db:
        await db.execute(delete(ProducedContent))
        await db.execute(delete(Ingredient))
        await db.commit()
        print("Database tables 'ingredients' and 'produced_content' cleaned.")

    library_dir = Path(settings.storage_path) / "library"
    dirs_to_clean = [
        library_dir / "quran_clips",
        library_dir / "bg_image",
        library_dir / "bg_video",
        library_dir / "backgrounds" / "images", # legacy/alternative path
        library_dir / "backgrounds" / "videos"
    ]

    for d in dirs_to_clean:
        if d.exists():
            for item in d.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    print(f"Failed to delete {item}: {e}")
            print(f"Cleaned directory: {d}")
        else:
            print(f"Directory not found (skipping): {d}")
            
    print("Wipe complete.")

def main():
    parser = argparse.ArgumentParser(description="Flux Debug Tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Wipe command
    wipe_parser = subparsers.add_parser("wipe-ingredients", help="Wipe all ingredients from DB and disk")

    args = parser.parse_args()

    if args.command == "wipe-ingredients":
        asyncio.run(wipe_ingredients())
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
