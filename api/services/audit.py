"""
PII-aware audit logging service.

This module provides audit logging functionality that redacts PII/PHI and
tracks only metadata (counts, codes, hashes, timestamps) for compliance.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID


class AuditEventType(str, Enum):
    """Types of audit events."""

    RUN_CREATED = "run_created"
    FILE_UPLOADED = "file_uploaded"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    PARSING_STARTED = "parsing_started"
    PARSING_COMPLETED = "parsing_completed"
    TYPE_INFERENCE_STARTED = "type_inference_started"
    TYPE_INFERENCE_COMPLETED = "type_inference_completed"
    PROFILING_STARTED = "profiling_started"
    PROFILING_COMPLETED = "profiling_completed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    ERROR_RECORDED = "error_recorded"
    WARNING_RECORDED = "warning_recorded"


@dataclass
class AuditEntry:
    """
    Single audit log entry with PII redaction.

    Stores only metadata: counts, codes, hashes, timestamps.
    Never stores actual data values to protect PHI/PII.
    """

    timestamp: str
    event_type: AuditEventType
    run_id: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type.value if isinstance(self.event_type, AuditEventType) else self.event_type,
            "run_id": self.run_id,
            "details": self.details
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AuditEntry':
        """Create from dictionary."""
        data['event_type'] = AuditEventType(data['event_type']) if isinstance(data['event_type'], str) else data['event_type']
        return cls(**data)


class AuditLogger:
    """
    PII-aware audit logger for profiling runs.

    Creates append-only audit logs per run at:
    /data/outputs/{run_id}/audit.log.json

    Logs only metadata (no PHI/PII):
    - File hashes (SHA-256)
    - Byte counts
    - Row/column counts
    - Error codes and counts (not values)
    - Timestamps for all stages
    """

    def __init__(self, output_dir: Path):
        """
        Initialize audit logger.

        Args:
            output_dir: Base output directory (e.g., /data/outputs)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_audit_log_path(self, run_id: UUID) -> Path:
        """
        Get audit log path for a run.

        Args:
            run_id: Run UUID

        Returns:
            Path to audit.log.json
        """
        run_output_dir = self.output_dir / str(run_id)
        run_output_dir.mkdir(parents=True, exist_ok=True)
        return run_output_dir / "audit.log.json"

    def _append_entry(self, run_id: UUID, entry: AuditEntry) -> None:
        """
        Append audit entry to log file.

        Args:
            run_id: Run UUID
            entry: AuditEntry to append
        """
        audit_log_path = self._get_audit_log_path(run_id)

        # Append as JSON line
        with open(audit_log_path, 'a') as f:
            json.dump(entry.to_dict(), f)
            f.write('\n')

    def _now(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    def _compute_file_hash(self, file_data: bytes) -> str:
        """
        Compute SHA-256 hash of file data.

        Args:
            file_data: File content as bytes

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(file_data).hexdigest()

    def log_run_created(
        self,
        run_id: UUID,
        delimiter: str,
        quoted: bool,
        expect_crlf: bool
    ) -> None:
        """
        Log run creation event.

        Args:
            run_id: Run UUID
            delimiter: CSV delimiter
            quoted: Whether fields use quoting
            expect_crlf: Whether CRLF line endings expected
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.RUN_CREATED,
            run_id=str(run_id),
            details={
                "delimiter": delimiter,
                "quoted": quoted,
                "expect_crlf": expect_crlf
            }
        )
        self._append_entry(run_id, entry)

    def log_file_uploaded(
        self,
        run_id: UUID,
        filename: str,
        file_data: bytes,
        is_gzipped: bool
    ) -> None:
        """
        Log file upload event with metadata only.

        Args:
            run_id: Run UUID
            filename: Original filename (no path info)
            file_data: File content as bytes (for hashing)
            is_gzipped: Whether file was gzipped
        """
        file_hash = self._compute_file_hash(file_data)
        byte_count = len(file_data)

        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.FILE_UPLOADED,
            run_id=str(run_id),
            details={
                "filename": filename,
                "file_hash_sha256": file_hash,
                "byte_count": byte_count,
                "is_gzipped": is_gzipped
            }
        )
        self._append_entry(run_id, entry)

    def log_validation_started(self, run_id: UUID) -> None:
        """
        Log validation stage start.

        Args:
            run_id: Run UUID
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.VALIDATION_STARTED,
            run_id=str(run_id),
            details={}
        )
        self._append_entry(run_id, entry)

    def log_validation_completed(
        self,
        run_id: UUID,
        utf8_valid: bool,
        crlf_count: int,
        lf_count: int,
        cr_count: int,
        mixed_endings: bool
    ) -> None:
        """
        Log validation stage completion.

        Args:
            run_id: Run UUID
            utf8_valid: Whether UTF-8 validation passed
            crlf_count: Count of CRLF line endings
            lf_count: Count of LF line endings
            cr_count: Count of CR line endings
            mixed_endings: Whether line endings are mixed
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.VALIDATION_COMPLETED,
            run_id=str(run_id),
            details={
                "utf8_valid": utf8_valid,
                "crlf_count": crlf_count,
                "lf_count": lf_count,
                "cr_count": cr_count,
                "mixed_endings": mixed_endings
            }
        )
        self._append_entry(run_id, entry)

    def log_parsing_started(self, run_id: UUID) -> None:
        """
        Log parsing stage start.

        Args:
            run_id: Run UUID
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.PARSING_STARTED,
            run_id=str(run_id),
            details={}
        )
        self._append_entry(run_id, entry)

    def log_parsing_completed(
        self,
        run_id: UUID,
        row_count: int,
        column_count: int,
        header_names: List[str],
        error_rollup: Dict[str, int]
    ) -> None:
        """
        Log parsing stage completion.

        Args:
            run_id: Run UUID
            row_count: Number of rows parsed
            column_count: Number of columns
            header_names: Column names from header (metadata, not data)
            error_rollup: Dictionary of error codes to counts
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.PARSING_COMPLETED,
            run_id=str(run_id),
            details={
                "row_count": row_count,
                "column_count": column_count,
                "header_names": header_names,
                "error_rollup": error_rollup
            }
        )
        self._append_entry(run_id, entry)

    def log_type_inference_started(self, run_id: UUID) -> None:
        """
        Log type inference stage start.

        Args:
            run_id: Run UUID
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.TYPE_INFERENCE_STARTED,
            run_id=str(run_id),
            details={}
        )
        self._append_entry(run_id, entry)

    def log_type_inference_completed(
        self,
        run_id: UUID,
        column_types: Dict[str, str],
        error_counts: Dict[str, int],
        warning_counts: Dict[str, int]
    ) -> None:
        """
        Log type inference stage completion.

        Args:
            run_id: Run UUID
            column_types: Dictionary of column name to inferred type
            error_counts: Dictionary of column name to error count
            warning_counts: Dictionary of column name to warning count
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.TYPE_INFERENCE_COMPLETED,
            run_id=str(run_id),
            details={
                "column_types": column_types,
                "error_counts": error_counts,
                "warning_counts": warning_counts
            }
        )
        self._append_entry(run_id, entry)

    def log_profiling_started(self, run_id: UUID) -> None:
        """
        Log profiling stage start.

        Args:
            run_id: Run UUID
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.PROFILING_STARTED,
            run_id=str(run_id),
            details={}
        )
        self._append_entry(run_id, entry)

    def log_profiling_completed(
        self,
        run_id: UUID,
        columns_profiled: int,
        total_null_count: int,
        total_distinct_count: int
    ) -> None:
        """
        Log profiling stage completion.

        Args:
            run_id: Run UUID
            columns_profiled: Number of columns profiled
            total_null_count: Total null count across all columns
            total_distinct_count: Total distinct count across all columns
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.PROFILING_COMPLETED,
            run_id=str(run_id),
            details={
                "columns_profiled": columns_profiled,
                "total_null_count": total_null_count,
                "total_distinct_count": total_distinct_count
            }
        )
        self._append_entry(run_id, entry)

    def log_run_completed(
        self,
        run_id: UUID,
        total_errors: int,
        total_warnings: int
    ) -> None:
        """
        Log run completion.

        Args:
            run_id: Run UUID
            total_errors: Total error count
            total_warnings: Total warning count
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.RUN_COMPLETED,
            run_id=str(run_id),
            details={
                "total_errors": total_errors,
                "total_warnings": total_warnings
            }
        )
        self._append_entry(run_id, entry)

    def log_run_failed(
        self,
        run_id: UUID,
        error_code: str,
        error_message: str
    ) -> None:
        """
        Log run failure.

        Args:
            run_id: Run UUID
            error_code: Error code (e.g., E_UTF8_INVALID)
            error_message: Error message (metadata only, no PHI)
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.RUN_FAILED,
            run_id=str(run_id),
            details={
                "error_code": error_code,
                "error_message": error_message
            }
        )
        self._append_entry(run_id, entry)

    def log_error(
        self,
        run_id: UUID,
        error_code: str,
        count: int
    ) -> None:
        """
        Log error occurrence (counts only, no values).

        Args:
            run_id: Run UUID
            error_code: Error code
            count: Number of occurrences
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.ERROR_RECORDED,
            run_id=str(run_id),
            details={
                "error_code": error_code,
                "count": count
            }
        )
        self._append_entry(run_id, entry)

    def log_warning(
        self,
        run_id: UUID,
        warning_code: str,
        count: int
    ) -> None:
        """
        Log warning occurrence (counts only, no values).

        Args:
            run_id: Run UUID
            warning_code: Warning code
            count: Number of occurrences
        """
        entry = AuditEntry(
            timestamp=self._now(),
            event_type=AuditEventType.WARNING_RECORDED,
            run_id=str(run_id),
            details={
                "warning_code": warning_code,
                "count": count
            }
        )
        self._append_entry(run_id, entry)

    def read_audit_log(self, run_id: UUID) -> List[AuditEntry]:
        """
        Read all audit entries for a run.

        Args:
            run_id: Run UUID

        Returns:
            List of AuditEntry objects
        """
        audit_log_path = self._get_audit_log_path(run_id)

        if not audit_log_path.exists():
            return []

        entries = []
        with open(audit_log_path, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    entries.append(AuditEntry.from_dict(data))

        return entries
