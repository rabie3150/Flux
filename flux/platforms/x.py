"""X / Twitter publishing strategies."""

from __future__ import annotations

from typing import Any

from flux.logger import get_logger

from .base import PlatformPublisher, PublishResult

logger = get_logger(__name__)


class XOfficialPublisher(PlatformPublisher):
    """Publish via X API v2."""

    @property
    def name(self) -> str:
        return "X API v2"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        logger.info("X official upload starting: %s", file_path)
        # TODO: Implement X API v2 media upload + tweet
        return PublishResult(
            success=False,
            error="X official publisher not yet implemented",
            transient=False,
        )


class XThirdPartyPublisher(PlatformPublisher):
    """Publish via third-party service."""

    @property
    def name(self) -> str:
        return f"X via {self.credentials.get('provider', 'third-party')}"

    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        logger.info("X third-party upload starting: %s", file_path)
        # TODO: Integrate with Buffer/Hootsuite API
        return PublishResult(
            success=False,
            error="X third-party publisher not yet implemented",
            transient=False,
        )
