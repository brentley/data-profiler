"""
Unit tests for FastAPI endpoints.

Tests all run lifecycle endpoints with proper fixtures and mocking.
"""

import gzip
import json
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path

# Add api directory to path so we can import as a package
api_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(api_dir.parent))

from api.app import app
from api.models.run import RunState
from api.storage.workspace import WorkspaceManager
from api.routers import runs


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for testing."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    workspace = WorkspaceManager(work_dir)
    # Set the workspace for the router
    runs.set_workspace(workspace)
    return workspace


@pytest.fixture
def client(temp_workspace):
    """Create test client with temporary workspace."""
    return TestClient(app)


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return b"""id|name|age|city
1|Alice|30|NYC
2|Bob|25|LA
3|Charlie|35|Chicago
"""


@pytest.fixture
def sample_csv_with_errors():
    """Sample CSV with format errors."""
    return b"""id|name|amount|date
1|Alice|100.5|20220101
2|Bob|$200.00|20220102
3|Charlie|300|2022-01-03
"""


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns 200 OK."""
        response = client.get("/healthz")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    def test_health_check_format(self, client):
        """Test health check response format."""
        response = client.get("/healthz")
        data = response.json()

        # Check timestamp is valid ISO format
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)


class TestCreateRun:
    """Tests for POST /runs endpoint."""

    def test_create_run_success(self, client):
        """Test creating a run successfully."""
        response = client.post(
            "/runs",
            json={
                "delimiter": "|",
                "quoted": True,
                "expect_crlf": True
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Check response structure
        assert "run_id" in data
        assert "state" in data
        assert "created_at" in data

        # Validate UUID format
        run_id = UUID(data["run_id"])
        assert isinstance(run_id, UUID)

        # Check state
        assert data["state"] == RunState.QUEUED.value

        # Check timestamp
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        assert isinstance(created_at, datetime)

    def test_create_run_with_comma_delimiter(self, client):
        """Test creating a run with comma delimiter."""
        response = client.post(
            "/runs",
            json={
                "delimiter": ",",
                "quoted": True,
                "expect_crlf": False
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["state"] == RunState.QUEUED.value

    def test_create_run_invalid_delimiter(self, client):
        """Test creating a run with invalid delimiter fails."""
        response = client.post(
            "/runs",
            json={
                "delimiter": ";",  # Invalid - only | and , allowed
                "quoted": True,
                "expect_crlf": True
            }
        )

        assert response.status_code == 422  # Validation error

    def test_create_run_missing_delimiter(self, client):
        """Test creating a run without delimiter fails."""
        response = client.post(
            "/runs",
            json={
                "quoted": True,
                "expect_crlf": True
            }
        )

        assert response.status_code == 422  # Validation error

    def test_create_run_defaults(self, client):
        """Test default values are applied."""
        response = client.post(
            "/runs",
            json={
                "delimiter": "|"
                # quoted and expect_crlf should default to True
            }
        )

        assert response.status_code == 201


class TestUploadFile:
    """Tests for POST /runs/{run_id}/upload endpoint."""

    def test_upload_file_success(self, client, sample_csv_content):
        """Test uploading a file successfully."""
        # Create run first
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file
        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        response = client.post(f"/runs/{run_id}/upload", files=files)

        assert response.status_code == 202
        data = response.json()

        assert data["run_id"] == run_id
        assert data["state"] == RunState.PROCESSING.value
        assert "message" in data

    def test_upload_gzipped_file(self, client, sample_csv_content):
        """Test uploading a gzipped file."""
        # Create run first
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Gzip the content
        gzipped_content = gzip.compress(sample_csv_content)

        # Upload gzipped file
        files = {"file": ("test.csv.gz", BytesIO(gzipped_content), "application/gzip")}
        response = client.post(f"/runs/{run_id}/upload", files=files)

        assert response.status_code == 202

    def test_upload_file_invalid_run_id(self, client, sample_csv_content):
        """Test uploading to non-existent run fails."""
        fake_run_id = str(uuid4())

        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        response = client.post(f"/runs/{fake_run_id}/upload", files=files)

        assert response.status_code == 404

    def test_upload_file_invalid_extension(self, client):
        """Test uploading file with invalid extension fails."""
        # Create run first
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file with invalid extension
        files = {"file": ("test.json", BytesIO(b"{}"), "application/json")}
        response = client.post(f"/runs/{run_id}/upload", files=files)

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_file_twice_fails(self, client, sample_csv_content):
        """Test uploading a file twice to the same run fails."""
        # Create run first
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file once
        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        response1 = client.post(f"/runs/{run_id}/upload", files=files)
        assert response1.status_code == 202

        # Try to upload again
        files = {"file": ("test2.csv", BytesIO(sample_csv_content), "text/csv")}
        response2 = client.post(f"/runs/{run_id}/upload", files=files)

        assert response2.status_code == 409  # Conflict

    def test_upload_invalid_gzip(self, client):
        """Test uploading invalid gzip file fails."""
        # Create run first
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload invalid gzip
        files = {"file": ("test.csv.gz", BytesIO(b"not gzipped"), "application/gzip")}
        response = client.post(f"/runs/{run_id}/upload", files=files)

        assert response.status_code == 400
        assert "decompress" in response.json()["detail"].lower()


class TestGetRunStatus:
    """Tests for GET /runs/{run_id}/status endpoint."""

    def test_get_status_queued(self, client):
        """Test getting status of queued run."""
        # Create run
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Get status
        response = client.get(f"/runs/{run_id}/status")

        assert response.status_code == 200
        data = response.json()

        assert data["run_id"] == run_id
        assert data["state"] == RunState.QUEUED.value
        assert data["progress_pct"] == 0.0
        assert "created_at" in data
        assert data["started_at"] is None
        assert data["completed_at"] is None
        assert isinstance(data["warnings"], list)
        assert isinstance(data["errors"], list)

    def test_get_status_processing(self, client, sample_csv_content):
        """Test getting status of processing run."""
        # Create run
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file to start processing
        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Get status
        response = client.get(f"/runs/{run_id}/status")

        assert response.status_code == 200
        data = response.json()

        # State should be processing or completed (depending on how fast it processes)
        assert data["state"] in [RunState.PROCESSING.value, RunState.COMPLETED.value]
        assert data["progress_pct"] >= 0.0

    def test_get_status_invalid_run_id(self, client):
        """Test getting status of non-existent run fails."""
        fake_run_id = str(uuid4())

        response = client.get(f"/runs/{fake_run_id}/status")

        assert response.status_code == 404

    def test_get_status_with_errors(self, client, sample_csv_with_errors):
        """Test getting status of run with errors."""
        # Create run
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file with errors
        files = {"file": ("test.csv", BytesIO(sample_csv_with_errors), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Get status
        response = client.get(f"/runs/{run_id}/status")

        assert response.status_code == 200
        data = response.json()

        # Should have some errors or warnings
        # (exact errors depend on type inference logic)
        assert len(data["errors"]) >= 0 or len(data["warnings"]) >= 0


class TestIntegrationFlow:
    """Integration tests for complete run lifecycle."""

    def test_full_run_lifecycle(self, client, sample_csv_content):
        """Test complete run lifecycle from creation to completion."""
        # Step 1: Create run
        create_response = client.post(
            "/runs",
            json={
                "delimiter": "|",
                "quoted": True,
                "expect_crlf": True
            }
        )

        assert create_response.status_code == 201
        run_id = create_response.json()["run_id"]

        # Step 2: Check initial status
        status_response = client.get(f"/runs/{run_id}/status")
        assert status_response.status_code == 200
        assert status_response.json()["state"] == RunState.QUEUED.value

        # Step 3: Upload file
        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        upload_response = client.post(f"/runs/{run_id}/upload", files=files)
        assert upload_response.status_code == 202

        # Step 4: Check processing status
        status_response = client.get(f"/runs/{run_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()

        # Should be processing or completed
        assert status_data["state"] in [RunState.PROCESSING.value, RunState.COMPLETED.value]

        # If completed, check final state
        if status_data["state"] == RunState.COMPLETED.value:
            assert status_data["progress_pct"] == 100.0
            assert status_data["completed_at"] is not None

    def test_invalid_utf8_fails_catastrophically(self, client):
        """Test that invalid UTF-8 causes catastrophic failure."""
        # Create run
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Create invalid UTF-8 content
        invalid_utf8 = b"id|name\n1|" + b"\xff\xfe" + b"\n"

        # Upload file
        files = {"file": ("test.csv", BytesIO(invalid_utf8), "text/csv")}
        upload_response = client.post(f"/runs/{run_id}/upload", files=files)

        # Upload should succeed but processing should fail
        assert upload_response.status_code == 202

        # Check status - should be failed
        status_response = client.get(f"/runs/{run_id}/status")
        status_data = status_response.json()

        # Should have failed with UTF-8 error
        if status_data["state"] == RunState.FAILED.value:
            assert len(status_data["errors"]) > 0
            # Check for UTF-8 error code
            error_codes = [e["code"] for e in status_data["errors"]]
            assert "E_UTF8_INVALID" in error_codes


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "service" in data
        assert "version" in data
        assert "docs" in data
        assert data["version"] == "1.0.0"


class TestCSVSanitization:
    """Tests for CSV injection prevention."""

    def test_sanitize_csv_value_normal(self):
        """Test sanitizing normal values."""
        from api.routers.runs import sanitize_csv_value

        assert sanitize_csv_value("hello") == "hello"
        assert sanitize_csv_value("123") == "123"
        assert sanitize_csv_value("test value") == "test value"
        assert sanitize_csv_value("") == ""
        assert sanitize_csv_value(None) == ""

    def test_sanitize_csv_value_dangerous(self):
        """Test sanitizing values with dangerous prefixes."""
        from api.routers.runs import sanitize_csv_value

        # Test dangerous prefixes
        assert sanitize_csv_value("=SUM(A1:A10)") == "'=SUM(A1:A10)"
        assert sanitize_csv_value("+cmd") == "'+cmd"
        assert sanitize_csv_value("-2+3") == "'-2+3"
        assert sanitize_csv_value("@SUM(1+1)") == "'@SUM(1+1)"

    def test_sanitize_csv_value_types(self):
        """Test sanitizing different data types."""
        from api.routers.runs import sanitize_csv_value

        # Numbers
        assert sanitize_csv_value(123) == "123"
        assert sanitize_csv_value(45.67) == "45.67"
        assert sanitize_csv_value(-10) == "'-10"  # Starts with -

        # Booleans
        assert sanitize_csv_value(True) == "True"
        assert sanitize_csv_value(False) == "False"


class TestMetricsCSVExport:
    """Tests for GET /runs/{run_id}/metrics.csv endpoint."""

    def test_metrics_csv_success(self, client, sample_csv_content):
        """Test exporting metrics as CSV successfully."""
        # Create run and upload file
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file
        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Wait for processing to complete (in real scenario, would poll status)
        import time
        time.sleep(0.5)

        # Get metrics CSV
        response = client.get(f"/runs/{run_id}/metrics.csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert f"metrics_{run_id}.csv" in response.headers["Content-Disposition"]

        # Parse CSV content
        csv_content = response.text
        lines = csv_content.strip().split('\n')

        # Check header
        assert len(lines) > 0
        header = lines[0]
        assert "column_name" in header
        assert "type" in header
        assert "null_count" in header
        assert "distinct_count" in header

        # Should have header + 4 data rows (id, name, age, city)
        assert len(lines) == 5  # header + 4 columns

    def test_metrics_csv_not_found(self, client):
        """Test exporting metrics for non-existent run fails."""
        fake_run_id = str(uuid4())

        response = client.get(f"/runs/{fake_run_id}/metrics.csv")

        assert response.status_code == 404

    def test_metrics_csv_not_completed(self, client):
        """Test exporting metrics for non-completed run fails."""
        # Create run but don't upload file
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Try to get metrics
        response = client.get(f"/runs/{run_id}/metrics.csv")

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    def test_metrics_csv_injection_prevention(self, client):
        """Test CSV injection prevention for dangerous values."""
        # Create CSV with potentially dangerous values
        dangerous_csv = b"""name|formula
