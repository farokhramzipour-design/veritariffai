import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.logging_config import configure_logging
from app.infrastructure.database.session import run_migrations_sync

# Configure logging before anything else imports a logger
configure_logging(
    environment=settings.environment,
    log_level="DEBUG" if settings.environment == "local" else "INFO",
)

from app.api.v1.router import api_router
from app.core.errors import APIError, api_error_handler, plan_upgrade_handler, unhandled_exception_handler
from app.domain.plan import PlanUpgradeRequired
from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations_sync()
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
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(api_router, prefix=settings.api_prefix)
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(PlanUpgradeRequired, plan_upgrade_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app


app = create_app()
