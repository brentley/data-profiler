"""
Run lifecycle endpoints.

This module implements the FastAPI routes for profiling run management.
"""

import csv
import json
import gzip
import tempfile
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from ..models.run import (
    CandidateKey,
    CandidateKeysResponse,
    ColumnProfileResponse,
    ConfirmKeysRequest,
    DuplicateDetectionResponse,
    DuplicateGroup,
    ErrorDetail,
    FileMetadata,
    FileUploadResponse,
    ProfileResponse,
    RunCreate,
    RunResponse,
    RunState,
    RunStatus,
)
from ..services.ingest import (
    CRLFDetector,
    CSVParser,
    ParserConfig,
    ParserError,
    UTF8Validator,
    ValidationResult,
)
from ..services.types import TypeInferrer
from ..services.profile import (
    NumericProfiler,
    StringProfiler,
    DateProfiler,
    MoneyProfiler,
    CodeProfiler,
)
from ..services.distincts import DistinctCounter
from ..services.audit import AuditLogger
from ..storage.workspace import WorkspaceManager

# Workspace manager (initialized lazily)
_workspace: Optional[WorkspaceManager] = None
_audit_logger: Optional[AuditLogger] = None


def get_workspace() -> WorkspaceManager:
    """Get or create workspace manager."""
    global _workspace
    if _workspace is None:
        work_dir = Path("/data/work")
        _workspace = WorkspaceManager(work_dir)
    return _workspace


def get_audit_logger() -> AuditLogger:
    """Get or create audit logger."""
    global _audit_logger
    if _audit_logger is None:
        output_dir = Path("/data/outputs")
        _audit_logger = AuditLogger(output_dir)
    return _audit_logger


def set_workspace(workspace_manager: WorkspaceManager):
    """Set workspace manager (for testing)."""
    global _workspace
    _workspace = workspace_manager

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(run_config: RunCreate) -> RunResponse:
    """
    Create a new profiling run.

    This initializes a run with configuration but does not process any data yet.
    Use the upload endpoint to provide the file to profile.

    Args:
        run_config: Run configuration (delimiter, quoting, line endings)

    Returns:
        RunResponse with run_id and initial state

    Raises:
        HTTPException: If run creation fails
    """
    try:
        workspace = get_workspace()
        audit_logger = get_audit_logger()

        metadata = workspace.create_run(
            delimiter=run_config.delimiter,
            quoted=run_config.quoted,
            expect_crlf=run_config.expect_crlf
        )

        # Log run creation
        audit_logger.log_run_created(
            run_id=metadata.run_id,
            delimiter=run_config.delimiter,
            quoted=run_config.quoted,
            expect_crlf=run_config.expect_crlf
        )

        return RunResponse(
            run_id=metadata.run_id,
            state=metadata.state,
            created_at=metadata.created_at
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create run: {str(e)}"
        )


@router.post(
    "/{run_id}/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def upload_file(run_id: UUID, file: UploadFile = File(...)) -> FileUploadResponse:
    """
    Upload a file for profiling.

    Accepts CSV/TXT files or gzipped versions. The file will be validated
    for UTF-8 encoding and CRLF detection before processing begins.

    Args:
        run_id: Run UUID from create_run endpoint
        file: File to upload (.txt, .csv, .txt.gz, .csv.gz)

    Returns:
        FileUploadResponse with processing status

    Raises:
        HTTPException: If run not found, file invalid, or already uploaded
    """
    workspace = get_workspace()

    # Check if run exists
    if not workspace.run_exists(run_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    # Load metadata
    metadata = workspace.load_metadata(run_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    # Check if already uploaded
    if metadata.state != RunState.QUEUED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run {run_id} already has a file uploaded (state: {metadata.state})"
        )

    # Validate file extension
    filename = file.filename or "uploaded_file"
    valid_extensions = ['.txt', '.csv', '.txt.gz', '.csv.gz']
    if not any(filename.endswith(ext) for ext in valid_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Accepted: {', '.join(valid_extensions)}"
        )

    try:
        # Read file content (streaming would be better for very large files)
        file_content = await file.read()

        # Detect if gzipped and decompress if needed
        is_gzipped = filename.endswith('.gz')
        if is_gzipped:
            try:
                file_content = gzip.decompress(file_content)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to decompress gzip file: {str(e)}"
                )

        # Save uploaded file
        workspace.save_uploaded_file(run_id, file_content, filename)

        # Log file upload with hash and byte count
        audit_logger = get_audit_logger()
        audit_logger.log_file_uploaded(
            run_id=run_id,
            filename=filename,
            file_data=file_content,
            is_gzipped=is_gzipped
        )

        # Update state to processing
        workspace.update_state(run_id, RunState.PROCESSING, progress_pct=0.0)

        # Start validation and processing
        await process_file(run_id, file_content, metadata.delimiter, metadata.quoted, workspace)

        return FileUploadResponse(
            run_id=run_id,
            state=RunState.PROCESSING,
            message="File uploaded and processing started"
        )

    except HTTPException:
        raise
    except Exception as e:
        # Mark as failed
        workspace.update_state(run_id, RunState.FAILED)
        workspace.add_error(
            run_id,
            ErrorDetail(code="E_UPLOAD_FAILED", message=str(e), count=1)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}"
        )


