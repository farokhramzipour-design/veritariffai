from typing import List, Dict, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    app_name: str = "Trade Cost Engine"
    api_prefix: str = "/api/v1"
    environment: str = Field(default="local")
    secret_key: str = Field(default="dev-secret")
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str | None = None
    celery_backend_url: str | None = None
    cors_origins: List[str] = Field(default_factory=list)
    jwt_issuer: Optional[str] = None
    jwt_audience: Optional[str] = None
    jwt_algorithm: str = "RS256"
    jwt_public_keys: Dict[str, str] = Field(default_factory=dict)
    rate_limit_enabled: bool = True
    rate_limit_hourly_default: int = 1000
    stripe_webhook_secret: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
