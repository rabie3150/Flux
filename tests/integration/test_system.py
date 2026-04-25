"""Integration tests for system API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_endpoint(client: AsyncClient):
    """GET /api/system/health returns healthy status."""
    response = await client.get("/api/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "version" in data
    assert "environment" in data


@pytest.mark.anyio
async def test_dashboard_empty(client: AsyncClient):
    """GET /api/system/dashboard returns zero counts when empty."""
    response = await client.get("/api/system/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["pipelines"] == 0
    assert data["workers"] == 0
    assert data["recent_events"] == []


@pytest.mark.anyio
async def test_settings_crud(client: AsyncClient):
    """Settings can be created, updated, listed, and deleted."""
    # Create setting
    resp = await client.put("/api/system/settings/fetch_interval", json={"value": 3600})
    assert resp.status_code == 200
    data = resp.json()
    assert "fetch_interval" in data

    # List settings
    list_resp = await client.get("/api/system/settings")
    assert list_resp.status_code == 200
    settings = list_resp.json()
    assert "fetch_interval" in settings

    # Update setting
    update_resp = await client.put(
        "/api/system/settings/fetch_interval", json={"value": 7200}
    )
    assert update_resp.status_code == 200

    # Delete setting
    del_resp = await client.delete("/api/system/settings/fetch_interval")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] == "fetch_interval"

    # Verify deleted
    list_after = await client.get("/api/system/settings")
    assert "fetch_interval" not in list_after.json()


@pytest.mark.anyio
async def test_delete_setting_not_found(client: AsyncClient):
    """DELETE nonexistent setting returns 404."""
    response = await client.delete("/api/system/settings/nonexistent")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_activity_log_empty(client: AsyncClient):
    """GET /api/system/activity returns empty list initially."""
    response = await client.get("/api/system/activity")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["events"] == []
    assert data["limit"] == 50
    assert data["offset"] == 0
