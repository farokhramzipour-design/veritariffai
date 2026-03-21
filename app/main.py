from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.router import api_router
from app.core.errors import APIError, api_error_handler, plan_upgrade_handler, unhandled_exception_handler
from app.domain.plan import PlanUpgradeRequired
from app.core.responses import ok
from app.core.middleware import RateLimitMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    
    # Configure CORS
    origins = settings.cors_origins if settings.cors_origins else ["*"]
    # allow_credentials=True is incompatible with allow_origins=["*"];
    # when origins is the wildcard we must set credentials to False.
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