async def profile_columns(
    run_id: UUID,
    temp_csv: Path,
    type_result,
    delimiter: str,
    workspace: WorkspaceManager
) -> Dict[str, Dict]:
    """
    Profile all columns in the CSV file using appropriate profilers.

    This performs streaming profiling with:
    1. Type-specific profilers (Numeric, String, Date, Money, Code)
    2. DistinctCounter for all columns
    3. Progress tracking (60-100%)

    Args:
        run_id: Run UUID
        temp_csv: Path to normalized CSV file
        type_result: TypeInferenceResult with detected types
        delimiter: CSV delimiter
        workspace: WorkspaceManager instance

    Returns:
        Dictionary mapping column names to profile results
    """
    column_profiles = {}
    columns = list(type_result.columns.keys())
    total_columns = len(columns)

    # Create profilers for each column based on type
    profilers = {}
    distinct_counters = {}

    for col_name, col_info in type_result.columns.items():
        inferred_type = col_info.inferred_type

        # Create type-specific profiler
        if inferred_type == "numeric":
            profilers[col_name] = NumericProfiler(num_bins=10)
        elif inferred_type == "money":
            profilers[col_name] = MoneyProfiler()
        elif inferred_type == "date":
            profilers[col_name] = DateProfiler()
        elif inferred_type == "code":
            profilers[col_name] = CodeProfiler(top_n=10)
        elif inferred_type in ["alpha", "varchar", "mixed", "unknown"]:
            profilers[col_name] = StringProfiler(top_n=10)
        else:
            profilers[col_name] = StringProfiler(top_n=10)

        # Create distinct counter for all columns
        distinct_counters[col_name] = DistinctCounter()

    # Stream through CSV and update profilers
    with open(temp_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=delimiter)

        for row in reader:
            for col_name in columns:
                value = row.get(col_name, '')
                profilers[col_name].update(value)

    # Finalize profilers and collect results
    for idx, col_name in enumerate(columns):
        # Update progress (60% to 100%)
        progress = 60.0 + ((idx + 1) / total_columns) * 40.0
        workspace.update_state(run_id, RunState.PROCESSING, progress_pct=progress)

        # Finalize profiler
        profiler = profilers[col_name]
        stats = profiler.finalize()

        # Get distinct count from DistinctCounter
        distinct_result = distinct_counters[col_name].count_distincts(
            temp_csv,
            col_name,
            delimiter=delimiter
        )

        # Get column type info
        col_info = type_result.columns[col_name]

        # Build profile result based on type
        profile = {
            "name": col_name,
            "type": col_info.inferred_type,
            "null_count": stats.null_count if hasattr(stats, 'null_count') else 0,
            "distinct_count": distinct_result.distinct_count,
            "distinct_pct": distinct_result.cardinality_ratio * 100.0,
        }

        # Add type-specific stats
        if col_info.inferred_type == "numeric":
            profile.update({
                "min": stats.min_value,
                "max": stats.max_value,
                "mean": stats.mean,
                "median": stats.median,
                "stddev": stats.stddev,
                "quantiles": stats.quantiles,
                "histogram": stats.histogram,
                "gaussian_pvalue": stats.gaussian_pvalue,
            })
        elif col_info.inferred_type == "money":
            profile.update({
                "valid_count": stats.valid_count,
                "invalid_count": stats.invalid_count,
                "min_value": stats.min_value,
                "max_value": stats.max_value,
                "two_decimal_ok": stats.two_decimal_ok,
                "disallowed_symbols_found": stats.disallowed_symbols_found,
            })
        elif col_info.inferred_type == "date":
            profile.update({
                "valid_count": stats.valid_count,
                "invalid_count": stats.invalid_count,
                "detected_format": stats.detected_format,
                "format_consistent": stats.format_consistent,
                "min_date": stats.min_date,
                "max_date": stats.max_date,
                "span_days": stats.span_days,
            })
        elif col_info.inferred_type == "code":
            profile.update({
                "cardinality_ratio": stats.cardinality_ratio,
                "min_length": stats.min_length,
                "max_length": stats.max_length,
                "avg_length": stats.avg_length,
                "top_values": stats.top_values[:10],
            })
        elif col_info.inferred_type in ["alpha", "varchar", "mixed", "unknown"]:
            profile.update({
                "min_length": stats.min_length,
                "max_length": stats.max_length,
                "avg_length": stats.avg_length,
                "top_values": stats.top_values[:10],
                "has_non_ascii": stats.has_non_ascii,
                "character_types": list(stats.character_types),
            })

        # Add top values from distinct counter
        profile["top_values"] = distinct_result.get_top_n(10)

        column_profiles[col_name] = profile

        # Cleanup distinct counter temp files
        distinct_counters[col_name].cleanup()

    return column_profiles


