import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.user import User
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
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    logger.info("Database connection established.")

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            logger.info("No users found. Running default seed data for local development.")
            from seed import seed_data
            seed_data()
    finally:
        db.close()

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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Centralized Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "details": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        errors.append(f"{field}: {msg}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Input validation error: " + "; ".join(errors),
            "error_code": "VALIDATION_ERROR",
            "details": exc.errors(),
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error(f"Database Integrity Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": "A database constraint violation occurred (e.g., duplicate record or invalid reference).",
            "error_code": "INTEGRITY_ERROR",
            "details": None,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An internal database error occurred. Please try again later.",
            "error_code": "DATABASE_ERROR",
            "details": None,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected server error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": None,
        },
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
