import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.core.errors import APIError, api_error_handler, plan_upgrade_handler, unhandled_exception_handler
from app.domain.plan import PlanUpgradeRequired
from app.core.middleware import RateLimitMiddleware

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    """Apply all pending Alembic migrations synchronously at startup."""
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        # Override the URL so alembic.ini doesn't need updating per environment
        from app.infrastructure.database.session import _build_db_url
        sync_url = _build_db_url().replace("+asyncpg", "+psycopg").replace("+aiosqlite", "")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully.")
    except Exception:
        logger.exception("Failed to apply Alembic migrations — the app will still start.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    # Configure CORS
    origins = settings.cors_origins if settings.cors_origins else ["*"]
    # allow_credentials=True is incompatible with allow_origins=["*"]
    allow_credentials = origins != ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # app.add_middleware(RateLimitMiddleware)
    app.include_router(api_router, prefix=settings.api_prefix)
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(PlanUpgradeRequired, plan_upgrade_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app


app = create_app()