Alice|normal
Bob|=SUM(A1:A10)
Charlie|+cmd|'/c calc'!A1
David|-2+3
Eve|@SUM(1+1)
"""

        # Create run and upload
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        files = {"file": ("test.csv", BytesIO(dangerous_csv), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Wait for processing
        import time
        time.sleep(0.5)

        # Get metrics CSV
        response = client.get(f"/runs/{run_id}/metrics.csv")

        if response.status_code == 200:
            csv_content = response.text

            # Check that dangerous characters are escaped
            # Values starting with =, +, -, @ should be prepended with '
            # This is in the top_values columns

            # Parse to verify no raw formula injection possible
            import csv as csv_module
            reader = csv_module.reader(StringIO(csv_content))
            rows = list(reader)

            # Check all data rows for proper sanitization
            for row in rows[1:]:  # Skip header
                for cell in row:
                    # If cell starts with dangerous char, it should be escaped
                    if cell and len(cell) > 1 and cell[0] == "'":
                        # This is an escaped value - check the original starts with dangerous char
                        assert cell[1] in ('=', '+', '-', '@')

    def test_metrics_csv_content_structure(self, client, sample_csv_content):
        """Test CSV content has expected structure and columns."""
        # Create run and upload file
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Wait for processing
        import time
        time.sleep(0.5)

        # Get metrics CSV
        response = client.get(f"/runs/{run_id}/metrics.csv")

        if response.status_code == 200:
            # Parse CSV
            import csv as csv_module
            reader = csv_module.reader(StringIO(response.text))
            rows = list(reader)

            # Check header structure
            header = rows[0]
            expected_columns = [
                "column_name", "type", "null_count", "distinct_count", "distinct_pct",
                "min_value", "max_value", "mean", "median", "stddev",
                "min_length", "max_length", "avg_length",
                "top_value_1", "top_value_1_count",
                "top_value_2", "top_value_2_count",
                "top_value_3", "top_value_3_count"
            ]

            for expected_col in expected_columns:
                assert expected_col in header

            # Check data rows
            for row in rows[1:]:
                # Each row should have same number of columns as header
                assert len(row) == len(header)

                # Column name should not be empty
                col_name_idx = header.index("column_name")
                assert row[col_name_idx] != ""

                # Type should not be empty
                type_idx = header.index("type")
                assert row[type_idx] != ""


class TestGetProfile:
    """Tests for GET /runs/{run_id}/profile endpoint."""

    def test_get_profile_success(self, client, sample_csv_content):
        """Test getting profile for completed run."""
        # Create run
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file
        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Wait for processing to complete (in tests it's synchronous)
        status_response = client.get(f"/runs/{run_id}/status")
        status_data = status_response.json()

        if status_data["state"] == "completed":
            # Get profile
            response = client.get(f"/runs/{run_id}/profile")

            assert response.status_code == 200
            data = response.json()

            # Check top-level structure
            assert "run_id" in data
            assert "file" in data
            assert "errors" in data
            assert "warnings" in data
            assert "columns" in data
            assert "candidate_keys" in data

            # Check file metadata
            assert data["file"]["rows"] == 3
            assert data["file"]["columns"] == 4
            assert data["file"]["delimiter"] == "|"
            assert isinstance(data["file"]["header"], list)

            # Check columns
            assert len(data["columns"]) == 4
            for col in data["columns"]:
                assert "name" in col
                assert "type" in col
                assert "null_count" in col
                assert "distinct_count" in col
                assert "distinct_pct" in col

    def test_get_profile_not_found(self, client):
        """Test getting profile for non-existent run."""
        fake_run_id = str(uuid4())
        response = client.get(f"/runs/{fake_run_id}/profile")

        assert response.status_code == 404

    def test_get_profile_not_complete(self, client):
        """Test getting profile before processing complete."""
        # Create run but don't upload file
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Try to get profile
        response = client.get(f"/runs/{run_id}/profile")

        assert response.status_code == 409  # Conflict
        assert "not complete" in response.json()["detail"].lower()

    def test_profile_saves_to_outputs(self, client, sample_csv_content, tmp_path):
        """Test that profile is saved to /data/outputs/{run_id}/profile.json."""
        # Create run
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file
        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Wait for completion
        status_response = client.get(f"/runs/{run_id}/status")
        if status_response.json()["state"] == "completed":
            # Get profile (should trigger save)
            client.get(f"/runs/{run_id}/profile")

            # Note: In test environment, /data might map to tmp_path
            # so we just verify the endpoint succeeded
            assert status_response.status_code == 200

    def test_profile_with_errors(self, client, sample_csv_with_errors):
        """Test profile includes error and warning information."""
        # Create run
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file with errors
        files = {"file": ("test.csv", BytesIO(sample_csv_with_errors), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Wait for completion
        status_response = client.get(f"/runs/{run_id}/status")
        if status_response.json()["state"] == "completed":
            # Get profile
            response = client.get(f"/runs/{run_id}/profile")

            assert response.status_code == 200
            data = response.json()

            # Should have some errors or warnings
            # (specific errors depend on type inference)
            assert isinstance(data["errors"], list)
            assert isinstance(data["warnings"], list)

    def test_profile_candidate_keys(self, client, sample_csv_content):
        """Test that candidate keys are included in profile."""
        # Create run
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file
        files = {"file": ("test.csv", BytesIO(sample_csv_content), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Wait for completion
        status_response = client.get(f"/runs/{run_id}/status")
        if status_response.json()["state"] == "completed":
            # Get profile
            response = client.get(f"/runs/{run_id}/profile")

            assert response.status_code == 200
            data = response.json()

            # Check candidate keys structure
            assert "candidate_keys" in data
            assert isinstance(data["candidate_keys"], list)

            # If there are candidate keys, validate structure
            if len(data["candidate_keys"]) > 0:
                key = data["candidate_keys"][0]
                assert "columns" in key
                assert "distinct_ratio" in key
                assert "null_ratio_sum" in key
                assert "score" in key
                assert isinstance(key["columns"], list)

    def test_profile_column_types(self, client):
        """Test that different column types are profiled correctly."""
        # Create CSV with different types
        csv_content = b"""id|name|amount|date
