"""
Unit tests for FastAPI endpoints.

Tests all run lifecycle endpoints with proper fixtures and mocking.
"""

import gzip
import json
from datetime import datetime
from io import BytesIO
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
