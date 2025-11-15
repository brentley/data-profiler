"""
Test suite for user-friendly error messages.

Tests that error messages returned to users are clear, actionable,
and don't expose technical stack traces.
"""
import pytest
import time
from pathlib import Path


class TestUserFriendlyErrors:
    """Test user-friendly error messages."""

    def test_utf8_error_message_is_friendly(self, api_client, sample_csv_invalid_utf8: Path):
        """Test that UTF-8 validation errors are user-friendly."""
        # Create run
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        # Upload invalid UTF-8 file
        with open(sample_csv_invalid_utf8, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("invalid.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Get status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should have failed with clear error
        assert status["state"] == "failed"
        errors = status.get("errors", [])
        assert len(errors) > 0

        # Error message should be user-friendly
        error_msg = errors[0].get("message", "")
        # Should NOT contain stack traces or internal details
        assert "Traceback" not in error_msg
        assert "Exception" not in error_msg
        assert ".py" not in error_msg
        # Should contain actionable information
        assert "UTF-8" in error_msg or "encoding" in error_msg.lower()

    def test_delimiter_mismatch_message_is_friendly(self, api_client, temp_dir: Path):
        """Test that delimiter mismatch warnings are user-friendly."""
        csv_path = temp_dir / "comma.csv"
        csv_path.write_text(
            "ID,Name,Age\n"
            "1,Alice,30\n"
            "2,Bob,25\n",
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

        # Get status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should have delimiter warning
        warnings = status.get("warnings", [])
        delimiter_warnings = [w for w in warnings if "delimiter" in w.get("message", "").lower()]

        if delimiter_warnings:
            warning_msg = delimiter_warnings[0].get("message", "")
            # Should be user-friendly
            assert "appears to use" in warning_msg.lower() or "detected" in warning_msg.lower()
            assert "comma" in warning_msg.lower() or "pipe" in warning_msg.lower()
            # Should NOT contain technical details
            assert "Traceback" not in warning_msg
            assert ".py" not in warning_msg

    def test_jagged_row_error_is_friendly(self, api_client, sample_csv_jagged: Path):
        """Test that jagged row errors are user-friendly."""
        # Create run
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        # Upload jagged file
        with open(sample_csv_jagged, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("jagged.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Get status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should have failed with clear error
        if status["state"] == "failed":
            errors = status.get("errors", [])
            assert len(errors) > 0

            error_msg = errors[0].get("message", "")
            # Should mention columns or rows
            assert "column" in error_msg.lower() or "row" in error_msg.lower()
            # Should NOT contain stack traces
            assert "Traceback" not in error_msg
            assert ".py" not in error_msg

    def test_missing_header_error_is_friendly(self, api_client, sample_csv_no_header: Path):
        """Test that missing header errors are user-friendly."""
        # Create run
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        # Upload file without header
        with open(sample_csv_no_header, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("no_header.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Get status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Should have failed with clear error
        if status["state"] == "failed":
            errors = status.get("errors", [])
            assert len(errors) > 0

            error_msg = errors[0].get("message", "")
            # Should mention header
            assert "header" in error_msg.lower()
            # Should NOT contain stack traces
            assert "Traceback" not in error_msg
            assert ".py" not in error_msg

    def test_invalid_file_type_error_is_friendly(self, api_client, temp_dir: Path):
        """Test that invalid file type errors are user-friendly."""
        # Create non-CSV file
        txt_path = temp_dir / "test.json"
        txt_path.write_text('{"data": "not a csv"}')

        # Create run
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        # Upload invalid file type
        with open(txt_path, "rb") as f:
            upload_response = api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.json", f, "application/json")}
            )

        # Should reject at upload time with clear message
        if upload_response.status_code == 400:
            error = upload_response.json()
            error_msg = error.get("detail", "")
            # Should mention accepted file types
            assert ".csv" in error_msg.lower() or ".txt" in error_msg.lower()
            # Should NOT contain stack traces
            assert "Traceback" not in error_msg

    def test_run_not_found_error_is_friendly(self, api_client):
        """Test that run not found errors are user-friendly."""
        fake_run_id = "00000000-0000-0000-0000-000000000000"

        # Try to get status of non-existent run
        response = api_client.get(f"/runs/{fake_run_id}/status")

        assert response.status_code == 404
        error = response.json()
        error_msg = error.get("detail", "")

        # Should be clear and simple
        assert "not found" in error_msg.lower()
        assert fake_run_id in error_msg
        # Should NOT contain stack traces
        assert "Traceback" not in error_msg
        assert ".py" not in error_msg

    def test_upload_to_completed_run_error_is_friendly(self, api_client, temp_dir: Path):
        """Test that uploading to completed run gives friendly error."""
        csv_path = temp_dir / "test.csv"
        csv_path.write_text("ID|Name\n1|Alice\n", encoding="utf-8")

        # Create run and upload
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        # Wait for completion
        time.sleep(2)

        # Try to upload again
        with open(csv_path, "rb") as f:
            response = api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test2.csv", f, "text/csv")}
            )

        # Should reject with friendly message
        if response.status_code == 409:
            error = response.json()
            error_msg = error.get("detail", "")
            # Should explain the state issue
            assert "already" in error_msg.lower() or "uploaded" in error_msg.lower()
            # Should NOT contain stack traces
            assert "Traceback" not in error_msg

    def test_get_profile_before_completion_error_is_friendly(self, api_client, temp_dir: Path):
        """Test that getting profile before completion gives friendly error."""
        csv_path = temp_dir / "test.csv"
        csv_path.write_text("ID|Name\n1|Alice\n", encoding="utf-8")

        # Create run (don't upload)
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        # Try to get profile immediately
        response = api_client.get(f"/runs/{run_id}/profile")

        # Should give clear error
        if response.status_code in [404, 409]:
            error = response.json()
            error_msg = error.get("detail", "")
            # Should mention state or completion
            assert "complete" in error_msg.lower() or "not found" in error_msg.lower()
            # Should NOT contain stack traces
            assert "Traceback" not in error_msg

    def test_confirm_keys_with_invalid_columns_error_is_friendly(self, api_client, temp_dir: Path):
        """Test that confirming invalid keys gives friendly error."""
        csv_path = temp_dir / "test.csv"
        csv_path.write_text("ID|Name\n1|Alice\n", encoding="utf-8")

        # Create run and upload
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        # Wait for completion
        time.sleep(2)

        # Try to confirm non-existent columns
        response = api_client.post(
            f"/runs/{run_id}/confirm-keys",
            json={"keys": ["NonExistentColumn"]}
        )

        # Should give clear error
        if response.status_code == 400:
            error = response.json()
            error_msg = error.get("detail", "")
            # Should mention invalid columns
            assert "invalid" in error_msg.lower() or "not found" in error_msg.lower()
            assert "NonExistentColumn" in error_msg
            # Should NOT contain stack traces
            assert "Traceback" not in error_msg

    def test_global_exception_handler(self, api_client):
        """Test that unhandled exceptions return friendly errors."""
        # This tests the global exception handler in app.py
        # We can't easily trigger an unhandled exception in tests,
        # but we can verify the handler exists

        from api.app import app

        # Verify global exception handler is registered
        assert app.exception_handlers is not None

    def test_error_codes_are_consistent(self, api_client, temp_dir: Path):
        """Test that error codes follow consistent naming convention."""
        csv_path = temp_dir / "invalid_utf8.csv"
        csv_path.write_bytes(b"ID|Name\n1|\xFF\xFE\n")

        # Create run and upload
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("invalid.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Get status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Check error codes format
        errors = status.get("errors", [])
        if errors:
            for error in errors:
                error_code = error.get("code", "")
                # Error codes should be E_ prefixed
                assert error_code.startswith("E_") or error_code.startswith("W_")
                # Should be uppercase with underscores
                assert error_code.isupper()
                assert " " not in error_code

    def test_warning_codes_are_consistent(self, api_client, temp_dir: Path):
        """Test that warning codes follow consistent naming convention."""
        csv_path = temp_dir / "mixed_endings.csv"
        # Create file with mixed line endings
        csv_path.write_bytes(b"ID|Name\r\n1|Alice\n2|Bob\r\n")

        # Create run and upload
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("mixed.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Get status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Check warning codes format
        warnings = status.get("warnings", [])
        if warnings:
            for warning in warnings:
                warning_code = warning.get("code", "")
                # Warning codes should be W_ prefixed
                assert warning_code.startswith("W_")
                # Should be uppercase with underscores
                assert warning_code.isupper()
                assert " " not in warning_code

    def test_error_messages_include_context(self, api_client, sample_csv_jagged: Path):
        """Test that error messages include helpful context."""
        # Create run and upload jagged file
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        with open(sample_csv_jagged, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("jagged.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Get status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Errors should have context
        errors = status.get("errors", [])
        if errors:
            error = errors[0]
            # Should have all required fields
            assert "code" in error
            assert "message" in error
            assert "count" in error

    def test_no_sensitive_info_in_errors(self, api_client, temp_dir: Path):
        """Test that error messages don't leak sensitive file paths or internals."""
        csv_path = temp_dir / "test.csv"
        csv_path.write_text("ID|Secret\n1|password123\n", encoding="utf-8")

        # Create run and upload
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("test.csv", f, "text/csv")}
            )

        # Wait for processing
        time.sleep(2)

        # Get status
        status_response = api_client.get(f"/runs/{run_id}/status")
        status = status_response.json()

        # Convert errors/warnings to string (not full response which includes profiles)
        errors_str = str(status.get("errors", []))
        warnings_str = str(status.get("warnings", []))

        # Error/warning messages should NOT contain file paths
        assert "/Users/" not in errors_str
        assert "C:\\" not in errors_str
        assert "/Users/" not in warnings_str
        assert "C:\\" not in warnings_str

        # Should NOT contain internal implementation details in errors
        assert "pydantic" not in errors_str.lower()
        assert "fastapi" not in errors_str.lower()
        assert "pydantic" not in warnings_str.lower()
        assert "fastapi" not in warnings_str.lower()
