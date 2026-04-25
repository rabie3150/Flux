"""Unit tests for the health endpoint."""

import pytest
from httpx import AsyncClient, ASGITransport

from flux.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health_returns_200(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_health_response_shape(client: AsyncClient):
    response = await client.get("/api/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "version" in data
    assert "environment" in data
