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
    result = cursor.execute("PRAGMA journal_mode=WAL")
    row = result.fetchone()
    if row and row[0].lower() != "wal":
        logger.warning("Failed to enable WAL mode. Current mode: %s", row[0])
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def init_db() -> None:
    """Create all tables. Call once at application startup."""
    # Import models so they register with Base.metadata
    import flux.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def get_db() -> AsyncSession:
    """FastAPI dependency yielding database sessions."""
    async with AsyncSessionLocal() as session:
        yield session
