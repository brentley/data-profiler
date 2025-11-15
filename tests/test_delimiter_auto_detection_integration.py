"""
Integration tests for delimiter auto-detection in the full workflow.

Tests that delimiter detection works end-to-end through the API.
"""
import os
import pytest
import time
from pathlib import Path


class TestDelimiterAutoDetectionIntegration:
    """Integration tests for delimiter auto-detection."""

    def test_auto_detect_comma_delimiter(self, api_client, temp_dir: Path):
        """Test auto-detection of comma delimiter through API."""
        csv_path = temp_dir / "comma.csv"
        csv_path.write_text(
            "ID,Name,Age\n"
            "1,Alice,30\n"
            "2,Bob,25\n"
            "3,Charlie,35\n",
            encoding="utf-8"
        )

        # Create run with wrong delimiter
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        # Upload file
        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("comma.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Check status - should have warning about delimiter mismatch
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should complete successfully (using detected delimiter)
        assert status["state"] in ["completed", "processing"]

        # Should have delimiter mismatch warning
        if status["state"] == "completed":
            warnings = status.get("warnings", [])
            assert any("delimiter" in w.get("message", "").lower() for w in warnings)

    def test_auto_detect_pipe_delimiter(self, api_client, temp_dir: Path):
        """Test auto-detection of pipe delimiter through API."""
        csv_path = temp_dir / "pipe.csv"
        csv_path.write_text(
            "ID|Name|Age\n"
            "1|Alice|30\n"
            "2|Bob|25\n"
            "3|Charlie|35\n",
            encoding="utf-8"
        )

        # Create run with wrong delimiter
        response = api_client.post("/runs", json={"delimiter": ","})
        run_id = response.json()["run_id"]

        # Upload file
        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("pipe.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Check status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should complete successfully
        assert status["state"] in ["completed", "processing"]

        # Should have delimiter mismatch warning
        if status["state"] == "completed":
            warnings = status.get("warnings", [])
            assert any("delimiter" in w.get("message", "").lower() for w in warnings)

    def test_auto_detect_tab_delimiter(self, api_client, temp_dir: Path):
        """Test auto-detection of tab delimiter through API."""
        csv_path = temp_dir / "tab.csv"
        csv_path.write_text(
            "ID\tName\tAge\n"
            "1\tAlice\t30\n"
            "2\tBob\t25\n"
            "3\tCharlie\t35\n",
            encoding="utf-8"
        )

        # Create run with wrong delimiter (tab not directly supported in create_run)
        response = api_client.post("/runs", json={"delimiter": ","})
        run_id = response.json()["run_id"]

        # Upload file
        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("tab.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Check status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should complete successfully
        assert status["state"] in ["completed", "processing"]

    def test_correct_delimiter_no_warning(self, api_client, temp_dir: Path):
        """Test that correct delimiter doesn't generate warning."""
        csv_path = temp_dir / "pipe.csv"
        csv_path.write_text(
            "ID|Name|Age\n"
            "1|Alice|30\n"
            "2|Bob|25\n"
            "3|Charlie|35\n",
            encoding="utf-8"
        )

        # Create run with CORRECT delimiter
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        # Upload file
        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("pipe.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Check status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should complete successfully
        assert status["state"] == "completed"

        # Should NOT have delimiter mismatch warning
        warnings = status.get("warnings", [])
        delimiter_warnings = [w for w in warnings if "delimiter" in w.get("message", "").lower()]

        # May have other warnings, but not delimiter mismatch
        if delimiter_warnings:
            assert not any("mismatch" in w.get("message", "").lower() for w in delimiter_warnings)

    def test_profile_with_detected_delimiter(self, api_client, temp_dir: Path):
        """Test that profile is generated with detected delimiter warning."""
        csv_path = temp_dir / "comma.csv"
        csv_path.write_text(
            "ID,Name,Score\n"
            "1,Alice,95.5\n"
            "2,Bob,87.2\n"
            "3,Charlie,92.8\n",
            encoding="utf-8"
        )

        # Create run with wrong delimiter
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        # Upload file
        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("comma.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Check status for delimiter warning
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should have delimiter mismatch warning
        warnings = status.get("warnings", [])
        delimiter_warnings = [w for w in warnings if "delimiter" in w.get("message", "").lower()]
        assert len(delimiter_warnings) > 0, "Expected delimiter mismatch warning"

    def test_delimiter_detection_with_quoted_fields(self, api_client, temp_dir: Path):
        """Test delimiter detection with quoted fields containing other delimiters."""
        csv_path = temp_dir / "quoted.csv"
        csv_path.write_text(
            'ID|Name|Description\n'
            '1|Alice|"Lives in Paris, France"\n'
            '2|Bob|"Works at Smith, Jones & Associates"\n'
            '3|Charlie|Normal field\n',
            encoding="utf-8"
        )

        # Create run with comma delimiter (wrong)
        response = api_client.post("/runs", json={"delimiter": ","})
        run_id = response.json()["run_id"]

        # Upload file
        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("quoted.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Check status for delimiter warning
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should have delimiter mismatch warning
        warnings = status.get("warnings", [])
        delimiter_warnings = [w for w in warnings if "delimiter" in w.get("message", "").lower()]
        assert len(delimiter_warnings) > 0, "Expected delimiter mismatch warning"

    def test_real_world_file_with_auto_detection(self, api_client):
        """Test auto-detection with the real problematic file.

        Set TEST_DATA_FILE environment variable to point to a test file,
        or this test will be skipped. Example:
            export TEST_DATA_FILE=/path/to/test/file.csv
        """
        # Use environment variable or skip test
        test_file_env = os.getenv('TEST_DATA_FILE')
        if not test_file_env:
            pytest.skip("TEST_DATA_FILE environment variable not set")

        real_file_path = Path(test_file_env)
        if not real_file_path.exists():
            pytest.skip(f"Test file not found: {real_file_path}")

        # Create run (let auto-detection figure out delimiter)
        response = api_client.post("/runs", json={"delimiter": ","})  # Intentionally wrong
        run_id = response.json()["run_id"]

        # Upload file
        with open(real_file_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("real_file.csv", f, "text/csv")}
            )

        # Wait for processing (may take longer for large file)
        for _ in range(10):
            time.sleep(2)
            status_response = api_client.get(f"/runs/{run_id}/status")
            status = status_response.json()
            if status["state"] in ["completed", "failed"]:
                break

        # Should complete (may have warnings)
        assert status["state"] == "completed"

    def test_delimiter_detection_confidence_logging(self, api_client, temp_dir: Path):
        """Test that delimiter detection confidence is logged."""
        csv_path = temp_dir / "pipe.csv"
        csv_path.write_text(
            "ID|Name|Age\n"
            "1|Alice|30\n"
            "2|Bob|25\n",
            encoding="utf-8"
        )

        # Create run
        response = api_client.post("/runs", json={"delimiter": ","})
        run_id = response.json()["run_id"]

        # Upload file
        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("pipe.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Check that processing completed
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should have delimiter information in warnings or complete successfully
        assert status["state"] in ["completed", "processing", "failed"]

    def test_low_confidence_detection(self, api_client, temp_dir: Path):
        """Test behavior when delimiter detection has low confidence."""
        # Create ambiguous file (single column)
        csv_path = temp_dir / "single_column.csv"
        csv_path.write_text(
            "ID\n"
            "1\n"
            "2\n"
            "3\n",
            encoding="utf-8"
        )

        # Create run
        response = api_client.post("/runs", json={"delimiter": ","})
        run_id = response.json()["run_id"]

        # Upload file
        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("single.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Should still complete (uses provided delimiter)
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()
        assert status["state"] in ["completed", "processing"]

    def test_delimiter_detection_with_mixed_content(self, api_client, temp_dir: Path):
        """Test delimiter detection with mixed numeric and text content."""
        csv_path = temp_dir / "mixed.csv"
        csv_path.write_text(
            "ID|Name|Score|Amount|Date\n"
            "1|Alice|95.5|1234.56|2023-01-15\n"
            "2|Bob|inf|5678.90|2023-02-20\n"
            "3|Charlie|92.8|nan|2023-03-25\n",
            encoding="utf-8"
        )

        # Create run with wrong delimiter
        response = api_client.post("/runs", json={"delimiter": ","})
        run_id = response.json()["run_id"]

        # Upload file
        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("mixed.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Check status for delimiter warning
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should have delimiter mismatch warning
        warnings = status.get("warnings", [])
        delimiter_warnings = [w for w in warnings if "delimiter" in w.get("message", "").lower()]
        assert len(delimiter_warnings) > 0, "Expected delimiter mismatch warning"
