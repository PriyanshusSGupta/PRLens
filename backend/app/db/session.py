from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

_engine = None
_session_factory = None


def _build_url(db_url: str) -> str:
    if db_url.startswith("postgresql://"):
        url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        url = url.replace("?sslmode=require", "")
        return url
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    return db_url


def get_engine():
    global _engine
    if _engine is None:
        url = _build_url(settings.database_url)
        _engine = create_async_engine(url, echo=settings.log_level == "DEBUG")
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncSession:
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
