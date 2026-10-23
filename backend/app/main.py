import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any, Mapping, Optional
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.database import engine
from app.core.limiter import limiter
from app.models.token import RevokedToken, PasswordResetToken
from sqlalchemy import text

from app.core.config import settings
import app.models  # ensure models are registered

from app.routers import (
    auth_router,
    users_router,
    customers_router,
    leads_router,
    projects_router,
    site_surveys_router,
    blogs_router,
    faqs_router,
    calculators_router,
    settings_router,
    dashboard_router,
    notifications_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("solara_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Checking SOLARA API database connection...")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection established.")
    except Exception as e:
        logger.critical(f"Database connection failure during startup: {e}")
        raise RuntimeError(f"Database connection failed: {e}") from e

    # Apply database schema migrations
    try:
        import os
        from alembic.config import Config
        from alembic import command
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
        if os.path.exists(alembic_ini_path) and "sqlite" not in settings.DATABASE_URL:
            alembic_cfg = Config(alembic_ini_path)
            alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
            alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations successfully applied to head.")
        else:
            logger.info(
                "Automatic schema creation is disabled for SQLite; "
                "tests initialize their schema explicitly and standalone databases require Alembic."
            )
    except Exception as e:
        logger.critical(f"Database schema initialization failure: {e}")
        raise RuntimeError(f"Database schema initialization failed: {e}") from e

    # Cleanup of expired tokens at startup
    try:
        with Session(engine) as db:
            now = datetime.now(timezone.utc)
            db.query(RevokedToken).filter(RevokedToken.expires_at < now).delete()
            db.query(PasswordResetToken).filter(PasswordResetToken.expires_at < now).delete()
            db.commit()
            logger.info("Cleaned up expired rows in revoked_tokens and password_reset_tokens.")
    except Exception as e:
        logger.warning(f"Error cleaning up expired tokens at startup: {e}")

    yield
    # Shutdown
    logger.info("SOLARA API shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-Ready REST API for SOLARA Solar Energy Website & CRM Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Attach slowapi state
app.state.limiter = limiter

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith(("/docs", "/redoc")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
    return response

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return _error_response(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        message="Rate limit exceeded. Please try again later.",
        error_code="HTTP_429",
    )


# Centralized Exception Handlers
def _error_code_for_status(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    }.get(status_code, f"HTTP_{status_code}")


def _error_response(
    status_code: int,
    message: str,
    error_code: str,
    details: Any = None,
    headers: Optional[Mapping[str, str]] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "success": False,
            "message": message,
            "error_code": error_code,
            "details": details,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        message = "An unexpected server error occurred."
        error_code = "INTERNAL_SERVER_ERROR"
    elif isinstance(exc.detail, str):
        message = exc.detail
        error_code = _error_code_for_status(exc.status_code)
    else:
        message = "The request could not be processed."
        error_code = _error_code_for_status(exc.status_code)

    return _error_response(
        status_code=exc.status_code,
        message=message,
        error_code=error_code,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Pydantic error objects may include the submitted input, so expose only
    # field locations and error types in the public response.
    errors = [
        {
            "location": error.get("loc", []),
            "message": "Invalid value.",
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Input validation error.",
        error_code="VALIDATION_ERROR",
        details=jsonable_encoder(errors),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error(
        "Database integrity constraint failed for %s %s (%s)",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return _error_response(
        status_code=status.HTTP_409_CONFLICT,
        message="The requested change conflicts with existing data.",
        error_code="CONFLICT",
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error(
        "Database operation failed for %s %s (%s)",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An internal database error occurred. Please try again later.",
        error_code="DATABASE_ERROR",
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception for %s %s (%s)",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected server error occurred.",
        error_code="INTERNAL_SERVER_ERROR",
    )


# Root Health & Status Endpoints
@app.get("/", tags=["System"])
def root():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
def health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy", "version": settings.VERSION}


# Register Version 1 Routers
api_v1_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(users_router, prefix=api_v1_prefix)
app.include_router(customers_router, prefix=api_v1_prefix)
app.include_router(leads_router, prefix=api_v1_prefix)
app.include_router(projects_router, prefix=api_v1_prefix)
app.include_router(site_surveys_router, prefix=api_v1_prefix)
app.include_router(blogs_router, prefix=api_v1_prefix)
app.include_router(faqs_router, prefix=api_v1_prefix)
app.include_router(calculators_router, prefix=api_v1_prefix)
app.include_router(settings_router, prefix=api_v1_prefix)
app.include_router(dashboard_router, prefix=api_v1_prefix)
app.include_router(notifications_router, prefix=api_v1_prefix)