async def process_file(
    run_id: UUID,
    file_content: bytes,
    delimiter: str,
    quoted: bool,
    workspace: WorkspaceManager
) -> None:
    """
    Process uploaded file with validation and parsing.

    This performs:
    1. UTF-8 validation
    2. CRLF detection
    3. CSV parsing with header validation
    4. Type inference
    5. Column profiling

    Args:
        run_id: Run UUID
        file_content: File content as bytes
        delimiter: CSV delimiter
        quoted: Whether fields use quoting
        workspace: WorkspaceManager instance

    Raises:
        HTTPException: If catastrophic errors occur
    """
    audit_logger = get_audit_logger()

    try:
        # Step 1: UTF-8 Validation (10% progress)
        audit_logger.log_validation_started(run_id)
        workspace.update_state(run_id, RunState.PROCESSING, progress_pct=10.0)

        stream = BytesIO(file_content)
        validator = UTF8Validator(stream)
        validation_result = validator.validate()

        if not validation_result.is_valid:
            # Catastrophic error - invalid UTF-8
            workspace.update_state(run_id, RunState.FAILED)
            workspace.add_error(
                run_id,
                ErrorDetail(
                    code="E_UTF8_INVALID",
                    message=validation_result.error or "Invalid UTF-8 encoding",
                    count=1
                )
            )
            audit_logger.log_run_failed(
                run_id=run_id,
                error_code="E_UTF8_INVALID",
                error_message=validation_result.error or "Invalid UTF-8 encoding"
            )
            return

        # Step 2: CRLF Detection (20% progress)
        workspace.update_state(run_id, RunState.PROCESSING, progress_pct=20.0)

        stream.seek(0)
        detector = CRLFDetector(stream)
        line_ending_result = detector.detect()

        # Normalize line endings
        normalized_content = detector.normalize()

        # Log validation completion with line ending counts
        audit_logger.log_validation_completed(
            run_id=run_id,
            utf8_valid=True,
            crlf_count=line_ending_result.crlf_count,
            lf_count=line_ending_result.lf_count,
            cr_count=line_ending_result.cr_count,
            mixed_endings=line_ending_result.mixed
        )

        # Record line ending info as warning if mixed
        if line_ending_result.mixed:
            workspace.add_warning(
                run_id,
                ErrorDetail(
                    code="W_LINE_ENDING",
                    message=f"Mixed line endings detected: {line_ending_result.crlf_count} CRLF, {line_ending_result.lf_count} LF, {line_ending_result.cr_count} CR",
                    count=1
                )
            )
            audit_logger.log_warning(
                run_id=run_id,
                warning_code="W_LINE_ENDING",
                count=1
            )

        # Step 3: CSV Parsing (50% progress)
        audit_logger.log_parsing_started(run_id)
        workspace.update_state(run_id, RunState.PROCESSING, progress_pct=30.0)

        # Create text stream from normalized content
        from io import StringIO
        text_stream = StringIO(normalized_content.decode('utf-8'))

        parser_config = ParserConfig(
            delimiter=delimiter,
            quoting=quoted,
            has_header=True,
            continue_on_error=True  # Continue processing on non-catastrophic errors
        )

        parser = CSVParser(text_stream, parser_config)

        # Parse header
        try:
            header_result = parser.parse_header()
        except ParserError as e:
            # Catastrophic error in header
            workspace.update_state(run_id, RunState.FAILED)
            workspace.add_error(
                run_id,
                ErrorDetail(code=e.code, message=e.message, count=1)
            )
            audit_logger.log_run_failed(
                run_id=run_id,
                error_code=e.code,
                error_message=e.message
            )
            return

        # Count rows for progress tracking
        row_count = 0
        for row in parser.parse_rows():
            row_count += 1
            # Update progress every 1000 rows
            if row_count % 1000 == 0:
                progress = 30.0 + (row_count / 10000) * 20.0  # 30-50% range
                workspace.update_state(run_id, RunState.PROCESSING, progress_pct=min(progress, 50.0))

        # Aggregate parser errors
        error_rollup = parser.get_error_rollup()
        for error_code, count in error_rollup.items():
            # Determine if it's a warning or error based on code
            if error_code.startswith('W_'):
                workspace.add_warning(
                    run_id,
                    ErrorDetail(code=error_code, message=f"Parser warning: {error_code}", count=count)
                )
                audit_logger.log_warning(run_id=run_id, warning_code=error_code, count=count)
            else:
                workspace.add_error(
                    run_id,
                    ErrorDetail(code=error_code, message=f"Parser error: {error_code}", count=count)
                )
                audit_logger.log_error(run_id=run_id, error_code=error_code, count=count)

        # Log parsing completion with counts (NO VALUES)
        column_count = len(header_result.header) if header_result else 0
        audit_logger.log_parsing_completed(
            run_id=run_id,
            row_count=row_count,
            column_count=column_count,
            header_names=header_result.header if header_result else [],
            error_rollup=error_rollup
        )

        # Step 4: Type Inference (60% progress)
        audit_logger.log_type_inference_started(run_id)
        workspace.update_state(run_id, RunState.PROCESSING, progress_pct=50.0)

        # Save normalized content to temp file for type inference
        run_dir = workspace.get_run_dir(run_id)
        temp_csv = run_dir / "normalized.csv"
        with open(temp_csv, 'wb') as f:
            f.write(normalized_content)

        # Run type inference
        inferrer = TypeInferrer(sample_size=None)  # Full inference
        type_result = inferrer.infer_column_types(temp_csv, delimiter=delimiter)

        # Collect type inference results for audit log
        column_types = {}
        error_counts = {}
        warning_counts = {}

        # Process type inference results
        for col_name, col_info in type_result.columns.items():
            column_types[col_name] = col_info.inferred_type
            error_counts[col_name] = col_info.error_count
            warning_counts[col_name] = col_info.warning_count

            if col_info.error_count > 0:
                workspace.add_error(
                    run_id,
                    ErrorDetail(
                        code=f"E_{col_info.inferred_type.upper()}_FORMAT",
                        message=f"Format violations in column '{col_name}'",
                        count=col_info.error_count
                    )
                )
                audit_logger.log_error(
                    run_id=run_id,
                    error_code=f"E_{col_info.inferred_type.upper()}_FORMAT",
                    count=col_info.error_count
                )

            if col_info.warning_count > 0:
                workspace.add_warning(
                    run_id,
                    ErrorDetail(
                        code=f"W_{col_info.inferred_type.upper()}_FORMAT",
                        message=f"Format warnings in column '{col_name}'",
                        count=col_info.warning_count
                    )
                )
                audit_logger.log_warning(
                    run_id=run_id,
                    warning_code=f"W_{col_info.inferred_type.upper()}_FORMAT",
                    count=col_info.warning_count
                )

        # Log type inference completion (counts and types only, NO VALUES)
        audit_logger.log_type_inference_completed(
            run_id=run_id,
            column_types=column_types,
            error_counts=error_counts,
            warning_counts=warning_counts
        )

        # Step 5: Profile Each Column (50-100% progress)
        audit_logger.log_profiling_started(run_id)
        workspace.update_state(run_id, RunState.PROCESSING, progress_pct=60.0)

        column_profiles = await profile_columns(
            run_id=run_id,
            temp_csv=temp_csv,
            type_result=type_result,
            delimiter=delimiter,
            workspace=workspace
        )

        # Store profile results in workspace metadata
        workspace.save_column_profiles(run_id, column_profiles)

        # Calculate aggregate statistics for audit log
        total_null_count = sum(
            profile.get('null_count', 0)
            for profile in column_profiles.values()
        )
        total_distinct_count = sum(
            profile.get('distinct_count', 0)
            for profile in column_profiles.values()
        )

        # Log profiling completion with aggregate counts (NO VALUES)
        audit_logger.log_profiling_completed(
            run_id=run_id,
            columns_profiled=len(column_profiles),
            total_null_count=total_null_count,
            total_distinct_count=total_distinct_count
        )

        # Step 6: Complete (100% progress)
        workspace.update_state(run_id, RunState.COMPLETED, progress_pct=100.0)

        # Load final metadata for audit log
        metadata = workspace.load_metadata(run_id)
        total_errors = sum(e.get('count', 0) for e in metadata.errors) if metadata else 0
        total_warnings = sum(w.get('count', 0) for w in metadata.warnings) if metadata else 0

        # Log run completion
        audit_logger.log_run_completed(
            run_id=run_id,
            total_errors=total_errors,
            total_warnings=total_warnings
        )

    except ParserError as e:
        # Catastrophic parser error
        workspace.update_state(run_id, RunState.FAILED)
        workspace.add_error(
            run_id,
            ErrorDetail(code=e.code, message=e.message, count=1)
        )
        audit_logger.log_run_failed(
            run_id=run_id,
            error_code=e.code,
            error_message=e.message
        )
    except Exception as e:
        # Unexpected error
        workspace.update_state(run_id, RunState.FAILED)
        workspace.add_error(
            run_id,
            ErrorDetail(code="E_PROCESSING_FAILED", message=str(e), count=1)
        )
        audit_logger.log_run_failed(
            run_id=run_id,
            error_code="E_PROCESSING_FAILED",
            error_message=str(e)
        )



