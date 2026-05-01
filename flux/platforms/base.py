"""Base class for platform publishers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PublishResult:
    """Result of a publish attempt."""

    def __init__(
        self,
        success: bool,
        post_id: str | None = None,
        url: str | None = None,
        error: str | None = None,
        transient: bool = False,
    ):
        self.success = success
        self.post_id = post_id
        self.url = url
        self.error = error
        self.transient = transient  # If True, retry is warranted


class PlatformPublisher(ABC):
    """Abstract base for all platform publishing strategies."""

    def __init__(self, credentials: dict[str, Any]):
        self.credentials = credentials

    @abstractmethod
    async def publish(
        self,
        file_path: str,
        caption: str,
        thumbnail_path: str | None = None,
    ) -> PublishResult:
        """Publish content to the platform.

        Args:
            file_path: Path to the rendered video file.
            caption: Caption text for the post.
            thumbnail_path: Optional path to thumbnail image.

        Returns:
            PublishResult with success status, post ID, URL, and error info.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this publisher strategy."""
        ...
