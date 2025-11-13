"""
Tests for PII-aware audit logging.

This module tests the audit logging service to ensure:
1. All audit events are logged correctly
2. PII/PHI is never stored (only counts, codes, hashes)
3. Append-only logs are created per run
4. SHA-256 hashes are computed correctly
"""

import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from ..services.audit import AuditEventType, AuditLogger


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for audit logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def audit_logger(temp_output_dir):
    """Create AuditLogger instance with temp directory."""
    return AuditLogger(temp_output_dir)


def test_audit_logger_initialization(temp_output_dir):
    """Test that AuditLogger creates output directory."""
    logger = AuditLogger(temp_output_dir)
    assert temp_output_dir.exists()
    assert logger.output_dir == temp_output_dir


def test_log_run_created(audit_logger, temp_output_dir):
    """Test logging run creation event."""
    run_id = uuid4()

    audit_logger.log_run_created(
        run_id=run_id,
        delimiter="|",
        quoted=True,
        expect_crlf=True
    )

    # Verify audit log file was created
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    assert audit_log_path.exists()

    # Verify log content
    with open(audit_log_path, 'r') as f:
        line = f.readline()
        entry = json.loads(line)

    assert entry['event_type'] == AuditEventType.RUN_CREATED.value
    assert entry['run_id'] == str(run_id)
    assert entry['details']['delimiter'] == "|"
    assert entry['details']['quoted'] is True
    assert entry['details']['expect_crlf'] is True
    assert 'timestamp' in entry


def test_log_file_uploaded(audit_logger, temp_output_dir):
    """Test logging file upload with hash and byte count."""
    run_id = uuid4()
    file_data = b"test,data\n1,2\n3,4\n"

    audit_logger.log_file_uploaded(
        run_id=run_id,
        filename="test.csv",
        file_data=file_data,
        is_gzipped=False
    )

    # Verify audit log
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        entry = json.loads(f.readline())

    assert entry['event_type'] == AuditEventType.FILE_UPLOADED.value
    assert entry['details']['filename'] == "test.csv"
    assert entry['details']['byte_count'] == len(file_data)
    assert entry['details']['is_gzipped'] is False
    assert 'file_hash_sha256' in entry['details']
    # Verify hash is hex string
    assert len(entry['details']['file_hash_sha256']) == 64
    assert all(c in '0123456789abcdef' for c in entry['details']['file_hash_sha256'])


def test_no_pii_in_logs(audit_logger, temp_output_dir):
    """Test that actual data values are never logged (PII protection)."""
    run_id = uuid4()

    # Simulate a file with PHI
    phi_data = b"SSN,Name,DOB\n123-45-6789,John Doe,1980-01-01\n"

    audit_logger.log_file_uploaded(
        run_id=run_id,
        filename="patient_data.csv",
        file_data=phi_data,
        is_gzipped=False
    )

    # Read entire audit log
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        log_content = f.read()

    # Verify PHI is NOT in the log
    assert 'John Doe' not in log_content
    assert '123-45-6789' not in log_content
    assert '1980-01-01' not in log_content

    # Verify only metadata is logged
    assert 'file_hash_sha256' in log_content
    assert 'byte_count' in log_content
    assert 'filename' in log_content


def test_log_validation_completed(audit_logger, temp_output_dir):
    """Test logging validation stage completion."""
    run_id = uuid4()

    audit_logger.log_validation_completed(
        run_id=run_id,
        utf8_valid=True,
        crlf_count=10,
        lf_count=2,
        cr_count=0,
        mixed_endings=True
    )

    # Verify log
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        entry = json.loads(f.readline())

    assert entry['event_type'] == AuditEventType.VALIDATION_COMPLETED.value
    assert entry['details']['utf8_valid'] is True
    assert entry['details']['crlf_count'] == 10
    assert entry['details']['lf_count'] == 2
    assert entry['details']['cr_count'] == 0
    assert entry['details']['mixed_endings'] is True


