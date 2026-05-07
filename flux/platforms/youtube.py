"""YouTube publishing strategies.

Official publisher uses YouTube Data API v3 with OAuth2.
Credentials are stored encrypted in the worker's credentials_json field.

Required pip packages (already in requirements.txt):
    google-api-python-client>=2.120.0
    google-auth-oauthlib>=1.2.0
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from flux.logger import get_logger

from .base import PlatformPublisher, PublishResult

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_API_SERVICE_NAME = "youtube"
_API_VERSION = "v3"
_DEFAULT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
_MAX_CHUNK_RETRIES = 3
_YOUTUBE_TITLE_LIMIT = 100
_YOUTUBE_DESC_LIMIT = 5000
_YOUTUBE_TAG_LIMIT = 500  # total chars across all tags


# ---------------------------------------------------------------------------
# Internal helpers (synchronous — run via asyncio.to_thread)
# ---------------------------------------------------------------------------


def _build_credentials(creds_dict: dict[str, Any]):
    """Build a google.oauth2.credentials.Credentials from the stored dict.

    The dict is the decrypted version of platform_workers.credentials_json
    and must contain at minimum: client_id, client_secret, refresh_token.
    """
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=creds_dict.get("token"),
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get(
            "token_uri", "https://oauth2.googleapis.com/token"
        ),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
        scopes=creds_dict.get("scopes", _DEFAULT_SCOPES),
    )


def _refresh_if_needed(credentials) -> str | None:
    """Refresh credentials if expired.

    Returns:
        None on success, or an error string on failure.
    """
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request

    if credentials.valid:
        return None

    if not credentials.refresh_token:
        return (
            "YouTube credentials expired and no refresh_token available. "
            "Re-run the OAuth consent flow."
        )

    try:
        credentials.refresh(Request())
        logger.info("YouTube OAuth access token refreshed successfully")
        return None
    except RefreshError as exc:
        detail = str(exc).lower()
        if "invalid_grant" in detail:
            return (
                "YouTube refresh token is invalid (revoked or expired). "
                "Delete the worker and re-authenticate via OAuth."
            )
        return f"YouTube credential refresh failed: {exc}"
    except Exception as exc:
        return f"Unexpected error refreshing YouTube credentials: {exc}"


def _do_upload(
    creds_dict: dict[str, Any],
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str,
    privacy_status: str,
) -> PublishResult:
    """Synchronous YouTube upload — called via asyncio.to_thread().

    Implements resumable upload with chunk-level retries and proper
    error classification matching Flux's transient/permanent model.
    """
    import googleapiclient.discovery
    import googleapiclient.errors
    import googleapiclient.http

    # ── 1. Build & refresh credentials ─────────────────────────────────
    credentials = _build_credentials(creds_dict)
    refresh_error = _refresh_if_needed(credentials)
    if refresh_error:
        return PublishResult(
            success=False,
            error=refresh_error,
            transient=False,  # Auth failure is permanent
        )

    # ── 2. Build API service ───────────────────────────────────────────
    try:
        service = googleapiclient.discovery.build(
            _API_SERVICE_NAME, _API_VERSION, credentials=credentials
        )
    except Exception as exc:
        return PublishResult(
            success=False,
            error=f"Failed to build YouTube API service: {exc}",
            transient=False,
        )

    # ── 3. Validate video file ─────────────────────────────────────────
    video_path = Path(file_path)
    if not video_path.exists():
        return PublishResult(
            success=False,
            error=f"Video file not found: {file_path}",
            transient=False,
        )

    # ── 4. Build request body ──────────────────────────────────────────
    body = {
        "snippet": {
            "title": title[:_YOUTUBE_TITLE_LIMIT],
            "description": description[:_YOUTUBE_DESC_LIMIT],
            "tags": tags if tags else [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media_body = googleapiclient.http.MediaFileUpload(
        file_path, chunksize=-1, resumable=True
    )

    insert_request = service.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media_body,
    )

    logger.info(
        "Starting YouTube resumable upload: title='%s', file='%s', privacy='%s'",
        title[:60],
        video_path.name,
        privacy_status,
    )

    # ── 5. Resumable upload loop ───────────────────────────────────────
    response = None
    retries = 0

    while response is None:
        try:
            status, response = insert_request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info("YouTube upload progress: %d%%", progress)
        except googleapiclient.errors.HttpError as exc:
            # ── Quota / rate-limit errors → transient ──
            error_body = _parse_api_error(exc)
            if error_body:
                reason = error_body.get("reason", "")
                if reason in ("uploadLimitExceeded", "quotaExceeded"):
                    return PublishResult(
                        success=False,
                        error=f"YouTube API quota exceeded ({reason})",
                        transient=True,  # Will resolve tomorrow
                    )
                if reason in ("rateLimitExceeded",):
                    return PublishResult(
                        success=False,
                        error=f"YouTube rate limit exceeded ({reason})",
                        transient=True,
                    )

            # ── Retryable server errors (5xx) ──
            http_status = exc.resp.status
            if http_status in (500, 502, 503, 504) and retries < _MAX_CHUNK_RETRIES:
                retries += 1
                logger.warning(
                    "YouTube upload HTTP %d (retry %d/%d): %s",
                    http_status,
                    retries,
                    _MAX_CHUNK_RETRIES,
                    _safe_error_content(exc),
                )
                continue

            # ── Auth / permission errors → permanent ──
            if http_status in (401, 403):
                return PublishResult(
                    success=False,
                    error=(
                        f"YouTube auth/permission error (HTTP {http_status}): "
                        f"{_safe_error_content(exc)}"
                    ),
                    transient=False,
                )

            # ── All other HTTP errors → permanent ──
            return PublishResult(
                success=False,
                error=(
                    f"YouTube upload HTTP error {http_status}: "
                    f"{_safe_error_content(exc)}"
                ),
                transient=False,
            )
        except Exception as exc:
            return PublishResult(
                success=False,
                error=f"Unexpected error during YouTube upload: {exc}",
                transient=False,
            )

    # ── 6. Validate response ───────────────────────────────────────────
    if not response:
        return PublishResult(
            success=False,
            error="YouTube upload completed but received empty response",
            transient=False,
        )

    video_id = response.get("id")
    if not video_id:
        return PublishResult(
            success=False,
            error=(
                "YouTube upload completed but no video ID in response: "
                + json.dumps(response)[:300]
            ),
            transient=False,
        )

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    logger.info(
        "YouTube upload successful: '%s' → %s (video ID: %s)",
        title[:60],
        video_url,
        video_id,
    )

    return PublishResult(
        success=True,
        post_id=video_id,
        url=video_url,
    )


def _parse_api_error(exc) -> dict[str, Any] | None:
    """Extract the first error entry from a Google API HttpError."""
    try:
        body = json.loads(exc.content.decode())
        errors = body.get("error", {}).get("errors", [])
        if errors:
            return errors[0]
    except (json.JSONDecodeError, AttributeError, KeyError, UnicodeDecodeError):
        pass
    return None


def _safe_error_content(exc, max_len: int = 300) -> str:
    """Get a truncated, safe-to-log error message from an HttpError."""
    try:
        return exc.content.decode()[:max_len]
    except Exception:
        return str(exc)[:max_len]


# ---------------------------------------------------------------------------
# Public publisher classes
# ---------------------------------------------------------------------------


class YouTubeOfficialPublisher(PlatformPublisher):
    """Publish via YouTube Data API v3 (OAuth2 resumable upload).

    Expected credentials_json structure (stored encrypted in DB)::

        {
            "client_id":     "xxx.apps.googleusercontent.com",
            "client_secret": "GOCSPX-xxx",
            "refresh_token": "1//0xxx",
            "token":         "ya29.xxx",          # access token (auto-refreshed)
            "token_uri":     "https://oauth2.googleapis.com/token",
            "scopes":        ["https://www.googleapis.com/auth/youtube.upload"],
            "category_id":   "27",                 # optional — default "27" (Education)
            "privacy_status": "public",            # optional — default "public"
            "tags":          ["quran", "islam"]     # optional — default tags
        }

    Initial OAuth setup:
        1. Download ``client_secret.json`` from Google Cloud Console.
        2. Run the one-time OAuth consent flow on a machine with a browser
           (see ``scripts/youtube_auth.py`` or use the admin panel).
        3. Store the resulting credentials in the worker via the admin API.
    """

    @property
    def name(self) -> str:
        return "YouTube Data API v3"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        # ── Validate required fields ──────────────────────────────────
        missing = [
            k
            for k in ("client_id", "client_secret", "refresh_token")
            if not self.credentials.get(k)
        ]
        if missing:
            return PublishResult(
                success=False,
                error=(
                    f"YouTube credentials missing required fields: "
                    f"{', '.join(missing)}. Complete the OAuth flow first."
                ),
                transient=False,
            )

        # ── Extract title & description from caption ──────────────────
        # Convention: first line of plugin caption → YouTube title,
        #             full caption → YouTube description.
        lines = caption.strip().split("\n", 1)
        title = lines[0].strip() if lines else "Untitled"
        description = caption

        # ── Read YouTube-specific config from credentials dict ────────
        category_id = str(self.credentials.get("category_id", "27"))
        privacy_status = self.credentials.get("privacy_status", "public")
        tags = self.credentials.get("tags", [])

        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        logger.info(
            "YouTube official upload starting: file=%s, title='%s'",
            file_path,
            title[:60],
        )

        # ── Run synchronous Google API upload in a thread ─────────────
        # google-api-python-client is not async-compatible, so we offload
        # the blocking I/O to a thread to keep the event loop responsive.
        return await asyncio.to_thread(
            _do_upload,
            creds_dict=self.credentials,
            file_path=file_path,
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,
            privacy_status=privacy_status,
        )


class YouTubeThirdPartyPublisher(PlatformPublisher):
    """Publish via third-party service (Buffer, Hootsuite, etc.)."""

    @property
    def name(self) -> str:
        return f"YouTube via {self.credentials.get('provider', 'third-party')}"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        logger.info("YouTube third-party upload starting: %s", file_path)
        # TODO: Integrate with Buffer/Hootsuite API
        return PublishResult(
            success=False,
            error="YouTube third-party publisher not yet implemented",
            transient=False,
        )
