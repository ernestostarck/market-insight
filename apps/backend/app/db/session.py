from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# The DATABASE_URL should be in the format: "postgresql+asyncpg://user:password@host/db"
async_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
# expire_on_commit=False: with AsyncSession, touching an expired attribute after commit
# would trigger implicit (sync) IO and fail with MissingGreenlet.
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