@router.get("/{run_id}/status", response_model=RunStatus)
async def get_run_status(run_id: UUID) -> RunStatus:
    """
    Get the current status of a profiling run.

    Poll this endpoint to track processing progress and detect completion or failure.

    Args:
        run_id: Run UUID

    Returns:
        RunStatus with current state, progress, and any errors/warnings

    Raises:
        HTTPException: If run not found
    """
    workspace = get_workspace()

    if not workspace.run_exists(run_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    metadata = workspace.load_metadata(run_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    # Convert error/warning dicts to ErrorDetail models
    warnings = [ErrorDetail(**w) for w in metadata.warnings]
    errors = [ErrorDetail(**e) for e in metadata.errors]

    return RunStatus(
        run_id=metadata.run_id,
        state=metadata.state,
        progress_pct=metadata.progress_pct,
        created_at=metadata.created_at,
        started_at=metadata.started_at,
        completed_at=metadata.completed_at,
        warnings=warnings,
        errors=errors,
        column_profiles=metadata.column_profiles
    )


def sanitize_csv_value(value) -> str:
    """
    Sanitize a value to prevent CSV injection attacks.

    CSV injection occurs when cells starting with =, +, -, or @ are
    interpreted as formulas by spreadsheet applications.

    Args:
        value: Value to sanitize (any type)

    Returns:
        Sanitized string value safe for CSV export
    """
    if value is None:
        return ""

    # Convert to string
    str_value = str(value)

    # Check if starts with dangerous characters
    if str_value and str_value[0] in ('=', '+', '-', '@'):
        # Prepend with single quote to prevent formula interpretation
        return "'" + str_value

    return str_value


@router.get("/{run_id}/metrics.csv")
async def get_metrics_csv(run_id: UUID) -> StreamingResponse:
    """
    Export column metrics as CSV.

    Generates a CSV file with one row per column containing all profiling metrics:
    - Column name and type
    - Null percentage and distinct count
    - Type-specific metrics (min/max, quantiles, etc.)

    The CSV is stored in the run directory as metrics.csv and returned with
    proper Content-Type headers for download. All values are sanitized to
    prevent CSV injection attacks (values starting with =, +, -, @ are escaped).

    Args:
        run_id: Run UUID

    Returns:
        StreamingResponse with CSV content

    Raises:
        HTTPException: If run not found or not completed
    """
    workspace = get_workspace()

    if not workspace.run_exists(run_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    metadata = workspace.load_metadata(run_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    # Check if run is completed
    if metadata.state != RunState.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run {run_id} is not completed (state: {metadata.state})"
        )

    # Check if column profiles exist
    if not metadata.column_profiles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No column profiles found for run {run_id}"
        )

    # Create outputs directory within the run directory
    run_dir = workspace.get_run_dir(run_id)
    csv_path = run_dir / "metrics.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        headers = [
            "column_name",
            "type",
            "null_count",
            "distinct_count",
            "distinct_pct",
            "min_value",
            "max_value",
            "mean",
            "median",
            "stddev",
            "min_length",
            "max_length",
            "avg_length",
            "top_value_1",
            "top_value_1_count",
            "top_value_2",
            "top_value_2_count",
            "top_value_3",
            "top_value_3_count",
        ]
        writer.writerow(headers)

        # Write one row per column
        for col_name, profile in metadata.column_profiles.items():
            # Extract metrics with defaults
            col_type = profile.get("type", "unknown")
            null_count = profile.get("null_count", 0)
            distinct_count = profile.get("distinct_count", 0)
            distinct_pct = profile.get("distinct_pct", 0.0)

            # Numeric metrics (for numeric/money types)
            min_value = profile.get("min", profile.get("min_value", ""))
            max_value = profile.get("max", profile.get("max_value", ""))
            mean = profile.get("mean", "")
            median = profile.get("median", "")
            stddev = profile.get("stddev", "")

            # String metrics (for string/code types)
            min_length = profile.get("min_length", "")
            max_length = profile.get("max_length", "")
            avg_length = profile.get("avg_length", "")

            # Top values (available for all types)
            top_values = profile.get("top_values", [])
            top_1_value = ""
            top_1_count = ""
            top_2_value = ""
            top_2_count = ""
            top_3_value = ""
            top_3_count = ""

            if len(top_values) > 0:
                top_1_value = top_values[0].get("value", "")
                top_1_count = top_values[0].get("count", "")
            if len(top_values) > 1:
                top_2_value = top_values[1].get("value", "")
                top_2_count = top_values[1].get("count", "")
            if len(top_values) > 2:
                top_3_value = top_values[2].get("value", "")
                top_3_count = top_values[2].get("count", "")

            # Build row with CSV injection prevention
            row = [
                sanitize_csv_value(col_name),
                sanitize_csv_value(col_type),
                sanitize_csv_value(null_count),
                sanitize_csv_value(distinct_count),
                sanitize_csv_value(distinct_pct),
                sanitize_csv_value(min_value),
                sanitize_csv_value(max_value),
                sanitize_csv_value(mean),
                sanitize_csv_value(median),
                sanitize_csv_value(stddev),
                sanitize_csv_value(min_length),
                sanitize_csv_value(max_length),
                sanitize_csv_value(avg_length),
                sanitize_csv_value(top_1_value),
                sanitize_csv_value(top_1_count),
                sanitize_csv_value(top_2_value),
                sanitize_csv_value(top_2_count),
                sanitize_csv_value(top_3_value),
                sanitize_csv_value(top_3_count),
            ]

            writer.writerow(row)

    # Read CSV content and return as streaming response
    def iterfile():
        with open(csv_path, 'rb') as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=metrics_{run_id}.csv"
        }
    )


