"""
Test suite for artifact generation.

RED PHASE: These tests define expected artifact generation behavior.

Requirements from spec:
- profile.json - Full profile with all metrics
- metrics.csv - Per-column metrics in CSV format
- report.html - Human-readable HTML report
- audit.log.json - PII-aware audit trail
"""
import pytest
from pathlib import Path
import json


class TestArtifactGeneration:
    """Test artifact generation functionality."""

    def test_generate_profile_json(self, sample_csv_basic: Path, temp_dir: Path):
        """Test generation of profile.json artifact."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir)
        profile_path = generator.generate_profile_json(
            csv_path=sample_csv_basic,
            run_id="test-run-123",
            delimiter="|"
        )

        assert profile_path.exists()
        assert profile_path.suffix == ".json"

        # Validate JSON structure
        with open(profile_path) as f:
            data = json.load(f)
            assert "run_id" in data
            assert "file" in data
            assert "columns" in data

    def test_profile_json_completeness(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that profile.json contains all required fields."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir)
        profile_path = generator.generate_profile_json(
            csv_path=sample_csv_basic,
            run_id="test-run-123",
            delimiter="|"
        )

        with open(profile_path) as f:
            data = json.load(f)

            # File metadata
            assert data["file"]["rows"] > 0
            assert data["file"]["columns"] > 0
            assert "delimiter" in data["file"]
            assert "header" in data["file"]

            # Column profiles
            for col in data["columns"]:
                assert "name" in col
                assert "inferred_type" in col
                assert "null_pct" in col
                assert "distinct_count" in col

    def test_generate_metrics_csv(self, sample_csv_basic: Path, temp_dir: Path):
        """Test generation of metrics.csv artifact."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir)
        metrics_path = generator.generate_metrics_csv(
            csv_path=sample_csv_basic,
            run_id="test-run-123",
            delimiter="|"
        )

        assert metrics_path.exists()
        assert metrics_path.suffix == ".csv"

        # Validate CSV structure
        content = metrics_path.read_text()
        lines = content.split("\n")
        assert len(lines) > 1  # Header + data rows
        assert "column" in lines[0].lower()
        assert "type" in lines[0].lower()

    def test_metrics_csv_format(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that metrics.csv follows expected format."""
        from api.services.artifacts import ArtifactGenerator
        import csv

        generator = ArtifactGenerator(output_dir=temp_dir)
        metrics_path = generator.generate_metrics_csv(
            csv_path=sample_csv_basic,
            run_id="test-run-123",
            delimiter="|"
        )

        with open(metrics_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) > 0
            first_row = rows[0]

            # Expected columns
            assert "column" in first_row
            assert "type" in first_row
            assert "null_pct" in first_row
            assert "distinct_count" in first_row

    def test_generate_html_report(self, sample_csv_basic: Path, temp_dir: Path):
        """Test generation of report.html artifact."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir)
        report_path = generator.generate_html_report(
            csv_path=sample_csv_basic,
            run_id="test-run-123",
            delimiter="|"
        )

        assert report_path.exists()
        assert report_path.suffix == ".html"

        # Validate HTML structure
        content = report_path.read_text()
        assert "<html" in content.lower()
        assert "<body" in content.lower()
        assert "</html>" in content.lower()

    def test_html_report_content(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that HTML report contains expected content."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir)
        report_path = generator.generate_html_report(
            csv_path=sample_csv_basic,
            run_id="test-run-123",
            delimiter="|"
        )

        content = report_path.read_text()

        # Should contain summary information
        assert "rows" in content.lower() or "records" in content.lower()
        assert "columns" in content.lower() or "fields" in content.lower()

        # Should contain column information
        assert "type" in content.lower()
        assert "distinct" in content.lower()

    def test_generate_audit_log(self, sample_csv_basic: Path, temp_dir: Path):
        """Test generation of audit.log.json artifact."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir)
        audit_path = generator.generate_audit_log(
            csv_path=sample_csv_basic,
            run_id="test-run-123",
            delimiter="|"
        )

        assert audit_path.exists()
        assert audit_path.name == "audit.log.json"

        # Validate JSON structure
        with open(audit_path) as f:
            data = json.load(f)
            assert "run_id" in data
            assert "timestamp" in data
            assert "file_sha256" in data

    def test_audit_log_pii_redaction(self, temp_dir: Path):
        """Test that audit log redacts PII appropriately."""
        from api.services.artifacts import ArtifactGenerator

        # Create CSV with PII-like data
        csv_path = temp_dir / "pii.csv"
        csv_path.write_text(
            "ID|Name|SSN\n"
            "1|John Doe|123-45-6789\n"
            "2|Jane Smith|987-65-4321\n",
            encoding="utf-8"
        )

        generator = ArtifactGenerator(output_dir=temp_dir)
        audit_path = generator.generate_audit_log(
            csv_path=csv_path,
            run_id="test-run-123",
            delimiter="|"
        )

        content = audit_path.read_text()

        # Should not contain actual values
        assert "123-45-6789" not in content
        assert "John Doe" not in content

        # Should contain counts and metadata
        assert "rows" in content.lower() or "count" in content.lower()

    def test_audit_log_sha256_hash(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that audit log includes SHA-256 hash of input file."""
        from api.services.artifacts import ArtifactGenerator
        import hashlib

        # Calculate expected hash
        with open(sample_csv_basic, "rb") as f:
            expected_hash = hashlib.sha256(f.read()).hexdigest()

        generator = ArtifactGenerator(output_dir=temp_dir)
        audit_path = generator.generate_audit_log(
            csv_path=sample_csv_basic,
            run_id="test-run-123",
            delimiter="|"
        )

        with open(audit_path) as f:
            data = json.load(f)
            assert data["file_sha256"] == expected_hash

    def test_artifact_file_naming(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that artifacts follow naming conventions."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir)
        run_id = "test-run-123"

        profile_path = generator.generate_profile_json(
            sample_csv_basic, run_id, delimiter="|"
        )
        metrics_path = generator.generate_metrics_csv(
            sample_csv_basic, run_id, delimiter="|"
        )
        report_path = generator.generate_html_report(
            sample_csv_basic, run_id, delimiter="|"
        )

        # Check naming
        assert "profile.json" in profile_path.name or run_id in profile_path.name
        assert "metrics.csv" in metrics_path.name or run_id in metrics_path.name
        assert "report.html" in report_path.name or run_id in report_path.name

    def test_artifact_directory_structure(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that artifacts are organized in correct directory structure."""
        from api.services.artifacts import ArtifactGenerator

        output_dir = temp_dir / "outputs"
        generator = ArtifactGenerator(output_dir=output_dir)
        run_id = "test-run-123"

        generator.generate_all_artifacts(
            csv_path=sample_csv_basic,
            run_id=run_id,
            delimiter="|"
        )

        # Should create run-specific directory
        run_dir = output_dir / run_id
        assert run_dir.exists()
        assert run_dir.is_dir()

        # Should contain all artifacts
        assert (run_dir / "profile.json").exists()
        assert (run_dir / "metrics.csv").exists()
        assert (run_dir / "report.html").exists()
        assert (run_dir / "audit.log.json").exists()

    def test_regenerate_artifacts_overwrites(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that regenerating artifacts overwrites existing ones."""
        from api.services.artifacts import ArtifactGenerator
        import time

        generator = ArtifactGenerator(output_dir=temp_dir)
        run_id = "test-run-123"

        # Generate first time
        profile_path1 = generator.generate_profile_json(
            sample_csv_basic, run_id, delimiter="|"
        )
        mtime1 = profile_path1.stat().st_mtime

        time.sleep(0.1)

        # Generate again
        profile_path2 = generator.generate_profile_json(
            sample_csv_basic, run_id, delimiter="|"
        )
        mtime2 = profile_path2.stat().st_mtime

        assert profile_path1 == profile_path2
        assert mtime2 > mtime1  # File was modified

    def test_html_report_styling(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that HTML report includes proper styling."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir)
        report_path = generator.generate_html_report(
            sample_csv_basic, "test-run-123", delimiter="|"
        )

        content = report_path.read_text()

        # Should have CSS styling
        assert "<style" in content.lower() or "stylesheet" in content.lower()

        # Should be responsive
        assert "viewport" in content.lower() or "responsive" in content.lower()

    def test_html_report_dark_mode(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that HTML report supports dark mode."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir, dark_mode=True)
        report_path = generator.generate_html_report(
            sample_csv_basic, "test-run-123", delimiter="|"
        )

        content = report_path.read_text()

        # Should have dark mode styling
        assert "dark" in content.lower() or "prefers-color-scheme" in content.lower()

    def test_artifact_generation_with_errors(self, sample_csv_money_violations: Path, temp_dir: Path):
        """Test that artifacts include error information."""
        from api.services.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(output_dir=temp_dir)
        profile_path = generator.generate_profile_json(
            sample_csv_money_violations, "test-run-123", delimiter="|"
        )

        with open(profile_path) as f:
            data = json.load(f)

            # Should contain errors
            assert "errors" in data
            assert len(data["errors"]) > 0

    def test_csv_metrics_includes_all_columns(self, sample_csv_basic: Path, temp_dir: Path):
        """Test that metrics.csv includes all columns from source."""
        from api.services.artifacts import ArtifactGenerator
        import csv

        generator = ArtifactGenerator(output_dir=temp_dir)
        metrics_path = generator.generate_metrics_csv(
            sample_csv_basic, "test-run-123", delimiter="|"
        )

        # Get column names from source
        with open(sample_csv_basic) as f:
            source_reader = csv.reader(f, delimiter="|")
            source_columns = next(source_reader)

        # Check metrics CSV
        with open(metrics_path) as f:
            metrics_reader = csv.DictReader(f)
            metrics_columns = [row["column"] for row in metrics_reader]

        assert set(source_columns) == set(metrics_columns)

    def test_artifact_generation_performance(self, temp_dir: Path):
        """Test that artifact generation completes in reasonable time."""
        import time
        from api.services.artifacts import ArtifactGenerator

        # Create large file
        large_csv = temp_dir / "large.csv"
        with large_csv.open("w", encoding="utf-8") as f:
            f.write("ID|Name|Value\n")
            for i in range(10000):
                f.write(f"{i}|Name{i}|Value{i}\n")

        generator = ArtifactGenerator(output_dir=temp_dir)

        start_time = time.time()
        generator.generate_all_artifacts(
            csv_path=large_csv,
            run_id="test-run-123",
            delimiter="|"
        )
        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (< 5 seconds)
        assert elapsed_time < 5.0
