"""
Pydantic models for run lifecycle API.

This module defines request and response models for the profiling run API.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RunState(str, Enum):
    """Run processing states."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RunCreate(BaseModel):
    """Request model for creating a profiling run."""

    delimiter: str = Field(
        ...,
        pattern="^[|,]$",
        description="Delimiter character: | or ,"
    )
    quoted: bool = Field(
        default=True,
        description="Whether fields use double-quote escaping"
    )
    expect_crlf: bool = Field(
        default=True,
        description="Whether to expect CRLF line endings"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "delimiter": "|",
                "quoted": True,
                "expect_crlf": True
            }
        }


class RunResponse(BaseModel):
    """Response model for creating a profiling run."""

    run_id: UUID = Field(..., description="Unique run identifier")
    state: RunState = Field(..., description="Current run state")
    created_at: datetime = Field(..., description="Run creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "state": "queued",
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class ErrorDetail(BaseModel):
    """Error or warning detail."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    count: int = Field(..., description="Number of occurrences")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "E_NUMERIC_FORMAT",
                "message": "Invalid numeric format (contains symbols)",
                "count": 42
            }
        }


class RunStatus(BaseModel):
    """Response model for run status."""

    run_id: UUID = Field(..., description="Run identifier")
    state: RunState = Field(..., description="Current state")
    progress_pct: float = Field(0.0, ge=0.0, le=100.0, description="Processing progress percentage")
    created_at: datetime = Field(..., description="Run creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    warnings: List[ErrorDetail] = Field(default_factory=list, description="Non-critical warnings")
    errors: List[ErrorDetail] = Field(default_factory=list, description="Errors encountered")

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "state": "processing",
                "progress_pct": 45.2,
                "created_at": "2025-01-15T10:30:00Z",
                "started_at": "2025-01-15T10:30:15Z",
                "completed_at": None,
                "warnings": [
                    {
                        "code": "W_DATE_RANGE",
                        "message": "Date outside expected range (1900-2026)",
                        "count": 7
                    }
                ],
                "errors": [
                    {
                        "code": "E_NUMERIC_FORMAT",
                        "message": "Invalid numeric format (contains symbols)",
                        "count": 42
                    }
                ]
            }
        }


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    run_id: UUID = Field(..., description="Run identifier")
    state: RunState = Field(..., description="Current state")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "state": "processing",
                "message": "File uploaded and processing started"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field("ok", description="Health status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field("1.0.0", description="API version")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "timestamp": "2025-01-15T10:30:00Z",
                "version": "1.0.0"
            }
        }
