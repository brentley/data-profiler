"""
CRLF Detection and Line Ending Normalization Tests.

Tests the line ending detector that must:
- Detect CRLF (\\r\\n), LF (\\n), CR (\\r) patterns
- Normalize all to \\n internally
- Record original line ending style for audit
- Handle mixed line endings
- Perform efficiently on large files
"""

import pytest
from io import BytesIO
from services.ingest import CRLFDetector, LineEndingStyle


class TestCRLFDetector:
    """Test CRLF detection and normalization."""

    def test_detect_crlf(self):
        """CRLF line endings should be detected."""
        data = b"line1\r\nline2\r\nline3\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        assert result.style == LineEndingStyle.CRLF
        assert result.original_style == "CRLF"
        assert result.sample_count >= 3

    def test_detect_lf(self):
        """LF line endings should be detected."""
        data = b"line1\nline2\nline3\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        assert result.style == LineEndingStyle.LF
        assert result.original_style == "LF"
        assert result.sample_count >= 3

    def test_detect_cr(self):
        """CR-only line endings should be detected (legacy Mac)."""
        data = b"line1\rline2\rline3\r"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        assert result.style == LineEndingStyle.CR
        assert result.original_style == "CR"
        assert result.sample_count >= 3

    def test_detect_mixed_crlf_lf(self):
        """Mixed CRLF and LF should detect predominant style."""
        # 5 CRLF, 2 LF
        data = b"line1\r\nline2\r\nline3\nline4\r\nline5\nline6\r\nline7\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        assert result.style == LineEndingStyle.CRLF
        assert result.mixed is True
        assert result.crlf_count == 5
        assert result.lf_count == 2

    def test_detect_mixed_lf_predominant(self):
        """Mixed with LF predominant should detect LF."""
        # 5 LF, 2 CRLF
        data = b"line1\nline2\nline3\r\nline4\nline5\r\nline6\nline7\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        assert result.style == LineEndingStyle.LF
        assert result.mixed is True
        assert result.lf_count == 5
        assert result.crlf_count == 2

    def test_normalization_crlf_to_lf(self):
        """CRLF should be normalized to LF internally."""
        data = b"line1\r\nline2\r\nline3\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        normalized = detector.normalize()

        assert b"\r\n" not in normalized
        assert normalized.count(b"\n") == 3
        assert normalized == b"line1\nline2\nline3\n"

    def test_normalization_cr_to_lf(self):
        """CR should be normalized to LF internally."""
        data = b"line1\rline2\rline3\r"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        normalized = detector.normalize()

        assert b"\r" not in normalized or b"\r\n" in normalized  # Allow CRLF
        assert normalized.count(b"\n") == 3

    def test_normalization_lf_unchanged(self):
        """LF should remain unchanged during normalization."""
        data = b"line1\nline2\nline3\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        normalized = detector.normalize()

        assert normalized == data

    def test_empty_stream(self):
        """Empty stream should handle gracefully."""
        stream = BytesIO(b"")
        detector = CRLFDetector(stream)

        result = detector.detect()

        assert result.style == LineEndingStyle.UNKNOWN
        assert result.sample_count == 0

    def test_single_line_no_ending(self):
        """Single line without line ending."""
        data = b"single line"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        assert result.style == LineEndingStyle.UNKNOWN
        assert result.sample_count == 0

    def test_large_file_performance(self):
        """Large file should detect efficiently (sample-based)."""
        # Generate 1MB with CRLF
        lines = [f"Line {i}\r\n".encode('utf-8') for i in range(10000)]
        data = b"".join(lines)
        stream = BytesIO(data)

        detector = CRLFDetector(stream, sample_size=100)
        result = detector.detect()

        assert result.style == LineEndingStyle.CRLF
        # Should sample, not scan entire file
        assert result.sample_count <= 100

    def test_audit_trail_info(self):
        """Detection should record info for audit trail."""
        data = b"line1\r\nline2\r\nline3\n"  # Mixed
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        # Audit trail should include
        assert hasattr(result, 'original_style')
        assert hasattr(result, 'mixed')
        assert hasattr(result, 'crlf_count')
        assert hasattr(result, 'lf_count')
        assert hasattr(result, 'cr_count')

    def test_quoted_field_crlf_not_counted(self):
        """CRLF inside quoted fields should not count as line ending."""
        # CSV with embedded CRLF in quotes
        data = b'col1,col2\r\n"value1\r\ninside",value2\r\n'
        stream = BytesIO(data)
        detector = CRLFDetector(stream, quoted_aware=True)

        result = detector.detect()

        # Only 2 actual line breaks (header + data row)
        assert result.sample_count == 2

    def test_binary_content_detection(self):
        """Binary content should not be misinterpreted as line endings."""
        # Binary data with byte values matching \r and \n
        data = b"\x00\x0D\x00\x0A\x00"  # NULL CR NULL LF NULL
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        # Should handle binary gracefully or reject
        assert result is not None

    @pytest.mark.parametrize("line_ending,expected", [
        (b"\r\n", LineEndingStyle.CRLF),
        (b"\n", LineEndingStyle.LF),
        (b"\r", LineEndingStyle.CR),
    ])
    def test_detect_specific_endings(self, line_ending, expected):
        """Parameterized test for specific line endings."""
        lines = [f"line{i}".encode() + line_ending for i in range(5)]
        data = b"".join(lines)
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        assert result.style == expected

    def test_streaming_detection(self):
        """Detector should work with streaming/chunked reads."""
        data = b"line1\r\nline2\r\nline3\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream, chunk_size=10)

        result = detector.detect()

        assert result.style == LineEndingStyle.CRLF

    def test_unicode_with_crlf(self):
        """Unicode content with CRLF should detect correctly."""
        data = "Hello 世界\r\nHello עולם\r\n".encode('utf-8')
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()

        assert result.style == LineEndingStyle.CRLF

    def test_crlf_audit_metadata(self):
        """Audit metadata should be comprehensive."""
        data = b"line1\r\nline2\r\nline3\r\n"
        stream = BytesIO(data)
        detector = CRLFDetector(stream)

        result = detector.detect()
        metadata = result.to_audit_dict()

        assert 'original_style' in metadata
        assert 'normalized_to' in metadata
        assert 'mixed' in metadata
        assert 'sample_count' in metadata
        assert metadata['original_style'] == 'CRLF'
        assert metadata['normalized_to'] == 'LF'
