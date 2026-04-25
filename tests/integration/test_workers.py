"""Integration tests for platform worker API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_create_worker(client: AsyncClient):
    """POST /api/workers creates a new worker."""
    response = await client.post(
        "/api/workers",
        json={
            "platform": "telegram",
            "display_name": "Test Channel",
            "credentials": {"token": "test123"},
            "schedule_cron": "0 9 * * *",
            "enabled": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["platform"] == "telegram"
    assert data["display_name"] == "Test Channel"
    assert data["schedule_cron"] == "0 9 * * *"
    assert data["enabled"] is True
    assert "id" in data


@pytest.mark.anyio
async def test_list_workers(client: AsyncClient):
    """GET /api/workers returns all workers."""
    await client.post(
        "/api/workers",
        json={"platform": "youtube", "display_name": "YT Channel"},
    )
    await client.post(
        "/api/workers",
        json={"platform": "telegram", "display_name": "TG Channel"},
    )

    response = await client.get("/api/workers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    platforms = {w["platform"] for w in data}
    assert platforms == {"youtube", "telegram"}


@pytest.mark.anyio
async def test_get_worker(client: AsyncClient):
    """GET /api/workers/{id} returns a single worker."""
    create_resp = await client.post(
        "/api/workers",
        json={"platform": "instagram", "display_name": "IG Account"},
    )
    worker_id = create_resp.json()["id"]

    response = await client.get(f"/api/workers/{worker_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "instagram"
    assert data["display_name"] == "IG Account"


@pytest.mark.anyio
async def test_get_worker_not_found(client: AsyncClient):
    """GET /api/workers/{id} returns 404 for unknown ID."""
    response = await client.get("/api/workers/nonexistent")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_worker(client: AsyncClient):
    """PUT /api/workers/{id} updates worker fields."""
    create_resp = await client.post(
        "/api/workers",
        json={"platform": "x", "display_name": "Old Name", "enabled": True},
    )
    worker_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/workers/{worker_id}",
        json={"display_name": "New Name", "enabled": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "New Name"
    assert data["enabled"] is False


@pytest.mark.anyio
async def test_delete_worker(client: AsyncClient):
    """DELETE /api/workers/{id} removes a worker."""
    create_resp = await client.post(
        "/api/workers",
        json={"platform": "tiktok", "display_name": "TT Account"},
    )
    worker_id = create_resp.json()["id"]

    response = await client.delete(f"/api/workers/{worker_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] == worker_id

    get_resp = await client.get(f"/api/workers/{worker_id}")
    assert get_resp.status_code == 404
