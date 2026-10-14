from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SOLARA Solar Energy CRM API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    # Production default is PostgreSQL as specified in instructions
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/solar_crm"
    
    # JWT Security & Session Lifetimes
    SECRET_KEY: str = "solara-crm-production-secret-key-change-in-env-at-least-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # Legacy default
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8  # Default session lifetime (remember_me=False)
    ACCESS_TOKEN_EXPIRE_REMEMBER_ME_DAYS: int = 30  # Extended session lifetime (remember_me=True)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    ACCOUNT_ACTIVATION_TOKEN_EXPIRE_HOURS: int = 24

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
    def parse_debug(cls, v):
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
