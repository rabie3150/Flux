"""Database setup for Flux.

Provides async SQLAlchemy engine, session factory, and base declarative class.
WAL mode and foreign keys are enabled on every connection.
"""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from flux.config import settings

# Convert sqlite:/// URL to aiosqlite equivalent for async support
_DATABASE_URL = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(
    _DATABASE_URL,
    echo=settings.flux_env == "development",
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record) -> None:
    """Enable WAL mode and foreign keys on every connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def init_db() -> None:
    """Create all tables. Call once at application startup."""
    # Import models so they register with Base.metadata
    import flux.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency yielding database sessions."""
    async with AsyncSessionLocal() as session:
        yield session
