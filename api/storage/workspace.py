"""
Workspace management for profiling runs.

This module manages run storage, state tracking, and file organization.
"""

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
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

    def __post_init__(self):
        """Initialize lists if None."""
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []
        if self.column_profiles is None:
            self.column_profiles = {}

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
        now = datetime.utcnow()

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

        Args:
            run_id: Run UUID

        Returns:
            Path to run directory
        """
        return self.runs_dir / str(run_id)

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
        now = datetime.utcnow()
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
