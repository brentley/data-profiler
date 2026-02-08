"""
VQ8 Data Profiler API.

FastAPI application for data profiling with run lifecycle management.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from .models.run import HealthResponse
from .routers import runs

# Load environment variables from .env file
load_dotenv()

# API version
API_VERSION = "1.0.0"

# Create FastAPI app
app = FastAPI(
    title="VQ8 Data Profiler API",
    description="Data profiling service for CSV/TXT files with exact metrics and type inference",
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS - read from environment or use defaults
cors_origins_str = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:4173,http://localhost:5173,http://localhost:8000"
)
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Middleware to limit request body size to prevent memory exhaustion."""
    # Skip check for file upload endpoints (they have their own limits)
    if request.url.path.endswith("/upload") or "/upload/chunk" in request.url.path:
        return await call_next(request)

    content_length = request.headers.get("content-length")
    if content_length:
        max_size = 10 * 1024 * 1024  # 10MB for JSON
        if int(content_length) > max_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "detail": f"Request body too large. Maximum size: {max_size} bytes",
                    "error_code": "E_REQUEST_TOO_LARGE"
                }
            )

    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if os.getenv("HTTPS", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# TODO(security): Add rate limiting to prevent API abuse
# Options:
# 1. Infrastructure level (Nginx): limit_req_zone
# 2. Application level (slowapi): pip install slowapi
# Recommended limits:
# - POST /runs: 10/minute (run creation)
# - POST /runs/{id}/upload: 5/minute (file uploads)
# - GET endpoints: 100/minute (status checks)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.

    Security: Prevents information leakage in error messages.

    Args:
        request: FastAPI request
        exc: Exception that was raised

    Returns:
        JSONResponse with error details
    """
    # Log full error internally (with stack trace)
    logger.error("Unhandled exception on %s", request.url.path, exc_info=True)

    # Return generic error to user (don't leak internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_code": "E_INTERNAL_ERROR",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# Health check endpoint
@app.get("/healthz", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns API status and version information.

    Returns:
        HealthResponse with status, timestamp, and version
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        version=API_VERSION
    )


# Include routers
app.include_router(runs.router)


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup tasks.

    Ensures required directories exist.
    """
    # Ensure work directory exists
    work_dir = Path(os.getenv("WORK_DIR", "/data/work"))
    work_dir.mkdir(parents=True, exist_ok=True)

    # Ensure outputs directory exists
    outputs_dir = Path(os.getenv("OUTPUT_DIR", "/data/outputs"))
    outputs_dir.mkdir(parents=True, exist_ok=True)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown tasks.

    Cleanup and resource release.
    """
    pass


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with API information.

    Returns:
        API information and links
    """
    return {
        "service": "VQ8 Data Profiler API",
        "version": API_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "health": "/healthz"
    }
