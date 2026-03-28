from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings


logger = logging.getLogger(__name__)


def _build_db_url() -> str:
    if settings.database_url:
        url = settings.database_url
    else:
        url = (
            f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
    # Ensure the async driver is used
    return url.replace("postgresql://", "postgresql+asyncpg://").replace(
        "postgres://", "postgresql+asyncpg://"
    )


engine = create_async_engine(_build_db_url(), pool_pre_ping=True)

AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def run_migrations_sync(*, raise_on_error: bool = False) -> bool:
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        sync_url = (
            _build_db_url()
            .replace("postgresql+asyncpg://", "postgresql+psycopg://")
            .replace("postgres+asyncpg://", "postgresql+psycopg://")
        )
        safe_target = sync_url.split("@")[-1] if "@" in sync_url else sync_url
        logger.info("Running migrations against: %s", safe_target)
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")
        return True
    except Exception:
        logger.exception("Failed to apply Alembic migrations.")
        if raise_on_error:
            raise
        return False


async def get_session() -> AsyncSession:
    async with AsyncSessionMaker() as session:
        yield session
