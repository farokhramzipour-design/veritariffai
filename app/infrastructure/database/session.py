from __future__ import annotations
import logging
import sqlalchemy as sa
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


def _ensure_alembic_version_capacity(conn) -> None:
    row = conn.execute(
        sa.text(
            """
            SELECT data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'alembic_version'
              AND column_name = 'version_num'
            """
        )
    ).fetchone()
    if not row:
        return
    data_type, max_len = row[0], row[1]
    if data_type == "character varying" and max_len is not None and int(max_len) < 64:
        conn.execute(sa.text("ALTER TABLE public.alembic_version ALTER COLUMN version_num TYPE varchar(128)"))
        conn.commit()


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
        try:
            engine_sync = sa.create_engine(sync_url, pool_pre_ping=True)
            with engine_sync.connect() as conn:
                _ensure_alembic_version_capacity(conn)
        except Exception:
            logger.exception("Failed to ensure alembic_version.version_num capacity.")
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
