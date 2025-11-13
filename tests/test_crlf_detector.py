"""
Test suite for CRLF detection and normalization.

RED PHASE: These tests define expected CRLF handling behavior.

Requirements from spec:
- CRLF line endings preferred; accept LF
- Record actual line ending style found
- Normalize internally for processing
- Embedded CRLF in quoted fields must be preserved
"""
import pytest
from pathlib import Path


class TestCRLFDetector:
    """Test CRLF detection and normalization."""

    def test_detect_crlf_line_endings(self, sample_csv_crlf: Path):
        """Test detection of CRLF (\\r\\n) line endings."""
        from api.services.validators import CRLFDetector

        detector = CRLFDetector()
        result = detector.analyze_file(sample_csv_crlf)

        assert result.line_ending_type == "CRLF"
        assert result.crlf_count > 0
        assert result.lf_only_count == 0
        assert result.is_consistent is True

    def test_detect_lf_line_endings(self, sample_csv_basic: Path):
        """Test detection of LF (\\n) line endings."""
        from api.services.validators import CRLFDetector

        detector = CRLFDetector()
        result = detector.analyze_file(sample_csv_basic)

        assert result.line_ending_type == "LF"
        assert result.lf_only_count > 0
        assert result.crlf_count == 0
        assert result.is_consistent is True

    def test_detect_mixed_line_endings(self, temp_dir: Path):
        """Test detection of mixed CRLF and LF line endings."""
        from api.services.validators import CRLFDetector

        mixed_csv = temp_dir / "mixed.csv"
        mixed_csv.write_bytes(
            b"ID|Name\r\n"
            b"1|Alice\n"
            b"2|Bob\r\n"
        )

        detector = CRLFDetector()
        result = detector.analyze_file(mixed_csv)

        assert result.line_ending_type == "MIXED"
        assert result.crlf_count == 2
        assert result.lf_only_count == 1
        assert result.is_consistent is False

    def test_normalization_crlf_to_lf(self, temp_dir: Path):
        """Test internal normalization of CRLF to LF."""
        from api.services.validators import CRLFNormalizer

        crlf_csv = temp_dir / "crlf.csv"
        crlf_csv.write_bytes(
            b"ID|Name\r\n"
            b"1|Alice\r\n"
            b"2|Bob\r\n"
        )

        normalizer = CRLFNormalizer()
        normalized_lines = list(normalizer.normalize_file(crlf_csv))

        # All lines should end with \n only
        for line in normalized_lines:
            assert not line.endswith("\r\n")
            if line:  # Skip empty lines
                assert line.endswith("\n") or line == normalized_lines[-1]

    def test_preserve_embedded_crlf_in_quoted_fields(self, temp_dir: Path):
        """Test that CRLF embedded in quoted fields is preserved."""
        from api.services.validators import CRLFNormalizer

        quoted_csv = temp_dir / "embedded_crlf.csv"
        quoted_csv.write_bytes(
            b'ID|Description\r\n'
            b'1|"Line1\r\nLine2"\r\n'
            b'2|Normal\r\n'
        )

        normalizer = CRLFNormalizer()
        normalized_lines = list(normalizer.normalize_file(quoted_csv))

        # The embedded CRLF in quoted field should remain
        assert any("\r\n" in line for line in normalized_lines if '"' in line)

    def test_detect_cr_only_line_endings(self, temp_dir: Path):
        """Test detection of old Mac CR-only line endings."""
        from api.services.validators import CRLFDetector

        cr_csv = temp_dir / "cr_only.csv"
        cr_csv.write_bytes(
            b"ID|Name\r"
            b"1|Alice\r"
            b"2|Bob\r"
        )

        detector = CRLFDetector()
        result = detector.analyze_file(cr_csv)

        assert result.line_ending_type == "CR"
        assert result.cr_only_count > 0

    def test_report_line_ending_statistics(self, temp_dir: Path):
        """Test that detector provides detailed statistics."""
        from api.services.validators import CRLFDetector

        mixed_csv = temp_dir / "stats.csv"
        mixed_csv.write_bytes(
            b"ID|Name\r\n"  # CRLF
            b"1|Alice\n"    # LF
            b"2|Bob\r\n"    # CRLF
            b"3|Charlie\n"  # LF
        )

        detector = CRLFDetector()
        result = detector.analyze_file(mixed_csv)

        assert result.total_lines == 4
        assert result.crlf_count == 2
        assert result.lf_only_count == 2
        assert result.crlf_percentage == 50.0
        assert result.lf_percentage == 50.0

    def test_warning_for_inconsistent_line_endings(self, temp_dir: Path):
        """Test that mixed line endings generate a warning."""
        from api.services.validators import CRLFDetector

        mixed_csv = temp_dir / "mixed_warn.csv"
        mixed_csv.write_bytes(
            b"ID|Name\r\n"
            b"1|Alice\n"
            b"2|Bob\r\n"
        )

        detector = CRLFDetector()
        result = detector.analyze_file(mixed_csv)

        assert result.warning is not None
        assert "mixed" in result.warning.lower() or "inconsistent" in result.warning.lower()

    def test_no_warning_for_consistent_crlf(self, sample_csv_crlf: Path):
        """Test that consistent CRLF does not generate warnings."""
        from api.services.validators import CRLFDetector

        detector = CRLFDetector()
        result = detector.analyze_file(sample_csv_crlf)

        assert result.warning is None
        assert result.is_consistent is True

    def test_no_warning_for_consistent_lf(self, sample_csv_basic: Path):
        """Test that consistent LF does not generate warnings."""
        from api.services.validators import CRLFDetector

        detector = CRLFDetector()
        result = detector.analyze_file(sample_csv_basic)

        assert result.warning is None
        assert result.is_consistent is True

    def test_gzip_file_line_ending_detection(self, temp_dir: Path):
        """Test line ending detection in gzipped files."""
        import gzip
        from api.services.validators import CRLFDetector

        gz_path = temp_dir / "test.csv.gz"
        with gzip.open(gz_path, "wb") as f:
            f.write(b"ID|Name\r\n1|Alice\r\n2|Bob\r\n")

        detector = CRLFDetector()
        result = detector.analyze_file(gz_path)

        assert result.line_ending_type == "CRLF"
        assert result.crlf_count > 0

    def test_empty_file_line_endings(self, temp_dir: Path):
        """Test handling of empty file."""
        from api.services.validators import CRLFDetector

        empty_csv = temp_dir / "empty.csv"
        empty_csv.write_bytes(b"")

        detector = CRLFDetector()
        result = detector.analyze_file(empty_csv)

        assert result.line_ending_type == "NONE"
        assert result.total_lines == 0

    def test_single_line_no_terminator(self, temp_dir: Path):
        """Test file with single line and no line terminator."""
        from api.services.validators import CRLFDetector

        single_csv = temp_dir / "single.csv"
        single_csv.write_bytes(b"ID|Name")

        detector = CRLFDetector()
        result = detector.analyze_file(single_csv)

        assert result.line_ending_type == "NONE"
        assert result.total_lines == 1
