"""
Application configuration using Pydantic Settings.
Reads from environment variables and .env file.
"""
from functools import lru_cache
from typing import List

from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_NAME: str = "FastAPI Auth Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/auth_service_db"

    # -------------------------------------------------------------------------
    # JWT
    # -------------------------------------------------------------------------
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -------------------------------------------------------------------------
    # Google OAuth2
    # -------------------------------------------------------------------------
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # -------------------------------------------------------------------------
    # Twilio (SMS)
    # -------------------------------------------------------------------------
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_VERIFY_SERVICE_SID: str = ""  # Verify Service SID (starts with VA)

    # -------------------------------------------------------------------------
    # SendGrid (Email)
    # -------------------------------------------------------------------------
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@example.com"
    SENDGRID_FROM_NAME: str = "FastAPI Auth Service"

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated CORS origins."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    RATE_LIMIT_PER_MINUTE: int = 60

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — imported everywhere via dependency injection."""
    return Settings()


settings = get_settings()
