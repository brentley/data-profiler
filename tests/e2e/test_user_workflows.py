"""
End-to-End User Workflow Tests.

Tests complete user workflows from UI interaction to artifact download:
- Upload file via web form
- Monitor progress with polling
- View results dashboard
- Interact with candidate keys
- Download artifacts
- Handle errors gracefully
"""

import pytest
import time
from pathlib import Path


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteUserWorkflow:
    """Test complete end-to-end user workflows."""

    def test_happy_path_upload_to_download(self, api_client, sample_csv_simple, temp_workspace):
        """
        Complete happy path: upload → process → view → download.

        User story:
        1. User uploads CSV file
        2. User monitors progress
        3. User views results
        4. User downloads artifacts
        """
        # Step 1: Create run
        response = api_client.post('/runs', json={
            'delimiter': '|',
            'quoted': True,
            'expect_crlf': False
        })

        assert response.status_code == 201
        run_id = response.json()['run_id']

        # Step 2: Upload file
        files = {'file': ('test.csv', sample_csv_simple, 'text/csv')}
        response = api_client.post(f'/runs/{run_id}/upload', files=files)

        assert response.status_code == 202

        # Step 3: Poll for completion
        max_polls = 60
        poll_count = 0

        while poll_count < max_polls:
            response = api_client.get(f'/runs/{run_id}/status')
            status = response.json()

            if status['state'] == 'completed':
                break
            elif status['state'] == 'failed':
                pytest.fail(f"Run failed: {status.get('errors')}")

            time.sleep(1)
            poll_count += 1

        assert status['state'] == 'completed', "Processing did not complete"
        assert status['progress_pct'] == 100.0

        # Step 4: Get profile
        response = api_client.get(f'/runs/{run_id}/profile')
        assert response.status_code == 200

        profile = response.json()
        assert profile['run_id'] == run_id
        assert profile['file']['rows'] == 5
        assert profile['file']['columns'] == 5

        # Step 5: Download artifacts
        # JSON
        response = api_client.get(f'/runs/{run_id}/profile')
        assert response.status_code == 200
        assert 'application/json' in response.headers['Content-Type']

        # CSV
        response = api_client.get(f'/runs/{run_id}/metrics.csv')
        assert response.status_code == 200
        assert 'text/csv' in response.headers['Content-Type']

        # HTML
        response = api_client.get(f'/runs/{run_id}/report.html')
        assert response.status_code == 200
        assert 'text/html' in response.headers['Content-Type']

    def test_candidate_key_workflow(self, api_client, sample_csv_simple):
        """
        Candidate key suggestion and confirmation workflow.

        User story:
        1. User uploads file
        2. System suggests candidate keys
        3. User confirms selection
        4. System runs duplicate check
        5. User views duplicate results
        """
        # Create and upload
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        files = {'file': ('test.csv', sample_csv_simple, 'text/csv')}
        api_client.post(f'/runs/{run_id}/upload', files=files)

        # Wait for completion
        self._wait_for_completion(api_client, run_id)

        # Get candidate key suggestions
        response = api_client.get(f'/runs/{run_id}/candidate-keys')
        assert response.status_code == 200

        suggestions = response.json()['suggestions']
        assert len(suggestions) > 0

        # 'id' should be top suggestion
        top_suggestion = suggestions[0]
        assert 'id' in top_suggestion['columns']

        # Confirm selection
        response = api_client.post(f'/runs/{run_id}/confirm-keys', json={
            'keys': [top_suggestion['columns']]
        })
        assert response.status_code == 202

        # Wait for duplicate check
        time.sleep(2)

        # Get updated profile with duplicate info
        response = api_client.get(f'/runs/{run_id}/profile')
        profile = response.json()

        id_col = next(c for c in profile['columns'] if c['name'] == 'id')
        assert 'duplicate_count' in id_col
        assert id_col['duplicate_count'] == 0  # No duplicates in sample

    def test_error_handling_workflow(self, api_client, sample_csv_money_violations):
        """
        Error handling workflow - non-catastrophic errors.

        User story:
        1. User uploads file with errors
        2. Processing continues with warnings
        3. User views error roll-up
        4. User drills down into specific errors
        """
        # Create and upload file with violations
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        files = {'file': ('violations.csv', sample_csv_money_violations, 'text/csv')}
        api_client.post(f'/runs/{run_id}/upload', files=files)

        # Wait for completion
        self._wait_for_completion(api_client, run_id)

        # Get status with errors
        response = api_client.get(f'/runs/{run_id}/status')
        status = response.json()

        assert status['state'] == 'completed'  # Should complete despite errors
        assert len(status['warnings']) > 0 or len(status['errors']) > 0

        # Get profile with error details
        response = api_client.get(f'/runs/{run_id}/profile')
        profile = response.json()

        # Check error roll-up
        assert 'errors' in profile
        money_errors = [e for e in profile['errors'] if e['code'] == 'E_MONEY_FORMAT']
        assert len(money_errors) > 0

        # Check per-column error counts
        bad_col = next(c for c in profile['columns'] if 'bad' in c['name'])
        assert 'violations_count' in bad_col.get('money_rules', {})

    def test_catastrophic_error_workflow(self, api_client, sample_invalid_utf8):
        """
        Catastrophic error handling workflow.

        User story:
        1. User uploads invalid file
        2. Processing stops immediately
        3. User sees clear error message
        4. No partial results available
        """
        # Create and upload invalid file
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        files = {'file': ('invalid.bin', sample_invalid_utf8, 'application/octet-stream')}
        api_client.post(f'/runs/{run_id}/upload', files=files)

        # Wait briefly
        time.sleep(2)

        # Check status
        response = api_client.get(f'/runs/{run_id}/status')
        status = response.json()

        assert status['state'] == 'failed'
        assert len(status['errors']) > 0

        # Verify catastrophic error present
        assert any(e['code'] == 'E_UTF8_INVALID' for e in status['errors'])

        # Profile should not be available
        response = api_client.get(f'/runs/{run_id}/profile')
        assert response.status_code == 404 or response.status_code == 409

    def test_compressed_file_workflow(self, api_client, sample_csv_simple):
        """
        Compressed file upload workflow.

        User story:
        1. User uploads .csv.gz file
        2. System auto-detects compression
        3. Decompresses and processes
        4. Results identical to uncompressed
        """
        import gzip

        # Create and upload compressed
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id_compressed = response.json()['run_id']

        compressed_data = gzip.compress(sample_csv_simple.encode('utf-8'))
        files = {'file': ('test.csv.gz', compressed_data, 'application/gzip')}
        api_client.post(f'/runs/{run_id_compressed}/upload', files=files)

        self._wait_for_completion(api_client, run_id_compressed)

        # Get compressed results
        response = api_client.get(f'/runs/{run_id_compressed}/profile')
        profile_compressed = response.json()

        # Create and upload uncompressed
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id_uncompressed = response.json()['run_id']

        files = {'file': ('test.csv', sample_csv_simple, 'text/csv')}
        api_client.post(f'/runs/{run_id_uncompressed}/upload', files=files)

        self._wait_for_completion(api_client, run_id_uncompressed)

        # Get uncompressed results
        response = api_client.get(f'/runs/{run_id_uncompressed}/profile')
        profile_uncompressed = response.json()

        # Results should be identical
        assert profile_compressed['file']['rows'] == profile_uncompressed['file']['rows']
        assert profile_compressed['file']['columns'] == profile_uncompressed['file']['columns']

    @pytest.mark.slow
    def test_long_running_process_workflow(self, api_client, sample_large_csv):
        """
        Long-running process with progress updates.

        User story:
        1. User uploads large file
        2. User sees progress updates
        3. Processing completes successfully
        4. Results are complete
        """
        # Upload large file
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        with open(sample_large_csv, 'rb') as f:
            files = {'file': ('large.csv', f, 'text/csv')}
            api_client.post(f'/runs/{run_id}/upload', files=files)

        # Monitor progress
        progress_values = []
        max_polls = 120

        for _ in range(max_polls):
            response = api_client.get(f'/runs/{run_id}/status')
            status = response.json()

            progress_values.append(status['progress_pct'])

            if status['state'] == 'completed':
                break
            elif status['state'] == 'failed':
                pytest.fail("Processing failed")

            time.sleep(1)

        # Verify progress increased
        assert len(progress_values) > 1
        assert progress_values[-1] == 100.0
        assert progress_values[0] < progress_values[-1]

        # Verify completeness
        response = api_client.get(f'/runs/{run_id}/profile')
        profile = response.json()

        assert profile['file']['rows'] == 100000  # Expected row count

    def _wait_for_completion(self, api_client, run_id: str, timeout: int = 60):
        """Helper to wait for run completion."""
        start = time.time()

        while time.time() - start < timeout:
            response = api_client.get(f'/runs/{run_id}/status')
            status = response.json()

            if status['state'] in ['completed', 'failed']:
                return status

            time.sleep(1)

        pytest.fail(f"Timeout waiting for run {run_id}")


