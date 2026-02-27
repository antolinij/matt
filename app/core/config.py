"""Application configuration"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List
from pydantic import model_validator


class Settings(BaseSettings):
    """Application settings"""
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields from .env
    )

    # API Settings
    APP_NAME: str = "Mattilda School Management API"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = False

    # Database - Individual components
    POSTGRES_USER: str = "mattilda"
    POSTGRES_PASSWORD: str = "mattilda123"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "mattilda_db"

    # Constructed DATABASE_URL (built from components above)
    DATABASE_URL: str = ""

    @model_validator(mode='after')
    def build_database_url(self):
        """Construct DATABASE_URL from individual components"""
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    # Database Pool Settings (for async)
    DB_POOL_SIZE: int = 20
    DB_POOL_OVERFLOW: int = 40
    DB_POOL_PRE_PING: bool = True
    DB_POOL_RECYCLE: int = 3600

    # Redis (for message queue)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Authentication & Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS - stored as strings, converted to lists
    CORS_ORIGINS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list"""
        return [item.strip() for item in self.CORS_ORIGINS.split(",")]

    def get_cors_methods(self) -> List[str]:
        """Get CORS methods as list"""
        return [item.strip() for item in self.CORS_ALLOW_METHODS.split(",")]

    def get_cors_headers(self) -> List[str]:
        """Get CORS headers as list"""
        return [item.strip() for item in self.CORS_ALLOW_HEADERS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
