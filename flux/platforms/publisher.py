"""Publisher factory — maps (platform, strategy) to concrete publisher."""

from __future__ import annotations

from typing import Any

from flux.logger import get_logger

from .base import PlatformPublisher
from .instagram import (
    InstagramOfficialPublisher,
    InstagramThirdPartyPublisher,
    InstagramUnofficialPublisher,
)
from .tiktok import (
    TikTokOfficialPublisher,
    TikTokThirdPartyPublisher,
    TikTokUnofficialPublisher,
)
from .x import XOfficialPublisher, XThirdPartyPublisher
from .youtube import YouTubeOfficialPublisher, YouTubeThirdPartyPublisher

logger = get_logger(__name__)

_REGISTRY: dict[str, dict[str, type[PlatformPublisher]]] = {
    "youtube": {
        "official": YouTubeOfficialPublisher,
        "third_party": YouTubeThirdPartyPublisher,
    },
    "tiktok": {
        "official": TikTokOfficialPublisher,
        "unofficial": TikTokUnofficialPublisher,
        "third_party": TikTokThirdPartyPublisher,
    },
    "instagram": {
        "official": InstagramOfficialPublisher,
        "unofficial": InstagramUnofficialPublisher,
        "third_party": InstagramThirdPartyPublisher,
    },
    "x": {
        "official": XOfficialPublisher,
        "third_party": XThirdPartyPublisher,
    },
}


def get_publisher(platform: str, strategy: str, credentials: dict[str, Any]) -> PlatformPublisher:
    """Get a publisher instance for the given platform and strategy.

    Args:
        platform: Platform key (youtube, tiktok, instagram, x).
        strategy: Connection strategy (official, unofficial, third_party).
        credentials: Decrypted credential dict for the publisher.

    Returns:
        PlatformPublisher instance.

    Raises:
        ValueError: If platform or strategy is not supported.
    """
    platform = platform.lower()
    strategy = strategy.lower()

    platform_strategies = _REGISTRY.get(platform)
    if not platform_strategies:
        raise ValueError(f"Unsupported platform: {platform}")

    publisher_cls = platform_strategies.get(strategy)
    if not publisher_cls:
        available = ", ".join(platform_strategies.keys())
        raise ValueError(f"Unsupported strategy '{strategy}' for {platform}. Available: {available}")

    return publisher_cls(credentials)


def list_strategies(platform: str) -> list[str]:
    """List available strategies for a platform."""
    return list(_REGISTRY.get(platform.lower(), {}).keys())
