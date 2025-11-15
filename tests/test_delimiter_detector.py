"""
Test suite for delimiter auto-detection.

Tests the DelimiterDetector class which automatically identifies
the delimiter used in CSV files.
"""
from api.services.ingest import DelimiterDetector


class TestDelimiterDetector:
    """Test delimiter auto-detection functionality."""

    def test_detect_comma_delimiter(self):
        """Test detection of comma-delimited CSV."""
        content = b"ID,Name,Age\n1,Alice,30\n2,Bob,25\n3,Charlie,35\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        assert delimiter == ","
        assert confidence > 0.7  # High confidence

    def test_detect_pipe_delimiter(self):
        """Test detection of pipe-delimited CSV."""
        content = b"ID|Name|Age\n1|Alice|30\n2|Bob|25\n3|Charlie|35\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        assert delimiter == "|"
        assert confidence > 0.7

    def test_detect_tab_delimiter(self):
        """Test detection of tab-delimited CSV."""
        content = b"ID\tName\tAge\n1\tAlice\t30\n2\tBob\t25\n3\tCharlie\t35\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        assert delimiter == "\t"
        assert confidence > 0.7

    def test_detect_semicolon_delimiter(self):
        """Test detection of semicolon-delimited CSV."""
        content = b"ID;Name;Age\n1;Alice;30\n2;Bob;25\n3;Charlie;35\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        assert delimiter == ";"
        assert confidence > 0.7

    def test_detect_single_column(self):
        """Test detection with single column (no delimiters)."""
        content = b"ID\n1\n2\n3\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should default to comma with low confidence
        assert delimiter == ","
        assert confidence <= 0.7

    def test_detect_mixed_delimiters_in_quotes(self):
        """Test detection with quoted fields containing other delimiters."""
        content = b'ID|Name|Description\n1|Alice|"Uses, commas"\n2|Bob|"Normal field"\n'
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should detect pipe as primary delimiter
        assert delimiter == "|"
        assert confidence > 0.5

    def test_detect_inconsistent_delimiter_counts(self):
        """Test detection with jagged rows (inconsistent delimiter counts)."""
        content = b"ID,Name,Age\n1,Alice,30\n2,Bob\n3,Charlie,35,Extra\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should still detect comma, but with lower confidence
        assert delimiter == ","
        assert 0 < confidence < 1.0

    def test_detect_empty_file(self):
        """Test detection with empty file."""
        content = b""
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should return default delimiter with low confidence
        assert delimiter == ","
        assert confidence <= 0.7

    def test_detect_single_row(self):
        """Test detection with only header row."""
        content = b"ID,Name,Age\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should detect comma but with lower confidence (needs more rows)
        assert delimiter == ","

    def test_detect_with_unicode(self):
        """Test detection with Unicode characters."""
        content = "ID|Name|City\n1|José|São Paulo\n2|François|Montréal\n".encode('utf-8')
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        assert delimiter == "|"
        assert confidence > 0.7

    def test_detect_large_sample(self):
        """Test detection with large file (sample size limit)."""
        # Create large content (> 8KB default sample size)
        lines = [b"ID|Name|Value"]
        for i in range(1000):
            lines.append(f"{i}|Name{i}|Value{i}".encode('utf-8'))
        content = b"\n".join(lines)

        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should detect from sample, not entire file
        assert delimiter == "|"
        assert confidence > 0.7

    def test_detect_with_quoted_delimiters(self):
        """Test detection when delimiter appears in quoted fields."""
        content = b'ID|Name|Email\n1|"Smith, John"|john@example.com\n2|"Doe, Jane"|jane@example.com\n'
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should detect pipe, not comma (which is inside quotes)
        assert delimiter == "|"

    def test_detect_confidence_score_range(self):
        """Test that confidence score is always between 0 and 1."""
        test_cases = [
            b"ID,Name\n1,Alice\n2,Bob\n",  # Good comma
            b"ID|Name\n1|Alice\n2|Bob\n",  # Good pipe
            b"ID\n1\n2\n",  # Single column
            b"",  # Empty
        ]

        detector = DelimiterDetector()
        for content in test_cases:
            _, confidence = detector.detect(content)
            assert 0.0 <= confidence <= 1.0

    def test_detect_with_null_bytes(self):
        """Test detection with null bytes in content."""
        # This should handle gracefully (UTF-8 decode with ignore)
        content = b"ID|Name\n1|Alice\x00\n2|Bob\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should still detect delimiter
        assert delimiter == "|"

    def test_detect_consistency_calculation(self):
        """Test that consistent delimiter counts give high confidence."""
        # Perfect consistency: all rows have same delimiter count
        content = b"ID,Name,Age\n1,Alice,30\n2,Bob,25\n3,Charlie,35\n"
        detector = DelimiterDetector()
        _, confidence = detector.detect(content)

        # Perfect consistency should give high confidence
        assert confidence > 0.9

    def test_detect_with_trailing_delimiter(self):
        """Test detection when rows have trailing delimiters."""
        content = b"ID|Name|Age|\n1|Alice|30|\n2|Bob|25|\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should still detect pipe
        assert delimiter == "|"
        assert confidence > 0.7

    def test_detect_custom_sample_size(self):
        """Test detection with custom sample size."""
        content = b"ID|Name|Value\n" + b"\n".join([f"{i}|Name|Val".encode() for i in range(100)])
        detector = DelimiterDetector(sample_size=100)  # Very small sample
        delimiter, confidence = detector.detect(content)

        # Should still work with small sample
        assert delimiter == "|"

    def test_detect_multiple_candidates(self):
        """Test when multiple delimiters could be valid."""
        # Contains both commas and pipes, but pipes are more consistent
        content = b"ID|Name|Description\n1|Alice|Lives in Paris, France\n2|Bob|Lives in London, UK\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should pick pipe (more consistent)
        assert delimiter == "|"

    def test_detect_csv_sniffer_fallback(self):
        """Test that manual detection works when csv.Sniffer fails."""
        # Edge case content that might confuse Sniffer
        content = b"A|B\n1|2\n"
        detector = DelimiterDetector()
        delimiter, confidence = detector.detect(content)

        # Should fall back to manual detection
        assert delimiter in [",", "|", "\t", ";"]
        assert 0 < confidence <= 1.0
