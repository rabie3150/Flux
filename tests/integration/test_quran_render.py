"""Integration tests for Quran plugin render trigger."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from flux.core.lock import _LOCK_FILE
from flux.models import Ingredient, Pipeline, Plugin, ProducedContent
from flux.plugins import load_plugins

_logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def cleanup_render_lock():
    """Remove stale render lock file before each test."""
    try:
        _LOCK_FILE.unlink()
    except (FileNotFoundError, PermissionError, OSError) as e:
        _logger.debug("Cleanup render lock before test: %s", e)
    yield
    try:
        _LOCK_FILE.unlink()
    except (FileNotFoundError, PermissionError, OSError) as e:
        _logger.debug("Cleanup render lock after test: %s", e)


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
    """Create a Quran pipeline with render config."""
    pipeline = Pipeline(
        name="Test Quran Pipeline",
        plugin_id=quran_plugin.id,
        config_json='{"canvas": {"width": 1080, "height": 1920, "fps": 30}}',
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)
    return pipeline


@pytest.fixture
async def approved_clip(
    db_session: AsyncSession, quran_pipeline: Pipeline
) -> Ingredient:
    """Create an approved quran_clip ingredient."""
    ing = Ingredient(
        pipeline_id=quran_pipeline.id,
        type="quran_clip",
        file_path="/tmp/test_clip.mp4",
        source_url="https://youtube.com/shorts/abc123",
        metadata_json='{"yt_id": "abc123"}',
        status="approved",
        duration_secs=45.0,
    )
    db_session.add(ing)
    await db_session.commit()
    await db_session.refresh(ing)
    return ing


@pytest.fixture
async def approved_bg(
    db_session: AsyncSession, quran_pipeline: Pipeline
) -> Ingredient:
    """Create an approved bg_image ingredient."""
    ing = Ingredient(
        pipeline_id=quran_pipeline.id,
        type="bg_image",
        file_path="/tmp/test_bg.jpg",
        source_url="https://pexels.com/photo/123",
        metadata_json='{"source": "pexels"}',
        status="approved",
    )
    db_session.add(ing)
    await db_session.commit()
    await db_session.refresh(ing)
    return ing


@pytest.mark.anyio
async def test_trigger_render_creates_produced_content(
    client: AsyncClient,
    quran_pipeline: Pipeline,
    approved_clip: Ingredient,
    approved_bg: Ingredient,
):
    """POST trigger with action=render creates produced_content from mock render."""
    mock_result = {
        "file_path": "/tmp/rendered.mp4",
        "thumbnail_path": "/tmp/thumb.jpg",
        "duration_secs": 45.0,
        "metadata": {"render_method": "video_compose"},
    }

    with patch(
        "flux.plugins.quran.plugin.render_from_ingredients",
        return_value=mock_result,
    ):
        response = await client.post(
            f"/api/pipelines/{quran_pipeline.id}/trigger",
            json={
                "action": "render",
                "ingredient_ids": [approved_clip.id, approved_bg.id],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_id"] == quran_pipeline.id
    assert data["status"] == "rendered"
    assert data["file_path"] == "/tmp/rendered.mp4"
    assert data["thumbnail_path"] == "/tmp/thumb.jpg"
    assert "content_id" in data


@pytest.mark.anyio
async def test_trigger_render_auto_selects_ingredients(
    client: AsyncClient,
    quran_pipeline: Pipeline,
    approved_clip: Ingredient,
    approved_bg: Ingredient,
):
    """POST trigger with action=render auto-selects approved ingredients if none given."""
    mock_result = {
        "file_path": "/tmp/rendered.mp4",
        "thumbnail_path": "/tmp/thumb.jpg",
        "duration_secs": 45.0,
        "metadata": {"render_method": "video_compose"},
    }

    with patch(
        "flux.plugins.quran.plugin.render_from_ingredients",
        return_value=mock_result,
    ):
        response = await client.post(
            f"/api/pipelines/{quran_pipeline.id}/trigger",
            json={"action": "render"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rendered"


@pytest.mark.anyio
async def test_trigger_render_no_approved_clip(
    client: AsyncClient,
    quran_pipeline: Pipeline,
):
    """POST trigger with action=render returns 400 if no approved clip exists."""
    response = await client.post(
        f"/api/pipelines/{quran_pipeline.id}/trigger",
        json={"action": "render"},
    )

    assert response.status_code == 400
    assert "No approved quran_clip" in response.json()["detail"]


@pytest.mark.anyio
async def test_trigger_render_pipeline_not_found(client: AsyncClient):
    """POST trigger for nonexistent pipeline returns 404."""
    response = await client.post(
        "/api/pipelines/nonexistent/trigger",
        json={"action": "render", "ingredient_ids": ["ing1", "ing2"]},
    )
    assert response.status_code == 404
