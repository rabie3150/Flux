"""Shared test fixtures for Flux."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from flux.db import Base, get_db
from flux.main import app

# Test database (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
_test_session_maker = async_sessionmaker(
    _test_engine, expire_on_commit=False, autocommit=False, autoflush=False
)


async def _create_tables() -> None:
    """Create all tables in the test database."""
    import flux.models  # noqa: F401

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _drop_tables() -> None:
    """Drop all tables from the test database."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a test database session."""
    async with _test_session_maker() as session:
        yield session


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    await _create_tables()
    yield
    await _drop_tables()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with _test_session_maker() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP test client with test DB override."""
    app.dependency_overrides[get_db] = _get_test_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
