"""
Test suite for API endpoints.

RED PHASE: These tests define expected API behavior.

Requirements from spec (OpenAPI 3.1):
- POST /runs - Create profiling run
- POST /runs/{run_id}/upload - Upload file
- GET /runs/{run_id}/status - Get run status
- GET /runs/{run_id}/profile - Get full profile JSON
- GET /runs/{run_id}/metrics.csv - Download CSV metrics
- GET /runs/{run_id}/report.html - Download HTML report
- GET /runs/{run_id}/candidate-keys - Get candidate key suggestions
- POST /runs/{run_id}/confirm-keys - Confirm keys for duplicate check
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create test client for API."""
    from api.app import app
    return TestClient(app)


class TestAPIEndpoints:
    """Test API endpoint functionality."""

    def test_healthz_endpoint(self, api_client):
        """Test health check endpoint."""
        response = api_client.get("/healthz")

        assert response.status_code == 200
        assert response.json() == {"status": "OK"}

    def test_create_run(self, api_client):
        """Test creating a new profiling run."""
        response = api_client.post(
            "/runs",
            json={"delimiter": "|", "quoted": True, "expect_crlf": True}
        )

        assert response.status_code == 201
        data = response.json()
        assert "run_id" in data
        assert len(data["run_id"]) == 36  # UUID length

    def test_create_run_missing_delimiter(self, api_client):
        """Test that delimiter is required when creating run."""
        response = api_client.post("/runs", json={})

        assert response.status_code == 422  # Validation error

    def test_create_run_invalid_delimiter(self, api_client):
        """Test that only pipe and comma delimiters are allowed."""
        response = api_client.post(
            "/runs",
            json={"delimiter": "tab"}
        )

        assert response.status_code == 422

    def test_upload_file(self, api_client, sample_csv_basic: Path):
        """Test uploading a file to a run."""
        # Create run first
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        # Upload file
        with open(sample_csv_basic, "rb") as f:
            response = api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        assert response.status_code == 202  # Accepted

    def test_upload_gzip_file(self, api_client, temp_dir: Path):
        """Test uploading a gzipped file."""
        import gzip

        # Create gzipped file
        gz_path = temp_dir / "test.csv.gz"
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            f.write("ID|Name\n1|Alice\n2|Bob\n")

        # Create run
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        # Upload gzipped file
        with open(gz_path, "rb") as f:
            response = api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv.gz", f, "application/gzip")}
            )

        assert response.status_code == 202

    def test_upload_to_nonexistent_run(self, api_client, sample_csv_basic: Path):
        """Test that uploading to non-existent run fails."""
        fake_run_id = "00000000-0000-0000-0000-000000000000"

        with open(sample_csv_basic, "rb") as f:
            response = api_client.post(
                f"/runs/{fake_run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        assert response.status_code == 404

    def test_get_run_status(self, api_client, sample_csv_basic: Path):
        """Test getting run status."""
        # Create and upload
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(sample_csv_basic, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        # Get status
        response = api_client.get(f"/runs/{run_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert data["state"] in ["queued", "processing", "completed", "failed"]
        assert "progress_pct" in data
        assert "warnings" in data
        assert "errors" in data

    def test_get_run_status_nonexistent(self, api_client):
        """Test getting status of non-existent run."""
        fake_run_id = "00000000-0000-0000-0000-000000000000"

        response = api_client.get(f"/runs/{fake_run_id}/status")

        assert response.status_code == 404

    def test_get_profile(self, api_client, sample_csv_basic: Path):
        """Test getting full profile JSON."""
        # Create, upload, and wait for completion
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(sample_csv_basic, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        # Wait for processing (in real scenario, poll status)
        import time
        time.sleep(1)

        # Get profile
        response = api_client.get(f"/runs/{run_id}/profile")

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "file" in data
        assert "columns" in data
        assert "errors" in data
        assert "warnings" in data

    def test_profile_structure(self, api_client, sample_csv_basic: Path):
        """Test that profile follows expected schema."""
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(sample_csv_basic, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        import time
        time.sleep(1)

        response = api_client.get(f"/runs/{run_id}/profile")
        data = response.json()

        # File metadata
        assert data["file"]["rows"] > 0
        assert data["file"]["columns"] > 0
        assert data["file"]["delimiter"] == "|"
        assert "header" in data["file"]

        # Column profiles
        for col in data["columns"]:
            assert "name" in col
            assert "inferred_type" in col
            assert "null_pct" in col
            assert "distinct_count" in col

    def test_download_metrics_csv(self, api_client, sample_csv_basic: Path):
        """Test downloading metrics as CSV."""
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(sample_csv_basic, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        import time
        time.sleep(1)

        response = api_client.get(f"/runs/{run_id}/metrics.csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"
        assert "column,type,null_pct" in response.text

    def test_download_html_report(self, api_client, sample_csv_basic: Path):
        """Test downloading HTML report."""
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(sample_csv_basic, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        import time
        time.sleep(1)

        response = api_client.get(f"/runs/{run_id}/report.html")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html"
        assert "<html" in response.text.lower()

    def test_get_candidate_keys(self, api_client, sample_csv_basic: Path):
        """Test getting candidate key suggestions."""
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(sample_csv_basic, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        import time
        time.sleep(1)

        response = api_client.get(f"/runs/{run_id}/candidate-keys")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

        if len(data["suggestions"]) > 0:
            suggestion = data["suggestions"][0]
            assert "columns" in suggestion
            assert "distinct_ratio" in suggestion
            assert "null_ratio_sum" in suggestion

    def test_confirm_keys(self, api_client, sample_csv_duplicates: Path):
        """Test confirming keys for duplicate detection."""
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(sample_csv_duplicates, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        import time
        time.sleep(1)

        # Confirm keys
        response = api_client.post(
            f"/runs/{run_id}/confirm-keys",
            json={"keys": [["ID"], ["ID", "Name"]]}
        )

        assert response.status_code == 202

    def test_confirm_keys_invalid_columns(self, api_client, sample_csv_basic: Path):
        """Test that confirming non-existent columns fails."""
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(sample_csv_basic, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        import time
        time.sleep(1)

        response = api_client.post(
            f"/runs/{run_id}/confirm-keys",
            json={"keys": [["NonExistentColumn"]]}
        )

        assert response.status_code == 400

    def test_concurrent_runs(self, api_client, sample_csv_basic: Path):
        """Test that multiple runs can be processed concurrently."""
        # Create two runs
        run1_response = api_client.post("/runs", json={"delimiter": "|"})
        run1_id = run1_response.json()["run_id"]

        run2_response = api_client.post("/runs", json={"delimiter": "|"})
        run2_id = run2_response.json()["run_id"]

        # Upload to both
        with open(sample_csv_basic, "rb") as f:
            api_client.post(
                f"/runs/{run1_id}/upload",
                files={"file": ("test1.csv", f, "text/csv")}
            )

        with open(sample_csv_basic, "rb") as f:
            api_client.post(
                f"/runs/{run2_id}/upload",
                files={"file": ("test2.csv", f, "text/csv")}
            )

        # Both should have status
        status1 = api_client.get(f"/runs/{run1_id}/status")
        status2 = api_client.get(f"/runs/{run2_id}/status")

        assert status1.status_code == 200
        assert status2.status_code == 200
        assert run1_id != run2_id

    def test_api_error_handling(self, api_client, sample_csv_invalid_utf8: Path):
        """Test API error handling for catastrophic errors."""
        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(sample_csv_invalid_utf8, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("invalid.csv", f, "text/csv")}
            )

        import time
        time.sleep(1)

        # Status should show failed state
        status_response = api_client.get(f"/runs/{run_id}/status")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["state"] == "failed"
        assert len(data["errors"]) > 0

    def test_progress_tracking(self, api_client, temp_dir: Path):
        """Test that progress is tracked during processing."""
        # Create larger file
        large_csv = temp_dir / "large.csv"
        with large_csv.open("w", encoding="utf-8") as f:
            f.write("ID|Name|Value\n")
            for i in range(10000):
                f.write(f"{i}|Name{i}|Value{i}\n")

        create_response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = create_response.json()["run_id"]

        with open(large_csv, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("large.csv", f, "text/csv")}
            )

        # Poll status to see progress
        import time
        progress_values = []
        for _ in range(5):
            time.sleep(0.5)
            status_response = api_client.get(f"/runs/{run_id}/status")
            if status_response.status_code == 200:
                progress_values.append(status_response.json()["progress_pct"])

        # Progress should increase or reach 100
        assert any(p > 0 for p in progress_values if p is not None)

    def test_rate_limiting(self, api_client):
        """Test that API has rate limiting (if implemented)."""
        # Attempt many requests quickly
        responses = []
        for _ in range(100):
            response = api_client.post("/runs", json={"delimiter": "|"})
            responses.append(response.status_code)

        # If rate limiting is implemented, some should be 429
        # If not, all should be 201
        assert all(code in [201, 429] for code in responses)
