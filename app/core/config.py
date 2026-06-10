"""Central application configuration, loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Enterprise AI Knowledge Copilot"
    API_V1_PREFIX: str = "/api/v1"

    # Database. Async drivers: postgresql+asyncpg (prod) or sqlite+aiosqlite (dev/test).
    DATABASE_URL: str = "sqlite+aiosqlite:///./copilot.db"

    # Auth / JWT. Override JWT_SECRET in every real environment.
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Workspace defaults
    DEFAULT_UPLOAD_LIMIT_MB: int = 50
    DEFAULT_STORAGE_QUOTA_MB: int = 5000

    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
