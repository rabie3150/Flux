"""Instagram publishing strategies."""

from __future__ import annotations

from typing import Any

from flux.logger import get_logger

from .base import PlatformPublisher, PublishResult

logger = get_logger(__name__)


class InstagramOfficialPublisher(PlatformPublisher):
    """Publish via Instagram Graph API (Facebook)."""

    @property
    def name(self) -> str:
        return "Instagram Graph API"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        logger.info("Instagram official upload starting: %s", file_path)
        # TODO: Implement Facebook Graph API reel/video upload
        return PublishResult(
            success=False,
            error="Instagram official publisher not yet implemented",
            transient=False,
        )


class InstagramUnofficialPublisher(PlatformPublisher):
    """Publish via Instagrapi (unofficial)."""

    @property
    def name(self) -> str:
        return "Instagram (Instagrapi)"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        logger.info("Instagram unofficial upload starting: %s", file_path)
        # TODO: Implement Instagrapi session-based upload
        return PublishResult(
            success=False,
            error="Instagram unofficial publisher not yet implemented",
            transient=False,
        )


class InstagramThirdPartyPublisher(PlatformPublisher):
    """Publish via third-party service."""

    @property
    def name(self) -> str:
        return f"Instagram via {self.credentials.get('provider', 'third-party')}"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        logger.info("Instagram third-party upload starting: %s", file_path)
        # TODO: Integrate with Buffer/Hootsuite API
        return PublishResult(
            success=False,
            error="Instagram third-party publisher not yet implemented",
            transient=False,
        )