def test_log_parsing_completed(audit_logger, temp_output_dir):
    """Test logging parsing stage with row/column counts (no values)."""
    run_id = uuid4()

    audit_logger.log_parsing_completed(
        run_id=run_id,
        row_count=1000,
        column_count=25,
        header_names=['id', 'name', 'email'],
        error_rollup={'E_QUOTE_RULE': 5, 'W_LINE_ENDING': 1}
    )

    # Verify log
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        entry = json.loads(f.readline())

    assert entry['event_type'] == AuditEventType.PARSING_COMPLETED.value
    assert entry['details']['row_count'] == 1000
    assert entry['details']['column_count'] == 25
    assert entry['details']['header_names'] == ['id', 'name', 'email']
    assert entry['details']['error_rollup'] == {'E_QUOTE_RULE': 5, 'W_LINE_ENDING': 1}


def test_log_type_inference_completed(audit_logger, temp_output_dir):
    """Test logging type inference with types and counts (no values)."""
    run_id = uuid4()

    audit_logger.log_type_inference_completed(
        run_id=run_id,
        column_types={'id': 'numeric', 'name': 'alpha', 'amount': 'money'},
        error_counts={'id': 0, 'name': 0, 'amount': 3},
        warning_counts={'id': 0, 'name': 5, 'amount': 0}
    )

    # Verify log
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        entry = json.loads(f.readline())

    assert entry['event_type'] == AuditEventType.TYPE_INFERENCE_COMPLETED.value
    assert entry['details']['column_types'] == {'id': 'numeric', 'name': 'alpha', 'amount': 'money'}
    assert entry['details']['error_counts'] == {'id': 0, 'name': 0, 'amount': 3}
    assert entry['details']['warning_counts'] == {'id': 0, 'name': 5, 'amount': 0}


def test_log_profiling_completed(audit_logger, temp_output_dir):
    """Test logging profiling completion with aggregate counts (no values)."""
    run_id = uuid4()

    audit_logger.log_profiling_completed(
        run_id=run_id,
        columns_profiled=25,
        total_null_count=150,
        total_distinct_count=5000
    )

    # Verify log
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        entry = json.loads(f.readline())

    assert entry['event_type'] == AuditEventType.PROFILING_COMPLETED.value
    assert entry['details']['columns_profiled'] == 25
    assert entry['details']['total_null_count'] == 150
    assert entry['details']['total_distinct_count'] == 5000


def test_log_error_and_warning(audit_logger, temp_output_dir):
    """Test logging errors and warnings (counts only, no values)."""
    run_id = uuid4()

    # Log error
    audit_logger.log_error(
        run_id=run_id,
        error_code="E_NUMERIC_FORMAT",
        count=10
    )

    # Log warning
    audit_logger.log_warning(
        run_id=run_id,
        warning_code="W_DATE_FORMAT",
        count=3
    )

    # Verify logs
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        lines = f.readlines()

    error_entry = json.loads(lines[0])
    assert error_entry['event_type'] == AuditEventType.ERROR_RECORDED.value
    assert error_entry['details']['error_code'] == "E_NUMERIC_FORMAT"
    assert error_entry['details']['count'] == 10

    warning_entry = json.loads(lines[1])
    assert warning_entry['event_type'] == AuditEventType.WARNING_RECORDED.value
    assert warning_entry['details']['warning_code'] == "W_DATE_FORMAT"
    assert warning_entry['details']['count'] == 3


def test_log_run_completed(audit_logger, temp_output_dir):
    """Test logging run completion with totals."""
    run_id = uuid4()

    audit_logger.log_run_completed(
        run_id=run_id,
        total_errors=15,
        total_warnings=8
    )

    # Verify log
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        entry = json.loads(f.readline())

    assert entry['event_type'] == AuditEventType.RUN_COMPLETED.value
    assert entry['details']['total_errors'] == 15
    assert entry['details']['total_warnings'] == 8


def test_log_run_failed(audit_logger, temp_output_dir):
    """Test logging run failure."""
    run_id = uuid4()

    audit_logger.log_run_failed(
        run_id=run_id,
        error_code="E_UTF8_INVALID",
        error_message="Invalid UTF-8 byte sequence at offset 1234"
    )

    # Verify log
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        entry = json.loads(f.readline())

    assert entry['event_type'] == AuditEventType.RUN_FAILED.value
    assert entry['details']['error_code'] == "E_UTF8_INVALID"
    assert entry['details']['error_message'] == "Invalid UTF-8 byte sequence at offset 1234"


