from typing import List, Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Trade Cost Engine"
    api_prefix: str = "/api/v1"
    environment: str = Field(default="local")
    debug: bool = Field(default=False, description="Include exception details in 500 responses")
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
    
    # Database settings
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "tce"
    postgres_host: str = "localhost"
    postgres_port: str = "5432"
    database_url: Optional[str] = None

    # Google Auth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: Optional[str] = None

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    # Import Analysis API
    openai_classification_model: str = "gpt-4o"
    import_analysis_confidence_threshold: float = 0.75
    
    # External Tariff APIs
    hmrc_api_key: Optional[str] = None
    taric_api_key: Optional[str] = None
    hmrc_eori_base_url: Optional[str] = None
    companies_house_api_key: Optional[str] = None
    vies_wsdl_url: Optional[str] = None
    azure_ad_client_id: Optional[str] = None
    academic_mock_enabled: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
