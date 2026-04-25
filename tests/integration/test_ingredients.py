"""Integration tests for ingredient API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from flux.models import Ingredient, Pipeline, Plugin


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


@pytest.fixture
async def sample_pipeline(
    db_session: AsyncSession, sample_plugin: Plugin
) -> Pipeline:
    """Create a test pipeline."""
    pipeline = Pipeline(
        name="Test Pipeline",
        plugin_id=sample_plugin.id,
        config_json="{}",
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)
    return pipeline


@pytest.fixture
async def sample_ingredients(
    db_session: AsyncSession, sample_pipeline: Pipeline
) -> list[Ingredient]:
    """Create test ingredients in various statuses."""
    ingredients = []
    for i, status in enumerate(["pending", "pending", "approved", "rejected"]):
        ing = Ingredient(
            pipeline_id=sample_pipeline.id,
            type="test_clip",
            file_path=f"/tmp/test_{i}.mp4",
            source_url=f"https://example.com/{i}",
            status=status,
            file_size_bytes=1024 * (i + 1),
        )
        ingredients.append(ing)
    db_session.add_all(ingredients)
    await db_session.commit()
    for ing in ingredients:
        await db_session.refresh(ing)
    return ingredients


@pytest.mark.anyio
async def test_list_ingredients(
    client: AsyncClient,
    sample_pipeline: Pipeline,
    sample_ingredients: list[Ingredient],
):
    """GET /api/pipelines/{id}/ingredients returns ingredients."""
    response = await client.get(
        f"/api/pipelines/{sample_pipeline.id}/ingredients"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_id"] == sample_pipeline.id
    assert data["count"] == 4


@pytest.mark.anyio
async def test_list_ingredients_with_status_filter(
    client: AsyncClient,
    sample_pipeline: Pipeline,
    sample_ingredients: list[Ingredient],
):
    """Filtering by status returns only matching ingredients."""
    response = await client.get(
        f"/api/pipelines/{sample_pipeline.id}/ingredients?status=pending"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    for ing in data["ingredients"]:
        assert ing["status"] == "pending"


@pytest.mark.anyio
async def test_approve_ingredients(
    client: AsyncClient,
    sample_pipeline: Pipeline,
    sample_ingredients: list[Ingredient],
):
    """POST approve marks ingredients as approved."""
    pending_ids = [ing.id for ing in sample_ingredients if ing.status == "pending"]

    response = await client.post(
        f"/api/pipelines/{sample_pipeline.id}/ingredients/approve",
        json={"ingredient_ids": pending_ids},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["approved"] == 2

    # Verify status changed
    list_resp = await client.get(
        f"/api/pipelines/{sample_pipeline.id}/ingredients?status=approved"
    )
    assert list_resp.json()["count"] == 3  # 1 originally + 2 newly approved


@pytest.mark.anyio
async def test_reject_ingredients(
    client: AsyncClient,
    sample_pipeline: Pipeline,
    sample_ingredients: list[Ingredient],
):
    """POST reject marks ingredients as rejected."""
    pending_ids = [ing.id for ing in sample_ingredients if ing.status == "pending"]

    response = await client.post(
        f"/api/pipelines/{sample_pipeline.id}/ingredients/reject",
        json={"ingredient_ids": pending_ids},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rejected"] == 2

    # Verify status changed (1 originally rejected + 2 newly rejected = 3)
    list_resp = await client.get(
        f"/api/pipelines/{sample_pipeline.id}/ingredients?status=rejected"
    )
    assert list_resp.json()["count"] == 3


@pytest.mark.anyio
async def test_delete_ingredients(
    client: AsyncClient,
    sample_pipeline: Pipeline,
    sample_ingredients: list[Ingredient],
):
    """DELETE removes ingredients physically."""
    all_ids = [ing.id for ing in sample_ingredients[:2]]

    response = await client.request(
        "DELETE",
        f"/api/pipelines/{sample_pipeline.id}/ingredients",
        json={"ingredient_ids": all_ids},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] == 2

    # Verify count decreased
    list_resp = await client.get(
        f"/api/pipelines/{sample_pipeline.id}/ingredients"
    )
    assert list_resp.json()["count"] == 2
