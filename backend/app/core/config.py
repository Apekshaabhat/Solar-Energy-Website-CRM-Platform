from typing import List, Optional, Union

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_SECRET_KEY = "solara-crm-development-only-secret-key-change-before-production"
_DEFAULT_ADMIN_PASSWORDS = {"admin123", "password123", "changeme", "your-password"}


def validate_admin_seed_password(password: Optional[str]) -> str:
    normalized = (password or "").strip()
    lowered = normalized.lower()
    placeholder_text = lowered.replace("_", "-")
    if (
        len(normalized) < 12
        or lowered in _DEFAULT_ADMIN_PASSWORDS
        or any(
            marker in placeholder_text
            for marker in ("replace-with", "change-me", "placeholder", "your-")
        )
        or not any(character.isupper() for character in normalized)
        or not any(character.islower() for character in normalized)
        or not any(character.isdigit() for character in normalized)
    ):
        raise ValueError(
            "SEED_ADMIN_PASSWORD must be at least 12 characters and include "
            "uppercase, lowercase, and numeric characters."
        )
    return normalized


class Settings(BaseSettings):
    PROJECT_NAME: str = "SOLARA Solar Energy CRM API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    # Production default is PostgreSQL as specified in instructions
    DATABASE_URL: str = "postgresql+psycopg2://postgres:PostgreSQL@localhost:5432/solar_crm"
    
    # JWT Security & Session Lifetimes
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # Legacy default
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8  # Default session lifetime (remember_me=False)
    ACCESS_TOKEN_EXPIRE_REMEMBER_ME_DAYS: int = 30  # Extended session lifetime (remember_me=True)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    ACCOUNT_ACTIVATION_TOKEN_EXPIRE_HOURS: int = 24

    SEED_ADMIN_PASSWORD: Optional[str] = None

    # Rate Limiting
    AUTH_RATE_LIMIT: str = "5/minute"

    # Email & Notification Settings
    EMAIL_BACKEND: str = "console"  # "console" for dev or "smtp" for production
    SMTP_HOST: Union[str, None] = None
    SMTP_PORT: int = 587
    SMTP_USER: Union[str, None] = None
    SMTP_PASSWORD: Union[str, None] = None
    SMTP_TLS: bool = True
    EMAILS_FROM_EMAIL: str = "noreply@solara.com"
    FRONTEND_URL: str = "http://localhost:5173"
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return value
        return value

    @model_validator(mode="after")
    def validate_production_security(self):
        environment = self.ENVIRONMENT.strip().lower()
        is_production = environment in {"production", "prod", "release"}
        if not is_production:
            return self

        if self.DEBUG:
            raise ValueError("DEBUG must be false in production.")

        secret = self.SECRET_KEY.strip()
        placeholder_text = secret.lower().replace("_", "-")
        if (
            len(secret) < 32
            or secret == _DEFAULT_SECRET_KEY
            or secret.lower() in {"secret", "changeme", "your-secret-key"}
            or any(
                marker in placeholder_text
                for marker in ("replace-with", "change-me", "placeholder", "your-")
            )
        ):
            raise ValueError(
                "Production SECRET_KEY must be a unique secret of at least 32 characters."
            )

        validate_admin_seed_password(self.SEED_ADMIN_PASSWORD)
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