@router.get("/{run_id}/profile", response_model=ProfileResponse)
async def get_profile(run_id: UUID) -> ProfileResponse:
    """
    Get the complete profiling results as JSON.

    This endpoint returns the full profile with file metadata, column statistics,
    errors, warnings, and candidate key suggestions. The profile is also saved
    to /data/outputs/{run_id}/profile.json for download.

    Args:
        run_id: Run UUID

    Returns:
        ProfileResponse with complete profiling results

    Raises:
        HTTPException: If run not found or processing not complete
    """
    workspace = get_workspace()

    if not workspace.run_exists(run_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    metadata = workspace.load_metadata(run_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    # Check if processing is complete
    if metadata.state not in [RunState.COMPLETED, RunState.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Processing not complete yet (state: {metadata.state})"
        )

    # Check if we have column profiles
    if not metadata.column_profiles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile data available"
        )

    # Read the normalized CSV to get row count and headers
    run_dir = workspace.get_run_dir(run_id)
    normalized_csv = run_dir / "normalized.csv"

    if not normalized_csv.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile data not found"
        )

    # Read CSV to get row count and headers
    row_count = 0
    headers = []
    with open(normalized_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=metadata.delimiter)
        headers = reader.fieldnames or []
        for _ in reader:
            row_count += 1

    # Build file metadata
    file_metadata = FileMetadata(
        rows=row_count,
        columns=len(headers),
        delimiter=metadata.delimiter,
        crlf_detected=metadata.expect_crlf,
        header=headers
    )

    # Convert error/warning dicts to ErrorDetail models
    warnings = [ErrorDetail(**w) for w in metadata.warnings]
    errors = [ErrorDetail(**e) for e in metadata.errors]

    # Convert column profiles to ColumnProfileResponse models
    column_profiles = []
    for col_name, profile_data in metadata.column_profiles.items():
        # Create base column profile
        col_profile = ColumnProfileResponse(
            name=profile_data.get("name", col_name),
            type=profile_data.get("type", "unknown"),
            null_count=profile_data.get("null_count", 0),
            distinct_count=profile_data.get("distinct_count", 0),
            distinct_pct=profile_data.get("distinct_pct", 0.0),
            top_values=profile_data.get("top_values", [])
        )

        # Add type-specific fields
        col_type = profile_data.get("type", "")

        if col_type == "numeric":
            col_profile.min = profile_data.get("min")
            col_profile.max = profile_data.get("max")
            col_profile.mean = profile_data.get("mean")
            col_profile.median = profile_data.get("median")
            col_profile.stddev = profile_data.get("stddev")
            col_profile.quantiles = profile_data.get("quantiles")
            col_profile.histogram = profile_data.get("histogram")
            col_profile.gaussian_pvalue = profile_data.get("gaussian_pvalue")

        elif col_type in ["alpha", "varchar", "code", "mixed", "unknown"]:
            col_profile.min_length = profile_data.get("min_length")
            col_profile.max_length = profile_data.get("max_length")
            col_profile.avg_length = profile_data.get("avg_length")
            col_profile.has_non_ascii = profile_data.get("has_non_ascii")
            col_profile.character_types = profile_data.get("character_types")
            if col_type == "code":
                col_profile.cardinality_ratio = profile_data.get("cardinality_ratio")

        elif col_type == "date":
            col_profile.valid_count = profile_data.get("valid_count")
            col_profile.invalid_count = profile_data.get("invalid_count")
            col_profile.detected_format = profile_data.get("detected_format")
            col_profile.format_consistent = profile_data.get("format_consistent")
            col_profile.min_date = profile_data.get("min_date")
            col_profile.max_date = profile_data.get("max_date")
            col_profile.span_days = profile_data.get("span_days")

        elif col_type == "money":
            col_profile.valid_count = profile_data.get("valid_count")
            col_profile.invalid_count = profile_data.get("invalid_count")
            col_profile.min_value = profile_data.get("min_value")
            col_profile.max_value = profile_data.get("max_value")
            col_profile.two_decimal_ok = profile_data.get("two_decimal_ok")
            col_profile.disallowed_symbols_found = profile_data.get("disallowed_symbols_found")

        column_profiles.append(col_profile)

    # Generate candidate keys based on distinct ratios and null counts
    candidate_keys = []
    for col_profile in column_profiles:
        if col_profile.distinct_pct >= 95.0:  # High cardinality
            distinct_ratio = col_profile.distinct_count / row_count if row_count > 0 else 0.0
            null_ratio = col_profile.null_count / row_count if row_count > 0 else 0.0
            score = distinct_ratio * (1.0 - null_ratio)

            if score >= 0.9:  # Only suggest strong candidates
                candidate_keys.append(CandidateKey(
                    columns=[col_profile.name],
                    distinct_ratio=distinct_ratio,
                    null_ratio_sum=null_ratio,
                    score=score
                ))

    # Sort by score descending
    candidate_keys.sort(key=lambda k: k.score, reverse=True)

    # Build complete profile
    profile = ProfileResponse(
        run_id=run_id,
        file=file_metadata,
        errors=errors,
        warnings=warnings,
        columns=column_profiles,
        candidate_keys=candidate_keys[:5]  # Top 5 candidates
    )

    # Save profile to outputs directory
    outputs_dir = Path("/data/outputs") / str(run_id)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    profile_path = outputs_dir / "profile.json"
    with open(profile_path, 'w') as f:
        # Convert to dict and serialize
        profile_dict = profile.model_dump(mode='json')
        json.dump(profile_dict, f, indent=2)

    return profile


