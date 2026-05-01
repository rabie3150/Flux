"""TikTok publishing strategies."""

from __future__ import annotations

from typing import Any

from flux.logger import get_logger

from .base import PlatformPublisher, PublishResult

logger = get_logger(__name__)


class TikTokOfficialPublisher(PlatformPublisher):
    """Publish via TikTok for Business API."""

    @property
    def name(self) -> str:
        return "TikTok for Business API"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        logger.info("TikTok official upload starting: %s", file_path)
        # TODO: Implement TikTok Business API video upload
        return PublishResult(
            success=False,
            error="TikTok official publisher not yet implemented",
            transient=False,
        )


class TikTokUnofficialPublisher(PlatformPublisher):
    """Publish via unofficial session/cookie-based methods."""

    @property
    def name(self) -> str:
        return "TikTok (unofficial)"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        logger.info("TikTok unofficial upload starting: %s", file_path)
        # TODO: Mobile automation or cookie-based upload
        return PublishResult(
            success=False,
            error="TikTok unofficial publisher not yet implemented",
            transient=False,
        )


class TikTokThirdPartyPublisher(PlatformPublisher):
    """Publish via third-party service."""

    @property
    def name(self) -> str:
        return f"TikTok via {self.credentials.get('provider', 'third-party')}"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        logger.info("TikTok third-party upload starting: %s", file_path)
        # TODO: Integrate with Buffer/Hootsuite API
        return PublishResult(
            success=False,
            error="TikTok third-party publisher not yet implemented",
            transient=False,
        )
