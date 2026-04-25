"""Database setup for Flux."""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from flux.config import settings

# Convert sqlite:/// URL to aiosqlite equivalent
_DATABASE_URL = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(
    _DATABASE_URL,
    echo=settings.flux_env == "development",
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode on every connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def get_db() -> AsyncSession:
    """Dependency for FastAPI endpoints."""
    async with AsyncSessionLocal() as session:
        yield session