@pytest.mark.e2e
class TestMultiRunManagement:
    """Test management of multiple concurrent runs."""

    def test_multiple_concurrent_runs(self, api_client, sample_csv_simple):
        """
        Multiple runs should process concurrently without interference.

        User story:
        1. User starts multiple runs
        2. All process independently
        3. Results are correct for each
        """
        run_ids = []

        # Start 5 concurrent runs
        for i in range(5):
            response = api_client.post('/runs', json={'delimiter': '|'})
            run_id = response.json()['run_id']
            run_ids.append(run_id)

            files = {'file': (f'test{i}.csv', sample_csv_simple, 'text/csv')}
            api_client.post(f'/runs/{run_id}/upload', files=files)

        # Wait for all to complete
        for run_id in run_ids:
            max_polls = 30
            for _ in range(max_polls):
                response = api_client.get(f'/runs/{run_id}/status')
                if response.json()['state'] == 'completed':
                    break
                time.sleep(1)

        # Verify all completed successfully
        for run_id in run_ids:
            response = api_client.get(f'/runs/{run_id}/profile')
            assert response.status_code == 200

            profile = response.json()
            assert profile['file']['rows'] == 5

    def test_run_isolation(self, api_client, sample_csv_simple):
        """
        Runs should be isolated - errors in one don't affect others.

        User story:
        1. User starts run A (valid)
        2. User starts run B (invalid)
        3. Run A completes successfully
        4. Run B fails independently
        """
        # Start valid run
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id_valid = response.json()['run_id']

        files = {'file': ('valid.csv', sample_csv_simple, 'text/csv')}
        api_client.post(f'/runs/{run_id_valid}/upload', files=files)

        # Start invalid run
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id_invalid = response.json()['run_id']

        invalid_data = b"id|name\n1\xFFInvalid\n"
        files = {'file': ('invalid.bin', invalid_data, 'application/octet-stream')}
        api_client.post(f'/runs/{run_id_invalid}/upload', files=files)

        # Wait for both
        time.sleep(3)

        # Valid run should succeed
        response = api_client.get(f'/runs/{run_id_valid}/status')
        assert response.json()['state'] == 'completed'

        # Invalid run should fail
        response = api_client.get(f'/runs/{run_id_invalid}/status')
        assert response.json()['state'] == 'failed'