@router.get("/{run_id}/candidate-keys", response_model=CandidateKeysResponse)
async def get_candidate_keys(run_id: UUID) -> CandidateKeysResponse:
    """
    Get candidate key suggestions for a completed run.

    Returns suggested candidate keys based on high cardinality and low null counts.
    Keys are scored using the formula: distinct_ratio * (1 - null_ratio)

    Args:
        run_id: Run UUID

    Returns:
        CandidateKeysResponse with suggested keys and metadata

    Raises:
        HTTPException: If run not found or not completed
    """
    workspace = get_workspace()

    if not workspace.run_exists(run_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    metadata = workspace.load_metadata(run_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    # Check if processing is complete
    if metadata.state != RunState.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Processing not complete yet (state: {metadata.state})"
        )

    # Check if we have column profiles
    if not metadata.column_profiles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile data available"
        )

    # Read the normalized CSV to get row count
    run_dir = workspace.get_run_dir(run_id)
    normalized_csv = run_dir / "normalized.csv"

    if not normalized_csv.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile data not found"
        )

    # Count rows
    row_count = 0
    with open(normalized_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=metadata.delimiter)
        for _ in reader:
            row_count += 1

    # Generate candidate keys based on distinct ratios and null counts
    candidate_keys = []
    for col_name, profile in metadata.column_profiles.items():
        distinct_pct = profile.get("distinct_pct", 0.0)

        if distinct_pct >= 95.0:  # High cardinality threshold
            null_count = profile.get("null_count", 0)
            distinct_count = profile.get("distinct_count", 0)

            distinct_ratio = distinct_count / row_count if row_count > 0 else 0.0
            null_ratio = null_count / row_count if row_count > 0 else 0.0
            score = distinct_ratio * (1.0 - null_ratio)

            if score >= 0.9:  # Only suggest strong candidates
                candidate_keys.append(CandidateKey(
                    columns=[col_name],
                    distinct_ratio=distinct_ratio,
                    null_ratio_sum=null_ratio,
                    score=score
                ))

    # Sort by score descending
    candidate_keys.sort(key=lambda k: k.score, reverse=True)

    return CandidateKeysResponse(
        run_id=run_id,
        candidate_keys=candidate_keys[:5],  # Top 5 candidates
        total_rows=row_count
    )


