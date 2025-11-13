"""
Full Pipeline Integration Tests.

Tests the complete data profiling pipeline:
Upload → UTF-8 Validation → CRLF Detection → CSV Parsing → Type Inference →
Profiling → Statistics → Candidate Keys → Artifacts Generation

This validates the end-to-end flow and integration between components.
"""

import pytest
import json
from pathlib import Path
from uuid import uuid4
import gzip


@pytest.mark.integration
class TestFullPipelineIntegration:
    """Test complete pipeline from upload to artifacts."""

    def test_simple_pipeline_success(self, temp_workspace, sample_csv_simple):
        """Complete pipeline with simple valid CSV."""
        # Setup
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"
        input_file.write_text(sample_csv_simple)

        # Execute pipeline
        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={
                'delimiter': '|',
                'quoted': True,
                'expect_crlf': False
            }
        )

        result = pipeline.execute()

        # Verify result
        assert result.success is True
        assert result.run_id == run_id
        assert result.state == 'completed'

        # Verify profile generated
        profile = result.profile
        assert profile is not None
        assert profile['file']['rows'] == 5
        assert profile['file']['columns'] == 5
        assert len(profile['columns']) == 5

        # Verify column profiling
        id_col = next(c for c in profile['columns'] if c['name'] == 'id')
        assert id_col['inferred_type'] == 'numeric'
        assert id_col['distinct_count'] == 5

        amount_col = next(c for c in profile['columns'] if c['name'] == 'amount')
        assert amount_col['inferred_type'] == 'money'
        assert amount_col['money_rules']['two_decimal_ok'] is True

        # Verify artifacts
        output_dir = temp_workspace / "outputs" / run_id
        assert output_dir.exists()
        assert (output_dir / "profile.json").exists()
        assert (output_dir / "metrics.csv").exists()
        assert (output_dir / "report.html").exists()

    def test_pipeline_with_errors_continues(self, temp_workspace, sample_csv_money_violations):
        """Pipeline should continue with non-catastrophic errors."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"
        input_file.write_text(sample_csv_money_violations)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Should complete despite errors
        assert result.success is True
        assert result.state == 'completed'

        # Should have recorded errors
        assert len(result.errors) > 0
        assert any(e['code'] == 'E_MONEY_FORMAT' for e in result.errors)

        # Profile should still be generated
        assert result.profile is not None

    def test_pipeline_catastrophic_error_stops(self, temp_workspace, sample_invalid_utf8):
        """Pipeline should stop on catastrophic errors."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.bin"
        input_file.write_bytes(sample_invalid_utf8)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Should fail with catastrophic error
        assert result.success is False
        assert result.state == 'failed'

        # Should have catastrophic error
        assert any(e['code'] == 'E_UTF8_INVALID' for e in result.errors)

        # No profile should be generated
        assert result.profile is None

    def test_pipeline_with_gzip_compression(self, temp_workspace, sample_csv_simple):
        """Pipeline should handle .gz compressed files."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv.gz"

        # Compress sample
        with gzip.open(input_file, 'wb') as f:
            f.write(sample_csv_simple.encode('utf-8'))

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Should decompress and process
        assert result.success is True
        assert result.profile['file']['rows'] == 5

    def test_pipeline_progress_tracking(self, temp_workspace, sample_large_csv):
        """Pipeline should track progress during execution."""
        run_id = str(uuid4())

        from services.pipeline import ProfilePipeline

        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress)

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=sample_large_csv,
            workspace=temp_workspace,
            config={'delimiter': '|'},
            progress_callback=progress_callback
        )

        result = pipeline.execute()

        # Should have progress updates
        assert len(progress_updates) > 0
        assert progress_updates[0] < progress_updates[-1]
        assert progress_updates[-1] == 100.0

    def test_pipeline_with_nulls(self, temp_workspace, sample_csv_with_nulls):
        """Pipeline should handle null values correctly."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"
        input_file.write_text(sample_csv_with_nulls)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Should handle nulls
        assert result.success is True

        # Check null percentages
        name_col = next(c for c in result.profile['columns'] if c['name'] == 'name')
        assert name_col['null_pct'] > 0

    @pytest.mark.slow
    def test_pipeline_large_file_performance(self, temp_workspace, sample_large_csv, time_profiler):
        """Large file should process within acceptable time."""
        run_id = str(uuid4())

        from services.pipeline import ProfilePipeline

        def run_pipeline():
            pipeline = ProfilePipeline(
                run_id=run_id,
                input_path=sample_large_csv,
                workspace=temp_workspace,
                config={'delimiter': '|'}
            )
            return pipeline.execute()

        result_data = time_profiler(run_pipeline)

        # Should complete
        assert result_data['result'].success is True

        # Performance check: 100k rows should process in < 30 seconds
        assert result_data['elapsed_seconds'] < 30.0

    def test_pipeline_candidate_keys_flow(self, temp_workspace, sample_csv_simple):
        """Pipeline should generate candidate key suggestions."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"
        input_file.write_text(sample_csv_simple)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Should have candidate keys
        assert 'candidate_keys' in result.profile
        assert len(result.profile['candidate_keys']) > 0

        # 'id' should be top candidate
        top_candidate = result.profile['candidate_keys'][0]
        assert 'id' in top_candidate['columns']
        assert top_candidate['distinct_ratio'] == 1.0

    def test_pipeline_artifacts_completeness(self, temp_workspace, sample_csv_simple):
        """All artifacts should be generated completely."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"
        input_file.write_text(sample_csv_simple)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        output_dir = temp_workspace / "outputs" / run_id

        # Check JSON profile
        json_path = output_dir / "profile.json"
        assert json_path.exists()
        with open(json_path) as f:
            profile = json.load(f)
            assert 'run_id' in profile
            assert 'file' in profile
            assert 'columns' in profile

        # Check CSV metrics
        csv_path = output_dir / "metrics.csv"
        assert csv_path.exists()
        with open(csv_path) as f:
            lines = f.readlines()
            assert len(lines) > 1  # Header + data

        # Check HTML report
        html_path = output_dir / "report.html"
        assert html_path.exists()
        with open(html_path) as f:
            html = f.read()
            assert '<html' in html.lower()
            assert 'profile' in html.lower()

        # Check audit log
        audit_path = output_dir / "audit.log.json"
        assert audit_path.exists()
        with open(audit_path) as f:
            audit = json.load(f)
            assert 'run_id' in audit
            assert 'timestamp' in audit