@pytest.mark.e2e
class TestUIInteractions:
    """Test UI-specific interactions and behaviors."""

    def test_toast_notifications(self, api_client, sample_csv_money_violations):
        """
        Toast notifications for errors and warnings.

        UI should show:
        - Success toast on completion
        - Warning toast for non-catastrophic errors
        - Error toast for catastrophic errors
        """
        # This would be tested with Selenium/Playwright in real E2E
        # Here we verify the API provides the necessary data

        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        files = {'file': ('violations.csv', sample_csv_money_violations, 'text/csv')}
        api_client.post(f'/runs/{run_id}/upload', files=files)

        time.sleep(3)

        response = api_client.get(f'/runs/{run_id}/status')
        status = response.json()

        # Should have warnings for UI to display
        assert len(status.get('warnings', [])) > 0 or len(status.get('errors', [])) > 0

    def test_error_rollup_display(self, api_client, sample_csv_money_violations):
        """
        Error roll-up table for user review.

        UI should show:
        - Error code
        - Error count
        - Sample message
        """
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        files = {'file': ('violations.csv', sample_csv_money_violations, 'text/csv')}
        api_client.post(f'/runs/{run_id}/upload', files=files)

        time.sleep(3)

        response = api_client.get(f'/runs/{run_id}/profile')
        profile = response.json()

        # Error roll-up should be present
        assert 'errors' in profile
        errors = profile['errors']

        # Each error should have code, message, count
        for error in errors:
            assert 'code' in error
            assert 'message' in error
            assert 'count' in error

    def test_per_column_drill_down(self, api_client, sample_csv_simple):
        """
        Per-column detail view.

        UI should show:
        - Column name
        - Inferred type
        - Stats
        - Top values
        - Distributions
        """
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        files = {'file': ('test.csv', sample_csv_simple, 'text/csv')}
        api_client.post(f'/runs/{run_id}/upload', files=files)

        time.sleep(3)

        response = api_client.get(f'/runs/{run_id}/profile')
        profile = response.json()

        # Each column should have complete profile
        for column in profile['columns']:
            assert 'name' in column
            assert 'inferred_type' in column
            assert 'null_pct' in column
            assert 'distinct_count' in column

            # Type-specific stats
            if column['inferred_type'] in ['numeric', 'money']:
                assert 'numeric_stats' in column
            elif column['inferred_type'] == 'date':
                assert 'date_stats' in column


