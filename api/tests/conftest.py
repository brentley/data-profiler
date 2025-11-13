"""
Pytest configuration and shared fixtures for VQ8 Data Profiler tests.

This module provides reusable fixtures for:
- Temporary workspaces
- Test data generation
- SQLite database mocking
- FastAPI test clients
- Sample files
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator, BinaryIO
import pytest
from io import BytesIO, StringIO
import sqlite3


# ============================================================================
# Workspace Fixtures
# ============================================================================

@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """
    Create an isolated temporary workspace for each test.

    Yields:
        Path: Temporary directory path

    Cleanup:
        Removes entire workspace after test completion
    """
    workspace = Path(tempfile.mkdtemp(prefix="vq8_test_"))

    # Create standard subdirectories
    (workspace / "uploads").mkdir()
    (workspace / "work").mkdir()
    (workspace / "outputs").mkdir()

    try:
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def temp_db_path(temp_workspace: Path) -> Path:
    """
    Provide a temporary SQLite database path.

    Args:
        temp_workspace: Workspace fixture

    Returns:
        Path: Database file path
    """
    return temp_workspace / "test.db"


# ============================================================================
# Data Generation Fixtures
# ============================================================================

@pytest.fixture
def sample_csv_simple() -> str:
    """
    Simple pipe-delimited CSV with mixed data types.

    Returns:
        str: CSV content
    """
    return """id|name|amount|date|status
1|Alice|100.50|20230101|active
2|Bob|250.75|20230102|inactive
3|Charlie|99.99|20230103|active
4|Diana|1000.00|20230104|pending
5|Eve|50.25|20230105|active"""


@pytest.fixture
def sample_csv_with_nulls() -> str:
    """
    CSV with null values represented as empty fields.

    Returns:
        str: CSV content
    """
    return """id|name|amount|date|status
1|Alice|100.50|20230101|active
2||250.75||inactive
3|Charlie||20230103|
4|Diana|1000.00||pending
5|||20230105|active"""


@pytest.fixture
def sample_csv_quoted() -> str:
    """
    CSV with quoted fields containing embedded delimiters.

    Returns:
        str: CSV content
    """
    return """id,name,description,amount
1,"Smith, John","Contains, commas",100.50
2,"Doe, Jane","Line 1
Line 2",250.75
3,"Brown, Bob","Quotes ""inside"" quotes",99.99"""


@pytest.fixture
def sample_csv_money_violations() -> str:
    """
    CSV with various money format violations.

    Returns:
        str: CSV content
    """
    return """id|amount_good|amount_bad1|amount_bad2|amount_bad3
1|100.50|100.5|$100.50|1,000.50
2|250.75|250|250.75$|(250.75)
3|99.99|99.999|99.99USD|99,99"""


@pytest.fixture
def sample_csv_date_formats() -> str:
    """
    CSV with various date formats.

    Returns:
        str: CSV content
    """
    return """id|date_yyyymmdd|date_mixed|date_out_of_range
1|20230101|20230101|18000101
2|20230102|2023-01-02|20500101
3|20230103|01/03/2023|19991231"""


@pytest.fixture
def sample_large_csv(temp_workspace: Path) -> Path:
    """
    Generate a large CSV file for performance testing.

    Args:
        temp_workspace: Workspace fixture

    Returns:
        Path: Path to generated file

    Note:
        Generates ~10MB file with 100k rows x 10 columns
    """
    file_path = temp_workspace / "large_sample.csv"

    with open(file_path, 'w') as f:
        # Header
        f.write("id|col1|col2|col3|col4|col5|col6|col7|col8|col9\n")

        # Generate 100k rows
        for i in range(100000):
            f.write(f"{i}|val{i}|{i % 100}|{i * 1.5:.2f}|2023{i%12+1:02d}{i%28+1:02d}|")
            f.write(f"text{i}|{i % 10}|{i * 2.0:.2f}|code{i%50}|{i % 2}\n")

    return file_path


@pytest.fixture
def sample_utf8_multibyte() -> bytes:
    """
    UTF-8 content with multibyte characters.

    Returns:
        bytes: UTF-8 encoded content
    """
    content = """id|name|city|emoji
