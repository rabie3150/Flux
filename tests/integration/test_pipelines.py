"""Integration tests for pipeline API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from flux.models import Plugin


@pytest.fixture
async def sample_plugin(db_session: AsyncSession) -> Plugin:
    """Create a test plugin."""
    plugin = Plugin(
        name="test_plugin",
        display_name="Test Plugin",
        version="1.0.0",
        api_version="1",
        module_path="flux.plugins.test",
    )
    db_session.add(plugin)
    await db_session.commit()
    await db_session.refresh(plugin)
    return plugin


@pytest.mark.anyio
async def test_create_pipeline(client: AsyncClient, sample_plugin: Plugin):
    """POST /api/pipelines creates a new pipeline."""
    response = await client.post(
        "/api/pipelines",
        json={
            "name": "Test Pipeline",
            "plugin_id": sample_plugin.id,
            "config": {"key": "value"},
            "enabled": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Pipeline"
    assert data["plugin_id"] == sample_plugin.id
    assert data["enabled"] is True
    assert "id" in data


@pytest.mark.anyio
async def test_list_pipelines(client: AsyncClient, sample_plugin: Plugin):
    """GET /api/pipelines returns all pipelines."""
    # Create two pipelines
    await client.post(
        "/api/pipelines",
        json={"name": "Pipeline A", "plugin_id": sample_plugin.id},
    )
    await client.post(
        "/api/pipelines",
        json={"name": "Pipeline B", "plugin_id": sample_plugin.id},
    )

    response = await client.get("/api/pipelines")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = {p["name"] for p in data}
    assert names == {"Pipeline A", "Pipeline B"}


@pytest.mark.anyio
async def test_get_pipeline(client: AsyncClient, sample_plugin: Plugin):
    """GET /api/pipelines/{id} returns a single pipeline."""
    create_resp = await client.post(
        "/api/pipelines",
        json={"name": "My Pipeline", "plugin_id": sample_plugin.id},
    )
    pipeline_id = create_resp.json()["id"]

    response = await client.get(f"/api/pipelines/{pipeline_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Pipeline"
    assert data["id"] == pipeline_id


@pytest.mark.anyio
async def test_get_pipeline_not_found(client: AsyncClient):
    """GET /api/pipelines/{id} returns 404 for unknown ID."""
    response = await client.get("/api/pipelines/nonexistent")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_pipeline(client: AsyncClient, sample_plugin: Plugin):
    """PUT /api/pipelines/{id} updates pipeline fields."""
    create_resp = await client.post(
        "/api/pipelines",
        json={"name": "Old Name", "plugin_id": sample_plugin.id, "enabled": True},
    )
    pipeline_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/pipelines/{pipeline_id}",
        json={"name": "New Name", "enabled": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["enabled"] is False


@pytest.mark.anyio
async def test_delete_pipeline(client: AsyncClient, sample_plugin: Plugin):
    """DELETE /api/pipelines/{id} removes a pipeline."""
    create_resp = await client.post(
        "/api/pipelines",
        json={"name": "To Delete", "plugin_id": sample_plugin.id},
    )
    pipeline_id = create_resp.json()["id"]

    response = await client.delete(f"/api/pipelines/{pipeline_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] == pipeline_id

    # Verify it's gone
    get_resp = await client.get(f"/api/pipelines/{pipeline_id}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_pipeline_stats(client: AsyncClient, sample_plugin: Plugin):
    """GET /api/pipelines/{id}/stats returns stock levels."""
    create_resp = await client.post(
        "/api/pipelines",
        json={"name": "Stats Pipe", "plugin_id": sample_plugin.id},
    )
    pipeline_id = create_resp.json()["id"]

    response = await client.get(f"/api/pipelines/{pipeline_id}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_id"] == pipeline_id
    assert "stock" in data
    assert data["stock"]["approved"] == 0
    assert data["stock"]["pending"] == 0
    assert data["stock"]["rejected"] == 0