@router.post("/{run_id}/confirm-keys", response_model=DuplicateDetectionResponse)
async def confirm_keys(run_id: UUID, request: ConfirmKeysRequest) -> DuplicateDetectionResponse:
    """
    Confirm candidate keys and run duplicate detection.

    Accepts user-confirmed key columns and performs exact duplicate detection
    based on those keys. Results are stored in workspace metadata.

    Args:
        run_id: Run UUID
        request: ConfirmKeysRequest with column names to use as keys

    Returns:
        DuplicateDetectionResponse with duplicate detection results

    Raises:
        HTTPException: If run not found, not completed, or keys invalid
    """
    workspace = get_workspace()

    if not workspace.run_exists(run_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    metadata = workspace.load_metadata(run_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    # Check if processing is complete
    if metadata.state != RunState.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Processing not complete yet (state: {metadata.state})"
        )

    # Verify confirmed keys exist in column profiles
    if not metadata.column_profiles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile data available"
        )

    available_columns = set(metadata.column_profiles.keys())
    confirmed_keys = request.keys
    invalid_keys = [k for k in confirmed_keys if k not in available_columns]

    if invalid_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid key columns: {', '.join(invalid_keys)}"
        )

    # Read the normalized CSV and detect duplicates
    run_dir = workspace.get_run_dir(run_id)
    normalized_csv = run_dir / "normalized.csv"

    if not normalized_csv.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile data not found"
        )

    # Simple hash-based duplicate detection
    key_counts = {}
    duplicate_groups_data = {}
    row_num = 0
    total_rows = 0

    with open(normalized_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=metadata.delimiter)

        for row in reader:
            row_num += 1
            total_rows += 1

            # Build key value from confirmed columns
            key_parts = []
            has_null = False
            for col in confirmed_keys:
                value = row.get(col, '')
                if not value:
                    has_null = True
                    break
                key_parts.append(value)

            if has_null:
                continue  # Skip rows with null keys

            key_value = '|'.join(key_parts)

            if key_value not in key_counts:
                key_counts[key_value] = 0
                duplicate_groups_data[key_value] = []

            key_counts[key_value] += 1
            duplicate_groups_data[key_value].append(row_num)

    # Find duplicates (keys that appear more than once)
    duplicate_groups = []
    total_duplicate_rows = 0
    duplicate_count = 0

    for key_value, count in key_counts.items():
        if count > 1:
            duplicate_count += 1
            total_duplicate_rows += (count - 1)  # Don't count the first occurrence

            duplicate_groups.append(DuplicateGroup(
                key_value=key_value,
                count=count,
                row_numbers=duplicate_groups_data[key_value]
            ))

    # Sort duplicate groups by count descending (most frequent first)
    duplicate_groups.sort(key=lambda g: g.count, reverse=True)

    # Calculate duplicate percentage
    duplicate_percentage = (total_duplicate_rows / total_rows * 100.0) if total_rows > 0 else 0.0

    # Store results in metadata
    duplicate_results = {
        "confirmed_keys": confirmed_keys,
        "has_duplicates": duplicate_count > 0,
        "duplicate_count": duplicate_count,
        "total_duplicate_rows": total_duplicate_rows,
        "duplicate_percentage": duplicate_percentage,
        "top_duplicate_groups": [
            {
                "key_value": g.key_value,
                "count": g.count,
                "row_numbers": g.row_numbers[:10]  # Store first 10 row numbers
            }
            for g in duplicate_groups[:10]  # Store top 10 groups
        ]
    }

    # Save duplicate results to metadata
    metadata_dict = metadata.to_dict()
    metadata_dict["duplicate_detection"] = duplicate_results

    # Save updated metadata
    with open(workspace.get_metadata_path(run_id), 'w') as f:
        json.dump(metadata_dict, f, indent=2)

    return DuplicateDetectionResponse(
        run_id=run_id,
        confirmed_keys=confirmed_keys,
        has_duplicates=duplicate_count > 0,
        duplicate_count=duplicate_count,
        total_duplicate_rows=total_duplicate_rows,
        duplicate_percentage=duplicate_percentage,
        duplicate_groups=duplicate_groups[:10]  # Return top 10 groups
    )
