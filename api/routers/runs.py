"""
Run lifecycle endpoints.

This module implements the FastAPI routes for profiling run management.
"""

import gzip
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ..models.run import (
    ErrorDetail,
    FileUploadResponse,
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
from ..storage.workspace import WorkspaceManager

# Workspace manager (initialized lazily)
_workspace: Optional[WorkspaceManager] = None


def get_workspace() -> WorkspaceManager:
    """Get or create workspace manager."""
    global _workspace
    if _workspace is None:
        work_dir = Path("/data/work")
        _workspace = WorkspaceManager(work_dir)
    return _workspace


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
        metadata = workspace.create_run(
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

    Args:
        run_id: Run UUID
        file_content: File content as bytes
        delimiter: CSV delimiter
        quoted: Whether fields use quoting
        workspace: WorkspaceManager instance

    Raises:
        HTTPException: If catastrophic errors occur
    """
    try:
        # Step 1: UTF-8 Validation (10% progress)
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
            return

        # Step 2: CRLF Detection (20% progress)
        workspace.update_state(run_id, RunState.PROCESSING, progress_pct=20.0)

        stream.seek(0)
        detector = CRLFDetector(stream)
        line_ending_result = detector.detect()

        # Normalize line endings
        normalized_content = detector.normalize()

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

        # Step 3: CSV Parsing (50% progress)
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
            else:
                workspace.add_error(
                    run_id,
                    ErrorDetail(code=error_code, message=f"Parser error: {error_code}", count=count)
                )

        # Step 4: Type Inference (70% progress)
        workspace.update_state(run_id, RunState.PROCESSING, progress_pct=60.0)

        # Save normalized content to temp file for type inference
        run_dir = workspace.get_run_dir(run_id)
        temp_csv = run_dir / "normalized.csv"
        with open(temp_csv, 'wb') as f:
            f.write(normalized_content)

        # Run type inference
        inferrer = TypeInferrer(sample_size=None)  # Full inference
        type_result = inferrer.infer_column_types(temp_csv, delimiter=delimiter)

        # Process type inference results
        for col_name, col_info in type_result.columns.items():
            if col_info.error_count > 0:
                workspace.add_error(
                    run_id,
                    ErrorDetail(
                        code=f"E_{col_info.inferred_type.upper()}_FORMAT",
                        message=f"Format violations in column '{col_name}'",
                        count=col_info.error_count
                    )
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

        # Step 5: Complete (100% progress)
        workspace.update_state(run_id, RunState.COMPLETED, progress_pct=100.0)

    except ParserError as e:
        # Catastrophic parser error
        workspace.update_state(run_id, RunState.FAILED)
        workspace.add_error(
            run_id,
            ErrorDetail(code=e.code, message=e.message, count=1)
        )
    except Exception as e:
        # Unexpected error
        workspace.update_state(run_id, RunState.FAILED)
        workspace.add_error(
            run_id,
            ErrorDetail(code="E_PROCESSING_FAILED", message=str(e), count=1)
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
        errors=errors
    )
