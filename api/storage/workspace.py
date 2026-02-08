"""
Workspace management for profiling runs.

This module manages run storage, state tracking, and file organization.
"""

import json
import math
import shutil
import gzip as gzip_module
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from ..models.run import ErrorDetail, RunState


@dataclass
class RunMetadata:
    """Metadata for a profiling run."""

    run_id: UUID
    state: RunState
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    delimiter: str = "|"
    quoted: bool = True
    expect_crlf: bool = True
    source_filename: Optional[str] = None
    progress_pct: float = 0.0
    warnings: List[Dict] = None
    errors: List[Dict] = None
    column_profiles: Optional[Dict[str, Dict]] = None
    detection_info: Optional[Dict] = None

    def __post_init__(self):
        """Initialize lists if None."""
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []
        if self.column_profiles is None:
            self.column_profiles = {}
        if self.detection_info is None:
            self.detection_info = {}

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert UUID and datetime to strings
        data['run_id'] = str(data['run_id'])
        data['state'] = data['state'].value if isinstance(data['state'], RunState) else data['state']
        data['created_at'] = data['created_at'].isoformat() if data['created_at'] else None
        data['started_at'] = data['started_at'].isoformat() if data['started_at'] else None
        data['completed_at'] = data['completed_at'].isoformat() if data['completed_at'] else None
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'RunMetadata':
        """Create from dictionary."""
        # Convert strings back to proper types
        data['run_id'] = UUID(data['run_id']) if isinstance(data['run_id'], str) else data['run_id']
        data['state'] = RunState(data['state']) if isinstance(data['state'], str) else data['state']
        data['created_at'] = datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        data['started_at'] = datetime.fromisoformat(data['started_at']) if data.get('started_at') and isinstance(data['started_at'], str) else data.get('started_at')
        data['completed_at'] = datetime.fromisoformat(data['completed_at']) if data.get('completed_at') and isinstance(data['completed_at'], str) else data.get('completed_at')
        return cls(**data)


