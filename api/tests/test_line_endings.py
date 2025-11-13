"""
Line ending detection and normalization tests.

Tests the CRLF detector that must:
- Detect CRLF (\\r\\n), LF (\\n), and CR (\\r) line endings
- Record the original line ending style
- Normalize all line endings to LF internally
- Handle mixed line endings
"""

import pytest
from io import BytesIO
from services.ingest import CRLFDetector


class TestLineEndingDetector:
    """Test line ending detection and normalization."""

    def test_detect_crlf(self):
        """Should detect CRLF line endings."""
        data = b"line1\r\nline2\r\nline3\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        assert result.detected_style == "CRLF"
        assert result.crlf_count > 0
        assert result.lf_only_count == 0
        assert result.cr_only_count == 0

    def test_detect_lf(self):
        """Should detect LF line endings."""
        data = b"line1\nline2\nline3\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        assert result.detected_style == "LF"
        assert result.lf_only_count > 0
        assert result.crlf_count == 0
        assert result.cr_only_count == 0

    def test_detect_cr(self):
        """Should detect CR line endings (old Mac style)."""
        data = b"line1\rline2\rline3\r"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        assert result.detected_style == "CR"
        assert result.cr_only_count > 0
        assert result.crlf_count == 0

    def test_mixed_line_endings_crlf_dominant(self):
        """Should detect dominant style when mixed."""
        # Mostly CRLF with one LF
        data = b"line1\r\nline2\r\nline3\nline4\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        assert result.detected_style == "CRLF"
        assert result.has_mixed is True
        assert result.crlf_count == 3
        assert result.lf_only_count == 1

    def test_mixed_line_endings_lf_dominant(self):
        """Should detect dominant style when mixed."""
        # Mostly LF with one CRLF
        data = b"line1\nline2\nline3\r\nline4\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        assert result.detected_style == "LF"
        assert result.has_mixed is True

    def test_normalize_crlf_to_lf(self):
        """Should normalize CRLF to LF internally."""
        data = b"line1\r\nline2\r\nline3\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        normalized = detector.normalize()
        assert b"\r\n" not in normalized
        assert b"line1\nline2\nline3\n" == normalized

    def test_normalize_preserves_lf(self):
        """Should preserve LF line endings."""
        data = b"line1\nline2\nline3\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        normalized = detector.normalize()
        assert normalized == data

    def test_normalize_cr_to_lf(self):
        """Should normalize CR to LF internally."""
        data = b"line1\rline2\rline3\r"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        normalized = detector.normalize()
        assert b"\r" not in normalized
        assert b"line1\nline2\nline3\n" == normalized

    def test_empty_file(self):
        """Should handle empty files."""
        stream = BytesIO(b"")
        detector = CRLFDetector(stream)

        result = detector.detect()
        assert result.detected_style == "NONE"

    def test_no_line_endings(self):
        """Should handle files with no line endings."""
        data = b"single line with no ending"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        assert result.detected_style == "NONE"

    def test_streaming_detection(self):
        """Should work with streaming/chunked data."""
        # Large file with CRLF
        data = b"line\r\n" * 10000
        stream = BytesIO(data)
        detector = CRLFDetector(stream, chunk_size=1024)

        result = detector.detect()
        assert result.detected_style == "CRLF"
        assert result.crlf_count == 10000

    def test_metadata_preserved(self):
        """Should preserve metadata about original file."""
        data = b"line1\r\nline2\nline3\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        # Original stats preserved
        assert result.original_style == "CRLF"
        assert result.has_mixed is True
        assert result.total_lines == 3

    def test_embedded_crlf_in_quoted_field(self):
        """Should not count CRLF inside quoted CSV fields."""
        # This will be handled by CSV parser, but detector should see all
        data = b'field1,"field\r\nwith\r\nlines",field3\r\n'
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        # Detector sees all line endings (parser will handle quoting)
        assert result.crlf_count >= 1

    def test_report_warning_on_mixed(self):
        """Should generate warning for mixed line endings."""
        data = b"line1\r\nline2\nline3\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        assert result.has_mixed is True
        assert len(result.warnings) > 0
        assert "mixed" in result.warnings[0].lower()
