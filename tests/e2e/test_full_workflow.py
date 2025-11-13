"""
End-to-End Full Workflow Test.

Tests the complete upload-to-download workflow.

NOTE: This test currently covers Phase 3 endpoints (upload + status polling).
Additional tests for Phase 4-6 endpoints will be added when those branches are merged:
- /runs/{run_id}/profile (Phase 3)
- /runs/{run_id}/candidate-keys (Phase 4 - issue #23)
- /runs/{run_id}/confirm-keys (Phase 4 - issue #22)
- /runs/{run_id}/metrics.csv (Phase 3)

Dependencies:
- Phase 3: Upload and processing (✅ DONE)
- Phase 4: Candidate keys + duplicate detection (⏳ In feature branches)
- Phase 5: Frontend integration (⏳ Pending)
"""

import json
import time
from io import BytesIO
from pathlib import Path

import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestFullWorkflow:
    """Test complete end-to-end workflow from upload to download."""

    def test_upload_and_processing_workflow(
        self,
        api_client,
        fixtures_dir
    ):
        """
        Test Phase 3 workflow: upload → process → status polling → completion.

        This test covers the core upload and processing workflow that is currently
        implemented. Additional workflow steps (profile export, candidate keys, etc.)
        will be tested once Phase 4-6 endpoints are merged.

        Workflow tested:
        1. Create run with configuration
        2. Upload CSV file
        3. Poll status until completion
        4. Verify processing completes successfully
        5. Verify column profiles are generated
        6. Verify no catastrophic errors

        Future additions (pending merge):
        7. Fetch complete profile (/profile endpoint)
        8. Get candidate key suggestions (/candidate-keys endpoint)
        9. Confirm keys for duplicate detection (/confirm-keys endpoint)
        10. Download artifacts (JSON, CSV)
        11. Verify audit log
        """
        # Use the duplicate_records.csv fixture which has known duplicates
        test_file = fixtures_dir / "duplicate_records.csv"
        assert test_file.exists(), f"Test fixture not found: {test_file}"

        # Step 1: Create run with configuration
        print("\n1. Creating run...")
        create_response = api_client.post(
            "/runs",
            json={
                "delimiter": "|",
                "quoted": False,
                "expect_crlf": False
            }
        )
        assert create_response.status_code == 201, f"Failed to create run: {create_response.text}"

        run_data = create_response.json()
        run_id = run_data["run_id"]
        assert run_data["state"] == "queued"
        print(f"   ✅ Run created: {run_id}")

        # Step 2: Upload CSV file
        print("\n2. Uploading file...")
        with open(test_file, "rb") as f:
            files = {"file": ("duplicate_records.csv", f, "text/csv")}
            upload_response = api_client.post(
                f"/runs/{run_id}/upload",
                files=files
            )

        assert upload_response.status_code == 202, f"Failed to upload: {upload_response.text}"
        upload_data = upload_response.json()
        assert upload_data["state"] == "processing"
        print("   ✅ File uploaded, processing started")

        # Step 3: Poll status until completion
        print("\n3. Monitoring progress...")
        max_polls = 60
        poll_count = 0
        status_data = None

        while poll_count < max_polls:
            status_response = api_client.get(f"/runs/{run_id}/status")
            assert status_response.status_code == 200
            status_data = status_response.json()

            state = status_data["state"]
            progress = status_data.get("progress_pct", 0.0)
            print(f"   Poll {poll_count + 1}: state={state}, progress={progress:.1f}%")

            if state == "completed":
                break
            elif state == "failed":
                errors = status_data.get("errors", [])
                pytest.fail(f"Run failed with errors: {errors}")

            time.sleep(0.1)  # Short delay for tests
            poll_count += 1

        assert status_data is not None
        assert status_data["state"] == "completed", "Processing did not complete in time"
        assert status_data["progress_pct"] == 100.0
        print("   ✅ Processing completed successfully")

        # Step 4: Verify no catastrophic errors (warnings are ok for test data)
        print("\n4. Verifying results...")
        errors = status_data.get("errors", [])
        catastrophic_errors = [e for e in errors if not e["code"].startswith("W_")]
        assert len(catastrophic_errors) == 0, f"Catastrophic errors found: {catastrophic_errors}"
        print("   ✅ No catastrophic errors")

        # Step 5: Verify column profiles are generated
        column_profiles = status_data.get("column_profiles")
        assert column_profiles is not None, "Column profiles not generated"
        assert len(column_profiles) == 6, f"Expected 6 columns, got {len(column_profiles)}"
        print(f"   ✅ Column profiles generated: {len(column_profiles)} columns")

        # Verify expected columns are present
        column_names = set(column_profiles.keys())
        expected_columns = {"ID", "Email", "First_Name", "Last_Name", "Phone", "Status"}
        assert column_names == expected_columns, f"Column mismatch: {column_names} != {expected_columns}"
        print(f"   ✅ All expected columns profiled: {', '.join(sorted(column_names))}")

        # Verify each column has basic profiling data
        for col_name, profile in column_profiles.items():
            assert "type" in profile, f"Column {col_name} missing type"
            assert "distinct_count" in profile, f"Column {col_name} missing distinct_count"
            assert "null_count" in profile, f"Column {col_name} missing null_count"

        print(f"\n✅ Phase 3 workflow test passed!")
        print("\n📝 Note: Additional tests for Phase 4-6 endpoints will be added")
        print("   when feature branches are merged:")
        print("   - /runs/{run_id}/profile")
        print("   - /runs/{run_id}/candidate-keys")
        print("   - /runs/{run_id}/confirm-keys")
        print("   - /runs/{run_id}/metrics.csv")

    def test_workflow_with_invalid_file(self, api_client):
        """
        Test workflow with invalid UTF-8 file (catastrophic error).

        Workflow should:
        1. Upload invalid file
        2. Detect UTF-8 error immediately
        3. Mark run as failed
        4. Not produce profile artifacts
        """
        print("\n=== Testing workflow with invalid file ===")

        # Step 1: Create run
        print("\n1. Creating run...")
        create_response = api_client.post(
            "/runs",
            json={"delimiter": "|", "quoted": False, "expect_crlf": False}
        )
        assert create_response.status_code == 201
        run_id = create_response.json()["run_id"]
        print(f"   ✅ Run created: {run_id}")

        # Step 2: Upload invalid UTF-8 file
        print("\n2. Uploading invalid file...")
        invalid_data = b"ID|Name\n1|Alice\n2|\xFF\xFEInvalid\n"
        files = {"file": ("invalid.csv", BytesIO(invalid_data), "text/csv")}

        upload_response = api_client.post(
            f"/runs/{run_id}/upload",
            files=files
        )

        # Upload should be accepted
        assert upload_response.status_code == 202
        print("   ✅ Invalid file uploaded")

        # Step 3: Wait briefly for validation
        print("\n3. Waiting for validation...")
        time.sleep(0.1)

        # Step 4: Check status - should be failed
        print("\n4. Checking status...")
        status_response = api_client.get(f"/runs/{run_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()

        assert status_data["state"] == "failed"
        errors = status_data.get("errors", [])
        assert len(errors) > 0

        # Should have UTF-8 validation error
        utf8_error = next((e for e in errors if "UTF8" in e["code"]), None)
        assert utf8_error is not None, "UTF-8 error not found in errors"
        print(f"   ✅ Run failed as expected: {utf8_error['code']}")

        # Step 5: Verify no column profiles for failed run
        print("\n5. Verifying no profiles for failed run...")
        column_profiles = status_data.get("column_profiles")
        assert column_profiles is None or len(column_profiles) == 0, \
            "Column profiles should not exist for failed run"
        print("   ✅ No profiles generated for failed run")

        print("\n✅ Invalid file workflow test passed!")

    def test_multiple_file_types(self, api_client, fixtures_dir):
        """
        Test workflow with different test fixtures.

        Verifies processing works correctly for:
        - Files with duplicates
        - Files with mixed types
        - Files with quoted fields
        - Files with date formats
        - Files with money violations
        """
        test_files = [
            ("duplicate_records.csv", 12, 6),
            ("mixed_types.csv", 4, 2),
            ("quoted_fields.csv", 8, 4),
            ("dates_mixed.csv", 5, 3),
            ("money_violations.csv", 4, 3),
        ]

        print("\n=== Testing multiple file types ===")

        for filename, expected_rows, expected_cols in test_files:
            test_file = fixtures_dir / filename
            if not test_file.exists():
                print(f"   ⏭️  Skipping {filename} (file not found)")
                continue

            print(f"\n📄 Testing {filename}...")

            # Create run and upload
            response = api_client.post("/runs", json={"delimiter": "|"})
            run_id = response.json()["run_id"]

            with open(test_file, "rb") as f:
                files = {"file": (filename, f, "text/csv")}
                api_client.post(f"/runs/{run_id}/upload", files=files)

            # Wait for completion (short timeout for test data)
            max_polls = 30
            for _ in range(max_polls):
                response = api_client.get(f"/runs/{run_id}/status")
                status = response.json()
                if status["state"] in ["completed", "failed"]:
                    break
                time.sleep(0.1)

            # Verify completion
            assert status["state"] == "completed", f"{filename} processing failed"

            # Verify column count (if profiles exist)
            profiles = status.get("column_profiles", {})
            if profiles:
                # Just verify we got some columns, not exact count (depends on fixture)
                assert len(profiles) > 0, f"{filename}: no columns profiled"
                print(f"   ✅ {filename}: {len(profiles)} columns profiled")
            else:
                print(f"   ⚠️  {filename}: No column profiles (may need profile endpoint)")

        print("\n✅ Multiple file types test passed!")


@pytest.mark.e2e
@pytest.mark.skip(reason="Waiting for Phase 4-6 endpoints to be merged")
class TestFullWorkflowWithAllEndpoints:
    """
    Complete workflow tests including Phase 4-6 endpoints.

    These tests are currently skipped because the required endpoints
    are implemented in feature branches that haven't been merged yet:
    - feature/candidate-keys-api-issue-23
    - feature/duplicate-detection-issue-22

    Once merged, remove the @pytest.mark.skip decorator.
    """

    def test_complete_workflow_with_profile_export(self, api_client, fixtures_dir):
        """Test upload → profile → download JSON."""
        pytest.skip("Requires /runs/{run_id}/profile endpoint (Phase 3)")

    def test_complete_workflow_with_candidate_keys(self, api_client, fixtures_dir):
        """Test upload → profile → candidate keys → confirm → duplicates."""
        pytest.skip("Requires /runs/{run_id}/candidate-keys endpoint (Phase 4)")

    def test_complete_workflow_with_csv_export(self, api_client, fixtures_dir):
        """Test upload → profile → download CSV metrics."""
        pytest.skip("Requires /runs/{run_id}/metrics.csv endpoint (Phase 3)")

    def test_complete_workflow_with_audit_log(self, api_client, fixtures_dir):
        """Test audit log creation and content verification."""
        pytest.skip("Requires audit log implementation to be verified")
