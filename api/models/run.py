"""
Pydantic models for run lifecycle API.

This module defines request and response models for the profiling run API.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
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
    column_profiles: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Column profile results")

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


class FileMetadata(BaseModel):
    """File metadata in profile response."""

    rows: int = Field(..., description="Total number of rows")
    columns: int = Field(..., description="Total number of columns")
    delimiter: str = Field(..., description="Delimiter used")
    crlf_detected: bool = Field(..., description="Whether CRLF line endings were detected")
    header: List[str] = Field(..., description="Column headers")


class ColumnProfileResponse(BaseModel):
    """Column profile in profile response."""

    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Inferred type")
    null_count: int = Field(..., description="Number of null values")
    distinct_count: int = Field(..., description="Number of distinct values")
    distinct_pct: float = Field(..., description="Percentage of distinct values")

    # Optional fields based on type
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    stddev: Optional[float] = None
    quantiles: Optional[Dict[str, float]] = None
    histogram: Optional[Dict[str, Any]] = None
    gaussian_pvalue: Optional[float] = None

    # String fields
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None
    has_non_ascii: Optional[bool] = None
    character_types: Optional[List[str]] = None

    # Date fields
    valid_count: Optional[int] = None
    invalid_count: Optional[int] = None
    detected_format: Optional[str] = None
    format_consistent: Optional[bool] = None
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    span_days: Optional[int] = None

    # Money fields
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    two_decimal_ok: Optional[bool] = None
    disallowed_symbols_found: Optional[bool] = None

    # Code fields
    cardinality_ratio: Optional[float] = None

    # Top values
    top_values: List[Dict[str, Any]] = Field(default_factory=list)


class CandidateKey(BaseModel):
    """Candidate key suggestion."""

    columns: List[str] = Field(..., description="Column names in key")
    distinct_ratio: float = Field(..., description="Ratio of distinct values")
    null_ratio_sum: float = Field(..., description="Sum of null ratios")
    score: float = Field(..., description="Key quality score")


class ProfileResponse(BaseModel):
    """Complete profile response."""

    run_id: UUID = Field(..., description="Run identifier")
    file: FileMetadata = Field(..., description="File metadata")
    errors: List[ErrorDetail] = Field(default_factory=list, description="Errors encountered")
    warnings: List[ErrorDetail] = Field(default_factory=list, description="Warnings encountered")
    columns: List[ColumnProfileResponse] = Field(default_factory=list, description="Column profiles")
    candidate_keys: List[CandidateKey] = Field(default_factory=list, description="Suggested candidate keys")