class WorkspaceManager:
    """
    Manages workspace directories and run state.

    Creates and manages per-run workspaces under /data/work/runs/{uuid}/
    Tracks run metadata and state transitions.
    """

    def __init__(self, work_dir: Path):
        """
        Initialize workspace manager.

        Args:
            work_dir: Base working directory (e.g., /data/work)
        """
        self.work_dir = Path(work_dir)
        self.runs_dir = self.work_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def create_run(
        self,
        delimiter: str,
        quoted: bool = True,
        expect_crlf: bool = True
    ) -> RunMetadata:
        """
        Create a new profiling run.

        Args:
            delimiter: CSV delimiter
            quoted: Whether fields use double-quote escaping
            expect_crlf: Whether to expect CRLF line endings

        Returns:
            RunMetadata for the new run
        """
        run_id = uuid4()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        metadata = RunMetadata(
            run_id=run_id,
            state=RunState.QUEUED,
            created_at=now,
            delimiter=delimiter,
            quoted=quoted,
            expect_crlf=expect_crlf
        )

        # Create run directory
        run_dir = self.get_run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        self.save_metadata(metadata)

        return metadata

    def get_run_dir(self, run_id: UUID) -> Path:
        """
        Get the directory for a specific run.

        Security: Validates path is within workspace to prevent traversal.

        Args:
            run_id: Run UUID

        Returns:
            Path to run directory

        Raises:
            ValueError: If path traversal detected
        """
        run_dir = self.runs_dir / str(run_id)

        # Security: Ensure the resolved path is within runs_dir (prevent path traversal)
        try:
            run_dir.resolve().relative_to(self.runs_dir.resolve())
        except ValueError:
            raise ValueError("Security: Path traversal detected in run_id")

        return run_dir

    def get_metadata_path(self, run_id: UUID) -> Path:
        """
        Get the metadata file path for a run.

        Args:
            run_id: Run UUID

        Returns:
            Path to metadata.json file
        """
        return self.get_run_dir(run_id) / "metadata.json"

    def get_uploaded_file_path(self, run_id: UUID) -> Path:
        """
        Get the uploaded file path for a run.

        Args:
            run_id: Run UUID

        Returns:
            Path to uploaded file
        """
        return self.get_run_dir(run_id) / "uploaded_file"

    def run_exists(self, run_id: UUID) -> bool:
        """
        Check if a run exists.

        Args:
            run_id: Run UUID

        Returns:
            True if run exists
        """
        return self.get_metadata_path(run_id).exists()

    def load_metadata(self, run_id: UUID) -> Optional[RunMetadata]:
        """
        Load metadata for a run.

        Args:
            run_id: Run UUID

        Returns:
            RunMetadata if exists, None otherwise
        """
        metadata_path = self.get_metadata_path(run_id)
        if not metadata_path.exists():
            return None

        with open(metadata_path, 'r') as f:
            data = json.load(f)

        return RunMetadata.from_dict(data)

    def save_metadata(self, metadata: RunMetadata) -> None:
        """
        Save metadata for a run.

        Args:
            metadata: RunMetadata to save
        """
        metadata_path = self.get_metadata_path(metadata.run_id)
        with open(metadata_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)

    def update_state(
        self,
        run_id: UUID,
        state: RunState,
        progress_pct: Optional[float] = None
    ) -> None:
        """
        Update run state.

        Args:
            run_id: Run UUID
            state: New state
            progress_pct: Progress percentage (optional)
        """
        metadata = self.load_metadata(run_id)
        if not metadata:
            raise ValueError(f"Run {run_id} not found")

        metadata.state = state

        if progress_pct is not None:
            metadata.progress_pct = progress_pct

        # Update timestamps based on state
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if state == RunState.PROCESSING and metadata.started_at is None:
            metadata.started_at = now
        elif state in [RunState.COMPLETED, RunState.FAILED]:
            metadata.completed_at = now
            metadata.progress_pct = 100.0 if state == RunState.COMPLETED else metadata.progress_pct

        self.save_metadata(metadata)

    def add_error(self, run_id: UUID, error: ErrorDetail) -> None:
        """
        Add an error to a run.

        Args:
            run_id: Run UUID
            error: ErrorDetail to add
        """
        metadata = self.load_metadata(run_id)
        if not metadata:
            raise ValueError(f"Run {run_id} not found")

        # Check if error code already exists
        error_dict = error.model_dump()
        existing = next((e for e in metadata.errors if e['code'] == error_dict['code']), None)

        if existing:
            # Increment count
            existing['count'] += error_dict['count']
        else:
            # Add new error
            metadata.errors.append(error_dict)

        self.save_metadata(metadata)

    def add_warning(self, run_id: UUID, warning: ErrorDetail) -> None:
        """
        Add a warning to a run.

        Args:
            run_id: Run UUID
            warning: ErrorDetail to add
        """
        metadata = self.load_metadata(run_id)
        if not metadata:
            raise ValueError(f"Run {run_id} not found")

        # Check if warning code already exists
        warning_dict = warning.model_dump()
        existing = next((w for w in metadata.warnings if w['code'] == warning_dict['code']), None)

        if existing:
            # Increment count
            existing['count'] += warning_dict['count']
        else:
            # Add new warning
            metadata.warnings.append(warning_dict)

        self.save_metadata(metadata)

    def save_column_profiles(self, run_id: UUID, column_profiles: Dict[str, Dict]) -> None:
        """
        Save column profile results to run metadata.

        Args:
            run_id: Run UUID
            column_profiles: Dictionary mapping column names to profile results
        """
        metadata = self.load_metadata(run_id)
        if not metadata:
            raise ValueError(f"Run {run_id} not found")

        metadata.column_profiles = column_profiles
        self.save_metadata(metadata)

    def save_uploaded_file(self, run_id: UUID, file_data: bytes, filename: str) -> Path:
        """
        Save uploaded file to run directory.

        Args:
            run_id: Run UUID
            file_data: File content as bytes
            filename: Original filename

        Returns:
            Path to saved file
        """
        file_path = self.get_uploaded_file_path(run_id)

        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_data)

        # Update metadata with filename
        metadata = self.load_metadata(run_id)
        if metadata:
            metadata.source_filename = filename
            self.save_metadata(metadata)

        return file_path

    def cleanup_run(self, run_id: UUID) -> None:
        """
        Clean up all files for a run.

        Args:
            run_id: Run UUID
        """
        run_dir = self.get_run_dir(run_id)
        if run_dir.exists():
            shutil.rmtree(run_dir)

    def list_runs(self) -> List[UUID]:
        """
        List all run IDs.

        Returns:
            List of run UUIDs
        """
        run_ids = []
        for run_dir in self.runs_dir.iterdir():
            if run_dir.is_dir():
                try:
                    run_id = UUID(run_dir.name)
                    run_ids.append(run_id)
                except ValueError:
                    # Skip invalid directory names
                    pass
        return run_ids

    def init_chunked_upload(self, run_id: UUID, filename: str, total_size: int, chunk_size: int) -> dict:
        """
        Initialize chunked upload tracking.

        Args:
            run_id: Run UUID
            filename: Original filename
            total_size: Total file size in bytes
            chunk_size: Size of each chunk in bytes

        Returns:
            Upload info dictionary
        """
        total_chunks = math.ceil(total_size / chunk_size)
        upload_info = {
            "filename": filename,
            "total_size": total_size,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "bytes_received": 0,
            "chunks_received": 0,
            "upload_state": "initialized",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        upload_path = self.get_run_dir(run_id) / "upload_info.json"
        with open(upload_path, 'w') as f:
            json.dump(upload_info, f, indent=2)

        # Create the chunks directory
        chunks_dir = self.get_run_dir(run_id) / "chunks"
        chunks_dir.mkdir(exist_ok=True)

        return upload_info

    def get_upload_info(self, run_id: UUID) -> Optional[dict]:
        """
        Get chunked upload info.

        Args:
            run_id: Run UUID

        Returns:
            Upload info dictionary if exists, None otherwise
        """
        upload_path = self.get_run_dir(run_id) / "upload_info.json"
        if not upload_path.exists():
            return None
        with open(upload_path, 'r') as f:
            return json.load(f)

    def save_chunk(self, run_id: UUID, chunk_index: int, chunk_data: bytes) -> dict:
        """
        Save a chunk and update upload tracking.

        Args:
            run_id: Run UUID
            chunk_index: Index of the chunk being saved
            chunk_data: Chunk data as bytes

        Returns:
            Updated upload info dictionary
        """
        run_dir = self.get_run_dir(run_id)
        chunks_dir = run_dir / "chunks"

        # Save chunk file
        chunk_path = chunks_dir / f"chunk_{chunk_index:06d}"
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)

        # Update upload info
        upload_info = self.get_upload_info(run_id)
        if upload_info:
            upload_info["bytes_received"] += len(chunk_data)
            upload_info["chunks_received"] += 1
            upload_info["upload_state"] = "uploading"

            upload_path = run_dir / "upload_info.json"
            with open(upload_path, 'w') as f:
                json.dump(upload_info, f, indent=2)

        return upload_info

    def assemble_chunks(self, run_id: UUID) -> Path:
        """
        Assemble chunks into final file.

        Args:
            run_id: Run UUID

        Returns:
            Path to assembled file
        """
        run_dir = self.get_run_dir(run_id)
        chunks_dir = run_dir / "chunks"
        upload_info = self.get_upload_info(run_id)

        if not upload_info:
            raise ValueError(f"No upload info for run {run_id}")

        filename = upload_info["filename"]
        output_path = self.get_uploaded_file_path(run_id)
        is_gzipped = filename.endswith('.gz')

        if is_gzipped:
            # Assemble chunks to a temp gz file, then decompress with bomb protection
            gz_path = run_dir / "uploaded_file.gz"
            with open(gz_path, 'wb') as outfile:
                for i in range(upload_info["total_chunks"]):
                    chunk_path = chunks_dir / f"chunk_{i:06d}"
                    if chunk_path.exists():
                        with open(chunk_path, 'rb') as chunk_file:
                            outfile.write(chunk_file.read())

            # Decompress with size limit (gzip bomb protection)
            max_decompressed_size = 10 * 1024 * 1024 * 1024  # 10GB
            bytes_written = 0
            with gzip_module.open(gz_path, 'rb') as gz_file:
                with open(output_path, 'wb') as out_file:
                    while True:
                        block = gz_file.read(65536)
                        if not block:
                            break
                        bytes_written += len(block)
                        if bytes_written > max_decompressed_size:
                            out_file.close()
                            output_path.unlink(missing_ok=True)
                            gz_path.unlink(missing_ok=True)
                            raise ValueError("Decompressed file exceeds maximum size (gzip bomb protection)")
                        out_file.write(block)

            # Clean up gz file
            gz_path.unlink(missing_ok=True)
        else:
            # Assemble chunks directly
            with open(output_path, 'wb') as outfile:
                for i in range(upload_info["total_chunks"]):
                    chunk_path = chunks_dir / f"chunk_{i:06d}"
                    if chunk_path.exists():
                        with open(chunk_path, 'rb') as chunk_file:
                            outfile.write(chunk_file.read())

        # Update upload state
        upload_info["upload_state"] = "completed"
        upload_path = run_dir / "upload_info.json"
        with open(upload_path, 'w') as f:
            json.dump(upload_info, f, indent=2)

        # Update metadata with filename
        metadata = self.load_metadata(run_id)
        if metadata:
            metadata.source_filename = filename
            self.save_metadata(metadata)

        # Clean up chunks directory
        if chunks_dir.exists():
            shutil.rmtree(chunks_dir)

        return output_path