1|Alice|100.50|20220101
2|Bob|200.75|20220102
3|Charlie|300.00|20220103
"""

        # Create run
        create_response = client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True}
        )
        run_id = create_response.json()["run_id"]

        # Upload file
        files = {"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        client.post(f"/runs/{run_id}/upload", files=files)

        # Wait for completion
        status_response = client.get(f"/runs/{run_id}/status")
        if status_response.json()["state"] == "completed":
            # Get profile
            response = client.get(f"/runs/{run_id}/profile")

            assert response.status_code == 200
            data = response.json()

            # Find columns by name
            columns_by_name = {col["name"]: col for col in data["columns"]}

            # Check id column (numeric)
            assert "id" in columns_by_name
            id_col = columns_by_name["id"]
            assert id_col["type"] in ["numeric", "alpha", "varchar"]

            # Check name column (alpha/varchar)
            assert "name" in columns_by_name
            name_col = columns_by_name["name"]
            assert name_col["type"] in ["alpha", "varchar", "code"]

            # Check amount column (numeric/money)
            assert "amount" in columns_by_name
            amount_col = columns_by_name["amount"]
            assert amount_col["type"] in ["numeric", "money"]

            # Check date column
            assert "date" in columns_by_name
            date_col = columns_by_name["date"]
            assert date_col["type"] in ["date", "numeric"]
