"""Flux plugin base interface.

All content plugins must implement ContentPlugin. The core engine knows nothing
about Quran verses, Hadith, or News — it only knows pipelines, ingredients,
renders, and posts. Plugins provide the content-specific logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RenderResult:
    """Standardized output from any plugin's render() method."""

    file_path: str | None = None
    thumbnail_path: str | None = None
    caption: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    attachments: list[str] = field(default_factory=list)


class ContentPlugin(ABC):
    """Abstract base class for all Flux content plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier (e.g., 'quran_shorts')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Quran Shorts')."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string."""
        ...

    @property
    @abstractmethod
    def ingredient_types(self) -> list[str]:
        """List of ingredient type strings this plugin produces."""
        ...

    @abstractmethod
    async def fetch(
        self, pipeline_id: str, config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Fetch new ingredients from external sources.

        Returns list of ingredient metadata dicts. Each dict must contain:
        - type: str — ingredient type
        - file_path: str | None — local file path (or None if text-only)
        - source_url: str | None — original source URL
        - metadata_json: str — plugin-defined metadata as JSON string

        The core engine inserts these into the ingredients table
        with status='pending'.
        """
        ...

    @abstractmethod
    async def render(
        self,
        pipeline_id: str,
        ingredient_ids: list[str],
        config: dict[str, Any],
    ) -> RenderResult:
        """Compose final content from approved ingredients.

        Returns RenderResult with file paths, caption, and metadata.
        The core engine stores this in produced_content.
        """
        ...

    @abstractmethod
    async def identify_content(
        self,
        pipeline_id: str,
        produced_content_id: str,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Identify the semantic content of a produced item.

        May set review flags in metadata (e.g., {"review_flag": True}).
        Returns identification data dict, or None if unknown.
        """
        ...

    @abstractmethod
    async def build_caption(
        self,
        pipeline_id: str,
        produced_content_id: str,
        config: dict[str, Any],
        worker_config: dict[str, Any],
    ) -> str:
        """Generate the final text caption for a specific platform worker.

        Returns caption string. The core engine truncates to platform limits
        if needed.
        """
        ...

    @abstractmethod
    def get_config_schema(self) -> dict[str, Any]:
        """Return JSONSchema for this plugin's pipeline configuration.

        The admin UI uses this to generate configuration forms.
        """
        ...
