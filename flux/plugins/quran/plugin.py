"""Dummy Quran Plugin for Phase 0 testing."""

from __future__ import annotations

from typing import Any

from flux.logger import get_logger
from flux.plugins.base import ContentPlugin, RenderResult

logger = get_logger(__name__)


class QuranPlugin(ContentPlugin):
    """A minimal dummy plugin for generating Quran shorts."""

    @property
    def name(self) -> str:
        return "quran_shorts"

    @property
    def display_name(self) -> str:
        return "Quran Shorts (Dummy)"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def ingredient_types(self) -> list[str]:
        return ["audio_recitation", "background_video", "translation_text"]

    async def fetch(
        self, pipeline_id: str, config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Mock fetch."""
        return [
            {
                "type": "audio_recitation",
                "file_path": None,
                "source_url": "https://example.com/audio.mp3",
                "metadata_json": '{"surah": 1, "ayah": 1}',
            }
        ]

    async def render(
        self,
        pipeline_id: str,
        ingredient_ids: list[str],
        config: dict[str, Any],
    ) -> RenderResult:
        """Mock render."""
        return RenderResult(
            file_path=None,  # mock — no actual file
            caption="Bismillah",
            metadata={"mock": True},
        )

    async def identify_content(
        self,
        pipeline_id: str,
        produced_content_id: str,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Mock identify."""
        return {"surah": 1, "ayah": 1}

    async def build_caption(
        self,
        pipeline_id: str,
        produced_content_id: str,
        config: dict[str, Any],
        worker_config: dict[str, Any],
    ) -> str:
        """Mock caption."""
        return "Alhamdulillah"

    def get_config_schema(self) -> dict[str, Any]:
        """Mock schema."""
        return {
            "type": "object",
            "properties": {
                "reciter": {"type": "string"},
            },
        }
