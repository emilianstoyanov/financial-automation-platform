"""Application settings loaded from environment variables."""

from typing import Literal
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Financial Automation Platform", alias="APP_NAME")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="ENVIRONMENT",
    )
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Database
    database_url: str = Field(
        default="sqlite:///./data/financial_data.db",
        alias="DATABASE_URL",
    )

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: str = Field(default="logs", alias="LOG_DIR")
    log_file: str = Field(default="app.log", alias="LOG_FILE")

    # OpenAPI
    openapi_enabled: bool = Field(default=True, alias="OPENAPI_ENABLED")

    # Exchange rates (Task 2)
    exchange_rate_api_url: str = Field(
        default="https://api.exchangerate-api.com/v4/latest/BGN",
        alias="EXCHANGE_RATE_API_URL",
    )

    # Document scraping (Task 3)
    scraping_use_curl_impersonate: bool = Field(
        default=False,
        alias="SCRAPING_USE_CURL_IMPERSONATE",
    )
    scraping_browser_fallback: bool = Field(
        default=False,
        alias="SCRAPING_BROWSER_FALLBACK",
    )
    scraping_playwright_headed: bool = Field(
        default=False,
        alias="SCRAPING_PLAYWRIGHT_HEADED",
    )

    # LLM extraction (Task 4)
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Convert Heroku-style postgres URLs for SQLAlchemy 2.x."""
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return URL suitable for SQLAlchemy engine creation."""
        url = self.database_url
        if url.startswith("sqlite") and ":///" in url and not url.startswith("sqlite:////"):
            # Ensure relative SQLite paths work from project root
            return url
        return url


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance for dependency injection."""
    return Settings()
