"""
Pytest configuration and shared fixtures for data-profiler tests.

This module provides reusable test fixtures and configuration
for the entire test suite.
"""
import os
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_csv_basic(temp_dir: Path) -> Path:
    """Create a basic valid CSV file for testing."""
    csv_path = temp_dir / "basic.csv"
    csv_path.write_text(
        "ID|Name|Age|Salary\n"
        "1|Alice|30|50000.00\n"
        "2|Bob|25|45000.00\n"
        "3|Charlie|35|60000.00\n",
        encoding="utf-8"
    )
    return csv_path


@pytest.fixture
def sample_csv_quoted(temp_dir: Path) -> Path:
    """Create CSV with quoted fields containing delimiters."""
    csv_path = temp_dir / "quoted.csv"
    csv_path.write_text(
        'ID|Name|Description\n'
        '1|"Smith, John"|"Uses | delimiter"\n'
        '2|"Doe, Jane"|Normal field\n'
        '3|Bob|"Quote has ""doubled"" quotes"\n',
        encoding="utf-8"
    )
    return csv_path


@pytest.fixture
def sample_csv_crlf(temp_dir: Path) -> Path:
    """Create CSV with CRLF line endings."""
    csv_path = temp_dir / "crlf.csv"
    csv_path.write_bytes(
        b"ID|Name\r\n"
        b"1|Alice\r\n"
        b"2|Bob\r\n"
    )
    return csv_path


@pytest.fixture
def sample_csv_money_violations(temp_dir: Path) -> Path:
    """Create CSV with various money format violations."""
    csv_path = temp_dir / "money_violations.csv"
    csv_path.write_text(
        "ID|Amount|InvalidAmount\n"
        "1|100.00|$100.00\n"
        "2|250.50|1,250.50\n"
        "3|99.99|(99.99)\n"
        "4|1000.00|1000\n",
        encoding="utf-8"
    )
    return csv_path


@pytest.fixture
def sample_csv_numeric_violations(temp_dir: Path) -> Path:
    """Create CSV with numeric format violations."""
    csv_path = temp_dir / "numeric_violations.csv"
    csv_path.write_text(
        "ID|Value|InvalidValue\n"
        "1|123|$123\n"
        "2|456.78|1,456.78\n"
        "3|999|abc123\n",
        encoding="utf-8"
    )
    return csv_path


@pytest.fixture
def sample_csv_dates(temp_dir: Path) -> Path:
    """Create CSV with various date formats."""
    csv_path = temp_dir / "dates.csv"
    csv_path.write_text(
        "ID|DateYYYYMMDD|DateMixed|OutOfRange\n"
        "1|20221109|20221109|18991231\n"
        "2|20230115|2023-01-15|20300101\n"
        "3|20220301|20220301|\n",
        encoding="utf-8"
    )
    return csv_path


@pytest.fixture
def sample_csv_mixed_types(temp_dir: Path) -> Path:
    """Create CSV with mixed types in columns."""
    csv_path = temp_dir / "mixed_types.csv"
    csv_path.write_text(
        "ID|MixedColumn\n"
        "1|100\n"
        "2|text\n"
        "3|150.50\n"
        "4|more text\n",
        encoding="utf-8"
    )
    return csv_path


@pytest.fixture
def sample_csv_duplicates(temp_dir: Path) -> Path:
    """Create CSV with duplicate records."""
    csv_path = temp_dir / "duplicates.csv"
    csv_path.write_text(
        "ID|Name|Email\n"
        "1|Alice|alice@example.com\n"
        "2|Bob|bob@example.com\n"
        "1|Alice|alice@example.com\n"
        "3|Charlie|charlie@example.com\n"
        "2|Bob|bob@example.com\n",
        encoding="utf-8"
    )
    return csv_path


@pytest.fixture
def sample_csv_invalid_utf8(temp_dir: Path) -> Path:
    """Create file with invalid UTF-8 byte sequence."""
    csv_path = temp_dir / "invalid_utf8.csv"
    csv_path.write_bytes(
        b"ID|Name\n"
        b"1|Alice\n"
        b"2|\xFF\xFEInvalid\n"  # Invalid UTF-8
    )
    return csv_path


@pytest.fixture
def sample_csv_jagged(temp_dir: Path) -> Path:
    """Create CSV with inconsistent column counts (jagged)."""
    csv_path = temp_dir / "jagged.csv"
    csv_path.write_text(
        "ID|Name|Age\n"
        "1|Alice|30\n"
        "2|Bob\n"  # Missing Age column
        "3|Charlie|35\n",
        encoding="utf-8"
    )
    return csv_path


@pytest.fixture
def sample_csv_no_header(temp_dir: Path) -> Path:
    """Create CSV with no header row."""
    csv_path = temp_dir / "no_header.csv"
    csv_path.write_text(
        "1|Alice|30\n"
        "2|Bob|25\n",
        encoding="utf-8"
    )
    return csv_path


@pytest.fixture
def api_client():
    """Create test client for API endpoints."""
    from api.app import app
    from api.routers.runs import set_workspace
    from api.storage.workspace import WorkspaceManager

    # Create test workspace in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = WorkspaceManager(Path(tmpdir))
        set_workspace(workspace)

        client = TestClient(app)
        yield client


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace directory for E2E tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture
def sample_csv_simple():
    """Return simple CSV content for E2E tests."""
    return """ID|Name|Email|Status|Score
1|Alice|alice@example.com|Active|95.5
2|Bob|bob@example.com|Active|87.2
3|Charlie|charlie@example.com|Inactive|92.8
4|Diana|diana@example.com|Active|88.1
5|Eve|eve@example.com|Active|91.0"""


@pytest.fixture
def sample_invalid_utf8():
    """Return invalid UTF-8 bytes for testing."""
    return b"ID|Name\n1|Alice\n2|\xFF\xFEInvalid\n"