1|张三|北京|😀
2|Müller|München|🎉
3|José|São Paulo|🌟
4|Γεωργία|Αθήνα|🎨"""
    return content.encode('utf-8')


@pytest.fixture
def sample_invalid_utf8() -> bytes:
    """
    Invalid UTF-8 byte sequence.

    Returns:
        bytes: Invalid UTF-8 content
    """
    # Valid header followed by invalid UTF-8
    return b"id|name|value\n1|Test\xFF Invalid|100\n"


# ============================================================================
# Binary Stream Fixtures
# ============================================================================

@pytest.fixture
def binary_stream_factory():
    """
    Factory for creating BytesIO streams from content.

    Returns:
        Callable: Function that creates BytesIO from bytes or str
    """
    def create_stream(content: bytes | str) -> BytesIO:
        if isinstance(content, str):
            content = content.encode('utf-8')
        return BytesIO(content)

    return create_stream


# ============================================================================
# SQLite Fixtures
# ============================================================================

@pytest.fixture
def in_memory_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Create an in-memory SQLite database for fast testing.

    Yields:
        sqlite3.Connection: Database connection

    Cleanup:
        Closes connection after test
    """
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def profiler_schema(in_memory_db: sqlite3.Connection) -> sqlite3.Connection:
    """
    Create profiler schema in SQLite database.

    Args:
        in_memory_db: Database connection

    Returns:
        sqlite3.Connection: Database with schema created
    """
    cursor = in_memory_db.cursor()

    # Create tables per spec
    cursor.execute("""
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            state TEXT NOT NULL,
            progress_pct REAL DEFAULT 0,
            delimiter TEXT,
            expect_crlf BOOLEAN,
            quoted BOOLEAN,
            source_filename TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            level TEXT NOT NULL,
            code TEXT,
            message TEXT,
            redaction_applied BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE columns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            name TEXT NOT NULL,
            inferred_type TEXT,
            null_count INTEGER DEFAULT 0,
            nonnull_count INTEGER DEFAULT 0,
            distinct_count INTEGER DEFAULT 0,
            top_values_json TEXT,
            length_min INTEGER,
            length_max INTEGER,
            length_avg REAL,
            numeric_json TEXT,
            money_json TEXT,
            date_json TEXT,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            code TEXT NOT NULL,
            message TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE candidate_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            columns_json TEXT NOT NULL,
            distinct_ratio REAL,
            null_ratio_sum REAL,
            score REAL,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE confirmed_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            columns_json TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        )
    """)

    in_memory_db.commit()

    return in_memory_db


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """
    FastAPI test client for API integration tests.

    Returns:
        TestClient: FastAPI test client

    Note:
        Requires FastAPI app to be implemented
    """
    # This will be implemented once FastAPI app exists
    # from fastapi.testclient import TestClient
    # from app import app
    # return TestClient(app)
    pytest.skip("FastAPI app not yet implemented")


# ============================================================================
# Error Scenario Fixtures
# ============================================================================

@pytest.fixture
def catastrophic_errors():
    """
    Sample catastrophic error scenarios.

    Returns:
        dict: Error scenarios with expected outcomes
    """
    return {
        'invalid_utf8': {
            'content': b"id|name\n1\xFFInvalid\n",
            'expected_code': 'E_UTF8_INVALID',
            'should_stop': True
        },
        'missing_header': {
            'content': b"1|Alice|100\n2|Bob|200\n",
            'expected_code': 'E_HEADER_MISSING',
            'should_stop': True
        },
        'jagged_row': {
            'content': b"id|name|amount\n1|Alice|100\n2|Bob\n",
            'expected_code': 'E_JAGGED_ROW',
            'should_stop': True
        }
    }


@pytest.fixture
def non_catastrophic_errors():
    """
    Sample non-catastrophic error scenarios.

    Returns:
        dict: Error scenarios that should continue processing
    """
    return {
        'quoting_violation': {
            'content': 'id,name,desc\n1,"Name,100\n',
            'expected_code': 'E_QUOTE_RULE',
            'should_continue': True
        },
        'money_format': {
            'content': 'id|amount\n1|$100.50\n',
            'expected_code': 'E_MONEY_FORMAT',
            'should_continue': True
        },
        'numeric_format': {
            'content': 'id|value\n1|1,000.50\n',
            'expected_code': 'E_NUMERIC_FORMAT',
            'should_continue': True
        }
    }


# ============================================================================
# Performance Fixtures
# ============================================================================

@pytest.fixture
def memory_profiler():
    """
    Memory usage profiler for performance tests.

    Returns:
        Callable: Function to measure memory usage
    """
    import tracemalloc

    def profile(func, *args, **kwargs):
        tracemalloc.start()

        result = func(*args, **kwargs)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            'result': result,
            'current_memory_mb': current / 1024 / 1024,
            'peak_memory_mb': peak / 1024 / 1024
        }

    return profile


@pytest.fixture
def time_profiler():
    """
    Execution time profiler for performance tests.

    Returns:
        Callable: Function to measure execution time
    """
    import time

    def profile(func, *args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()

        return {
            'result': result,
            'elapsed_seconds': end - start
        }

    return profile


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """
    Configure pytest with custom markers.

    Args:
        config: Pytest config object
    """
    config.addinivalue_line(
        "markers", "unit: Unit tests for isolated components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for service interaction"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end workflow tests"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and scalability tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take >1 second"
    )
    config.addinivalue_line(
        "markers", "catastrophic: Tests for catastrophic error scenarios"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers automatically.

    Args:
        config: Pytest config
        items: List of test items
    """
    for item in items:
        # Auto-mark based on file path
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
