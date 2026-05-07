"""One-time YouTube OAuth2 consent flow.

Run this on a machine with a browser to generate the credentials
needed by YouTubeOfficialPublisher.

Usage:
    python scripts/youtube_auth.py                          # uses default path from .env
    python scripts/youtube_auth.py --secrets path/to/client_secret.json
    python scripts/youtube_auth.py --worker-id <ID>         # store directly into a worker

Prerequisites:
    1. Go to https://console.cloud.google.com
    2. Create a project (or use existing)
    3. Enable "YouTube Data API v3"
    4. Create OAuth 2.0 Client ID (Desktop application)
    5. Download the client_secret.json file
    6. Place it at the path configured in YOUTUBE_CLIENT_SECRETS_PATH (.env)

This script will:
    - Open your browser for Google account authorization
    - Save the resulting credentials to a JSON file
    - Optionally store them (encrypted) directly into a Flux platform worker
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path so we can import flux modules
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULT_OUTPUT = _PROJECT_ROOT / "secrets" / "youtube_credentials.json"


def run_oauth_flow(client_secrets_path: Path) -> dict:
    """Run the OAuth consent flow and return the credential dict.

    Opens a browser window for the user to authorize the application.
    Returns a dict ready to be stored in platform_workers.credentials_json.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not client_secrets_path.exists():
        print(f"\n[ERROR] Client secrets file not found: {client_secrets_path}")
        print()
        print("  To get this file:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create an OAuth 2.0 Client ID (type: Desktop application)")
        print("  3. Download the JSON file")
        print(f"  4. Save it to: {client_secrets_path}")
        sys.exit(1)

    print(f"\n[INFO] Using client secrets from: {client_secrets_path}")
    print("[INFO] Opening browser for Google authorization...")
    print("[INFO] If browser doesn't open, check the console for a URL.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path), SCOPES
    )
    credentials = flow.run_local_server(port=0)

    # Build the credential dict in the format expected by YouTubeOfficialPublisher
    creds_dict = {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
        "token": credentials.token,
        "token_uri": credentials.token_uri,
        "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
        # YouTube-specific defaults (operator can change later via admin API)
        "category_id": "27",       # 27 = Education
        "privacy_status": "public",
        "tags": [],
    }

    return creds_dict


def save_to_file(creds_dict: dict, output_path: Path) -> None:
    """Save credentials to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(creds_dict, f, indent=2)
    print(f"\n[OK] Credentials saved to: {output_path}")
    print("[WARN] This file contains secrets — do NOT commit it to git.")


async def store_in_worker(creds_dict: dict, worker_id: str) -> None:
    """Encrypt and store credentials directly into a platform worker."""
    from flux.core.crypto import encrypt_dict
    from flux.db import AsyncSessionLocal, init_db
    from flux.models import PlatformWorker

    await init_db()

    async with AsyncSessionLocal() as db:
        worker = await db.get(PlatformWorker, worker_id)
        if not worker:
            print(f"\n[ERROR] Worker not found: {worker_id}")
            sys.exit(1)

        if worker.platform != "youtube":
            print(f"\n[ERROR] Worker '{worker.display_name}' is platform "
                  f"'{worker.platform}', not 'youtube'.")
            sys.exit(1)

        worker.credentials_json = encrypt_dict(creds_dict)
        worker.connection_strategy = "official"
        await db.commit()
        print(f"\n[OK] Credentials stored (encrypted) in worker: "
              f"{worker.display_name} ({worker_id})")


def main():
    parser = argparse.ArgumentParser(
        description="Generate YouTube OAuth2 credentials for Flux."
    )
    parser.add_argument(
        "--secrets",
        type=Path,
        default=None,
        help="Path to client_secret.json from Google Cloud Console. "
             "Defaults to YOUTUBE_CLIENT_SECRETS_PATH from .env",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to save the credential JSON. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="If provided, store credentials directly into this platform worker "
             "(encrypted in DB). Skips file output.",
    )
    parser.add_argument(
        "--category-id",
        type=str,
        default="27",
        help="YouTube video category ID. Default: 27 (Education). "
             "See https://developers.google.com/youtube/v3/docs/videoCategories",
    )
    parser.add_argument(
        "--privacy",
        type=str,
        choices=["public", "unlisted", "private"],
        default="public",
        help="Default privacy status for uploads. Default: public",
    )

    args = parser.parse_args()

    # Resolve client secrets path
    secrets_path = args.secrets
    if secrets_path is None:
        try:
            from flux.config import settings
            secrets_path = settings.youtube_client_secrets_path
        except Exception:
            secrets_path = _PROJECT_ROOT / "secrets" / "client_secret.json"

    # Run the OAuth flow
    creds_dict = run_oauth_flow(secrets_path)

    # Apply user overrides
    creds_dict["category_id"] = args.category_id
    creds_dict["privacy_status"] = args.privacy

    # Display summary (redacted)
    print("\n" + "=" * 60)
    print("  YouTube OAuth2 Credentials Generated Successfully")
    print("=" * 60)
    print(f"  Client ID:     {creds_dict['client_id'][:30]}...")
    print(f"  Refresh Token: {creds_dict['refresh_token'][:20]}...")
    print(f"  Category:      {creds_dict['category_id']}")
    print(f"  Privacy:       {creds_dict['privacy_status']}")
    print("=" * 60)

    # Store credentials
    if args.worker_id:
        import asyncio
        asyncio.run(store_in_worker(creds_dict, args.worker_id))
    else:
        save_to_file(creds_dict, args.output)
        print(f"\n[NEXT] To use these credentials:")
        print(f"  Option A: Store via API:")
        print(f"    curl -X PUT http://localhost:8000/api/workers/YOUR_WORKER_ID \\")
        print(f"      -H 'Content-Type: application/json' \\")
        print(f"      -d @{args.output}")
        print(f"\n  Option B: Store directly:")
        print(f"    python scripts/youtube_auth.py --worker-id YOUR_WORKER_ID")


if __name__ == "__main__":
    main()