@pytest.mark.e2e
class TestDownloadWorkflows:
    """Test artifact download workflows."""

    def test_json_download_completeness(self, api_client, sample_csv_simple):
        """JSON profile should be complete and valid."""
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        files = {'file': ('test.csv', sample_csv_simple, 'text/csv')}
        api_client.post(f'/runs/{run_id}/upload', files=files)

        time.sleep(3)

        response = api_client.get(f'/runs/{run_id}/profile')
        profile = response.json()

        # Verify JSON structure
        assert 'run_id' in profile
        assert 'file' in profile
        assert 'columns' in profile
        assert 'errors' in profile
        assert 'warnings' in profile
        assert 'candidate_keys' in profile

    def test_csv_metrics_download(self, api_client, sample_csv_simple):
        """CSV metrics file should be valid and complete."""
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        files = {'file': ('test.csv', sample_csv_simple, 'text/csv')}
        api_client.post(f'/runs/{run_id}/upload', files=files)

        time.sleep(3)

        response = api_client.get(f'/runs/{run_id}/metrics.csv')
        csv_content = response.text

        # Verify CSV structure
        lines = csv_content.strip().split('\n')
        assert len(lines) > 1  # Header + data

        # Header should have expected columns
        header = lines[0]
        assert 'column_name' in header
        assert 'type' in header
        assert 'null_pct' in header

    def test_html_report_rendering(self, api_client, sample_csv_simple):
        """HTML report should render correctly."""
        response = api_client.post('/runs', json={'delimiter': '|'})
        run_id = response.json()['run_id']

        files = {'file': ('test.csv', sample_csv_simple, 'text/csv')}
        api_client.post(f'/runs/{run_id}/upload', files=files)

        time.sleep(3)

        response = api_client.get(f'/runs/{run_id}/report.html')
        html_content = response.text

        # Verify HTML structure
        assert '<html' in html_content.lower()
        assert '</html>' in html_content.lower()
        assert 'profile' in html_content.lower() or 'report' in html_content.lower()