def test_append_only_logs(audit_logger, temp_output_dir):
    """Test that audit logs are append-only."""
    run_id = uuid4()

    # Log multiple events
    audit_logger.log_run_created(run_id, "|", True, True)
    audit_logger.log_file_uploaded(run_id, "test.csv", b"data", False)
    audit_logger.log_validation_started(run_id)
    audit_logger.log_validation_completed(run_id, True, 10, 0, 0, False)
    audit_logger.log_parsing_started(run_id)

    # Verify all entries are present
    audit_log_path = temp_output_dir / str(run_id) / "audit.log.json"
    with open(audit_log_path, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 5

    # Verify order is preserved (FIFO)
    events = [json.loads(line)['event_type'] for line in lines]
    assert events == [
        AuditEventType.RUN_CREATED.value,
        AuditEventType.FILE_UPLOADED.value,
        AuditEventType.VALIDATION_STARTED.value,
        AuditEventType.VALIDATION_COMPLETED.value,
        AuditEventType.PARSING_STARTED.value,
    ]


def test_read_audit_log(audit_logger, temp_output_dir):
    """Test reading audit log entries."""
    run_id = uuid4()

    # Log several events
    audit_logger.log_run_created(run_id, "|", True, True)
    audit_logger.log_file_uploaded(run_id, "test.csv", b"data", False)
    audit_logger.log_validation_started(run_id)

    # Read entries
    entries = audit_logger.read_audit_log(run_id)

    assert len(entries) == 3
    assert entries[0].event_type == AuditEventType.RUN_CREATED
    assert entries[1].event_type == AuditEventType.FILE_UPLOADED
    assert entries[2].event_type == AuditEventType.VALIDATION_STARTED


def test_read_nonexistent_audit_log(audit_logger):
    """Test reading audit log for nonexistent run returns empty list."""
    run_id = uuid4()
    entries = audit_logger.read_audit_log(run_id)
    assert entries == []


def test_sha256_hash_consistency(audit_logger, temp_output_dir):
    """Test that SHA-256 hash is consistent for same data."""
    run_id1 = uuid4()
    run_id2 = uuid4()
    file_data = b"test,data\n1,2\n3,4\n"

    # Log same file twice
    audit_logger.log_file_uploaded(run_id1, "test1.csv", file_data, False)
    audit_logger.log_file_uploaded(run_id2, "test2.csv", file_data, False)

    # Read hashes
    audit_log1 = temp_output_dir / str(run_id1) / "audit.log.json"
    audit_log2 = temp_output_dir / str(run_id2) / "audit.log.json"

    with open(audit_log1, 'r') as f:
        entry1 = json.loads(f.readline())
    with open(audit_log2, 'r') as f:
        entry2 = json.loads(f.readline())

    # Hashes should be identical for same data
    assert entry1['details']['file_hash_sha256'] == entry2['details']['file_hash_sha256']


def test_audit_log_per_run_isolation(audit_logger, temp_output_dir):
    """Test that audit logs are isolated per run."""
    run_id1 = uuid4()
    run_id2 = uuid4()

    # Log events for different runs
    audit_logger.log_run_created(run_id1, "|", True, True)
    audit_logger.log_run_created(run_id2, ",", False, False)

    # Verify separate log files
    audit_log1 = temp_output_dir / str(run_id1) / "audit.log.json"
    audit_log2 = temp_output_dir / str(run_id2) / "audit.log.json"

    assert audit_log1.exists()
    assert audit_log2.exists()
    assert audit_log1 != audit_log2

    # Verify correct content in each
    with open(audit_log1, 'r') as f:
        entry1 = json.loads(f.readline())
    with open(audit_log2, 'r') as f:
        entry2 = json.loads(f.readline())

    assert entry1['run_id'] == str(run_id1)
    assert entry2['run_id'] == str(run_id2)
    assert entry1['details']['delimiter'] == "|"
    assert entry2['details']['delimiter'] == ","
