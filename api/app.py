"""
VQ8 Data Profiler API.

FastAPI application for data profiling with run lifecycle management.
"""

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models.run import HealthResponse
from .routers import runs

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

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:8000",  # API server
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.

    Args:
        request: FastAPI request
        exc: Exception that was raised

    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_code": "E_INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat() + "Z"
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
        timestamp=datetime.utcnow(),
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
    work_dir = Path("/data/work")
    work_dir.mkdir(parents=True, exist_ok=True)

    # Ensure outputs directory exists
    outputs_dir = Path("/data/outputs")
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