@pytest.mark.integration
class TestPipelineErrorScenarios:
    """Test pipeline behavior with various error scenarios."""

    def test_jagged_row_stops_immediately(self, temp_workspace):
        """Jagged row should stop pipeline immediately."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"

        # Create file with jagged row
        content = "id|name|amount\n1|Alice|100\n2|Bob\n3|Charlie|300\n"
        input_file.write_text(content)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Should fail catastrophically
        assert result.success is False
        assert any(e['code'] == 'E_JAGGED_ROW' for e in result.errors)

        # Should note line number
        error = next(e for e in result.errors if e['code'] == 'E_JAGGED_ROW')
        assert 'line' in error['message'].lower()

    def test_multiple_non_catastrophic_errors(self, temp_workspace):
        """Multiple non-catastrophic errors should accumulate."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"

        # CSV with multiple violations
        content = """id|amount1|amount2|amount3
1|100.50|$100.50|1,000.50
2|200.75|$200.75|2,000.75
3|300.99|$300.99|3,000.99"""
        input_file.write_text(content)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Should complete
        assert result.success is True

        # Should have multiple errors
        assert len(result.errors) > 0

        # Check error rollup
        error_rollup = {e['code']: e['count'] for e in result.errors}
        assert 'E_MONEY_FORMAT' in error_rollup
        assert error_rollup['E_MONEY_FORMAT'] >= 6  # 3 rows * 2 bad columns

    def test_empty_file_handling(self, temp_workspace):
        """Empty file should be handled gracefully."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"
        input_file.write_text("")

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Should fail (no header)
        assert result.success is False
        assert any(e['code'] == 'E_HEADER_MISSING' for e in result.errors)


@pytest.mark.integration
class TestPipelineResourceManagement:
    """Test resource management and cleanup."""

    def test_temp_files_cleaned_on_success(self, temp_workspace, sample_csv_simple):
        """Temporary files should be cleaned up after successful run."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"
        input_file.write_text(sample_csv_simple)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Temp work directory should be cleaned
        work_dir = temp_workspace / "work" / "runs" / run_id
        assert not work_dir.exists() or len(list(work_dir.glob("*.tmp"))) == 0

    def test_temp_files_preserved_on_failure(self, temp_workspace, sample_invalid_utf8):
        """Temporary files should be preserved on failure for debugging."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.bin"
        input_file.write_bytes(sample_invalid_utf8)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'},
            preserve_on_failure=True
        )

        result = pipeline.execute()

        # Work directory should exist for debugging
        work_dir = temp_workspace / "work" / "runs" / run_id
        assert work_dir.exists()

    @pytest.mark.slow
    def test_memory_not_leaked(self, temp_workspace, sample_large_csv, memory_profiler):
        """Memory should be released after pipeline execution."""
        run_id = str(uuid4())

        from services.pipeline import ProfilePipeline

        def run_multiple_pipelines():
            for i in range(5):
                pipeline = ProfilePipeline(
                    run_id=f"{run_id}_{i}",
                    input_path=sample_large_csv,
                    workspace=temp_workspace,
                    config={'delimiter': '|'}
                )
                pipeline.execute()

        result = memory_profiler(run_multiple_pipelines)

        # Peak memory should not grow excessively
        # 5 runs should not use 5x memory (indicating leaks)
        assert result['peak_memory_mb'] < 500  # Reasonable limit

    def test_sqlite_connections_closed(self, temp_workspace, sample_csv_simple):
        """SQLite connections should be properly closed."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"
        input_file.write_text(sample_csv_simple)

        from services.pipeline import ProfilePipeline

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Should be able to delete database file (no locks)
        db_path = temp_workspace / "work" / "runs" / run_id / f"{run_id}.db"
        if db_path.exists():
            db_path.unlink()  # Should not raise error


@pytest.mark.integration
class TestPipelineStateTransitions:
    """Test pipeline state machine and transitions."""

    def test_state_progression_success(self, temp_workspace, sample_csv_simple):
        """State should progress through: queued → processing → completed."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.csv"
        input_file.write_text(sample_csv_simple)

        from services.pipeline import ProfilePipeline

        states_observed = []

        def state_callback(state):
            states_observed.append(state)

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'},
            state_callback=state_callback
        )

        result = pipeline.execute()

        # Should have progressed through states
        assert 'queued' in states_observed or states_observed[0] == 'processing'
        assert 'processing' in states_observed
        assert states_observed[-1] == 'completed'

    def test_state_transition_on_failure(self, temp_workspace, sample_invalid_utf8):
        """State should transition to failed on catastrophic error."""
        run_id = str(uuid4())
        input_file = temp_workspace / "uploads" / f"{run_id}.bin"
        input_file.write_bytes(sample_invalid_utf8)

        from services.pipeline import ProfilePipeline

        states_observed = []

        def state_callback(state):
            states_observed.append(state)

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=input_file,
            workspace=temp_workspace,
            config={'delimiter': '|'},
            state_callback=state_callback
        )

        result = pipeline.execute()

        # Should end in failed state
        assert states_observed[-1] == 'failed'
