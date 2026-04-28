"""Integration tests for Quran plugin fetch trigger."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from flux.models import Pipeline, Plugin
from flux.plugins import load_plugins


@pytest.fixture(scope="session", autouse=True)
def load_quran_plugin():
    """Ensure plugins are loaded before any test runs."""
    load_plugins()


@pytest.fixture
async def quran_plugin(db_session: AsyncSession) -> Plugin:
    """Create the quran_shorts plugin record."""
    plugin = Plugin(
        name="quran_shorts",
        display_name="Quran Shorts",
        version="1.0.0",
        api_version="1",
        module_path="flux.plugins.quran",
    )
    db_session.add(plugin)
    await db_session.commit()
    await db_session.refresh(plugin)
    return plugin


@pytest.fixture
async def quran_pipeline(
    db_session: AsyncSession, quran_plugin: Plugin
) -> Pipeline:
    """Create a Quran pipeline with fetch config."""
    pipeline = Pipeline(
        name="Test Quran Pipeline",
        plugin_id=quran_plugin.id,
        config_json='{"source_channels": ["https://youtube.com/@test"], "max_clips_per_fetch": 5, "bg_sources": {"pexels_keywords": ["nature"]}}',
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)
    return pipeline


@pytest.mark.anyio
async def test_trigger_fetch_creates_ingredients(
    client: AsyncClient,
    quran_pipeline: Pipeline,
):
    """POST trigger with action=fetch creates ingredients from plugin results."""
    mock_clip = {
        "type": "quran_clip",
        "file_path": "/tmp/test_clip.mp4",
        "source_url": "https://youtube.com/shorts/abc123",
        "metadata": {"yt_id": "abc123", "title": "Test Clip"},
        "file_size_bytes": 1024,
        "duration_secs": 45.0,
    }
    mock_bg = {
        "type": "bg_image",
        "file_path": "/tmp/test_bg.jpg",
        "source_url": "https://pexels.com/photo/123",
        "metadata": {"source": "pexels", "media_id": "123"},
        "file_size_bytes": 512,
        "duration_secs": None,
    }

    with patch("flux.plugins.quran.plugin.fetch_clips", return_value=[mock_clip]):
        with patch(
            "flux.plugins.quran.plugin.fetch_backgrounds", return_value=[mock_bg]
        ):
            response = await client.post(
                f"/api/pipelines/{quran_pipeline.id}/trigger",
                json={"action": "fetch"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_id"] == quran_pipeline.id
    assert data["created"] == 2


@pytest.mark.anyio
async def test_trigger_fetch_pipeline_not_found(client: AsyncClient):
    """POST trigger for nonexistent pipeline returns 404."""
    response = await client.post(
        "/api/pipelines/nonexistent/trigger",
        json={"action": "fetch"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_trigger_unknown_action_returns_400(
    client: AsyncClient,
    quran_pipeline: Pipeline,
):
    """POST trigger with unknown action returns 400."""
    response = await client.post(
        f"/api/pipelines/{quran_pipeline.id}/trigger",
        json={"action": "dance"},
    )
    assert response.status_code == 400
    assert "Unknown action" in response.json()["detail"]


@pytest.mark.anyio
async def test_trigger_render_no_ingredients(
    client: AsyncClient,
    quran_pipeline: Pipeline,
):
    """POST trigger with action=render returns 400 when no approved ingredients exist."""
    response = await client.post(
        f"/api/pipelines/{quran_pipeline.id}/trigger",
        json={"action": "render"},
    )
    assert response.status_code == 400
    assert "No approved quran_clip" in response.json()["detail"]
