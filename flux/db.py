"""Database setup for Flux.

Provides async SQLAlchemy engine, session factory, and base declarative class.
WAL mode and foreign keys are enabled on every connection.
"""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)

# Convert sqlite:/// URL to aiosqlite equivalent for async support
_db_url = settings.database_url
if "+aiosqlite" not in _db_url:
    _DATABASE_URL = _db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    _DATABASE_URL = _db_url

engine = create_async_engine(
    _DATABASE_URL,
    echo=False,
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
    cursor.execute("PRAGMA journal_mode")
    row = cursor.fetchone()
    if row and row[0].lower() != "wal":
        logger.warning("Failed to enable WAL mode. Current mode: %s", row[0])
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def _migrate_columns() -> None:
    """Add columns that may be missing from existing SQLite tables."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        # PlatformWorker migrations
        result = await conn.execute(
            text("PRAGMA table_info(platform_workers)")
        )
        columns = {row[1] for row in result.fetchall()}

        if "connection_strategy" not in columns:
            await conn.execute(
                text("ALTER TABLE platform_workers ADD COLUMN connection_strategy VARCHAR(32) NOT NULL DEFAULT 'official'")
            )
            logger.info("Migration: added connection_strategy to platform_workers")

        if "third_party_provider" not in columns:
            await conn.execute(
                text("ALTER TABLE platform_workers ADD COLUMN third_party_provider VARCHAR(32)")
            )
            logger.info("Migration: added third_party_provider to platform_workers")


async def init_db() -> None:
    """Create all tables. Call once at application startup."""
    import flux.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_columns()
    logger.info("Database tables created/verified")


async def get_db() -> AsyncSession:
    """FastAPI dependency yielding database sessions."""
    async with AsyncSessionLocal() as session:
        yield session
