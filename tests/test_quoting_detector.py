"""
Test suite for quoting auto-detection.

Tests the QuotingDetector class which automatically identifies
whether CSV files use double-quote escaping.
"""
import pytest
from api.services.ingest import QuotingDetector


class TestQuotingDetector:
    """Test quoting auto-detection functionality."""

    def test_detect_unquoted_csv(self):
        """Test detection of unquoted CSV."""
        content = b"ID,Name,Age\n1,Alice,30\n2,Bob,25\n3,Charlie,35\n"
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        assert quoted is False
        assert confidence > 0.7  # High confidence

    def test_detect_quoted_csv_with_embedded_delimiters(self):
        """Test detection of quoted CSV with embedded delimiters."""
        content = b'ID,Name,City\n1,"Smith, John",NYC\n2,"Doe, Jane",LA\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        assert quoted is True
        assert confidence > 0.9  # Very high confidence for embedded delimiters

    def test_detect_quoted_csv_with_escaped_quotes(self):
        """Test detection of quoted CSV with escaped quotes."""
        content = b'ID,Name,Description\n1,John,"He said ""hello"""\n2,Jane,"She said ""goodbye"""\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        assert quoted is True
        assert confidence > 0.7

    def test_detect_simple_quoted_csv(self):
        """Test detection of simple quoted CSV (all fields quoted)."""
        content = b'"ID","Name","Age"\n"1","Alice","30"\n"2","Bob","25"\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        assert quoted is True
        assert confidence > 0.7

    def test_detect_pipe_delimiter_unquoted(self):
        """Test detection with pipe delimiter, unquoted."""
        content = b"ID|Name|Age\n1|Alice|30\n2|Bob|25\n"
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, '|')

        assert quoted is False
        assert confidence > 0.7

    def test_detect_pipe_delimiter_quoted(self):
        """Test detection with pipe delimiter and quoting."""
        content = b'ID|Name|Email\n1|"John Smith"|"john|smith@example.com"\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, '|')

        assert quoted is True
        assert confidence > 0.9  # High confidence due to embedded delimiter

    def test_detect_mixed_quoted_unquoted(self):
        """Test detection with mix of quoted and unquoted fields."""
        content = b'ID,Name,Description\n1,Alice,"Lives in NYC"\n2,Bob,Lives in LA\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        # Should detect as quoted (some fields are quoted)
        assert quoted is True

    def test_detect_single_row_unquoted(self):
        """Test detection with single row, unquoted."""
        content = b"ID,Name,Age\n1,Alice,30\n"
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        assert quoted is False

    def test_detect_single_row_quoted(self):
        """Test detection with single row, quoted."""
        content = b'"ID","Name","Age"\n"1","Alice","30"\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        assert quoted is True

    def test_detect_empty_file(self):
        """Test detection with empty file."""
        content = b""
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        # Should default to quoted with moderate confidence
        assert 0.0 <= confidence <= 1.0

    def test_detect_header_only(self):
        """Test detection with header row only."""
        content = b"ID,Name,Age\n"
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        assert 0.0 <= confidence <= 1.0

    def test_detect_tab_delimiter_quoted(self):
        """Test detection with tab delimiter and quoting."""
        content = b'ID\tName\tCity\n1\t"Smith, John"\tNYC\n2\t"Doe, Jane"\tLA\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, '\t')

        # Comma in quoted field, but tab is delimiter
        assert quoted is True

    def test_detect_confidence_score_range(self):
        """Test that confidence score is always between 0 and 1."""
        test_cases = [
            (b"ID,Name\n1,Alice\n2,Bob\n", ','),
            (b'"ID","Name"\n"1","Alice"\n', ','),
            (b'ID|"Name|With|Pipes"\n', '|'),
            (b"", ','),
        ]

        detector = QuotingDetector()
        for content, delimiter in test_cases:
            _, confidence = detector.detect(content, delimiter)
            assert 0.0 <= confidence <= 1.0

    def test_detect_semicolon_delimiter_quoted(self):
        """Test detection with semicolon delimiter and quoting."""
        content = b'ID;Name;Description\n1;Alice;"Uses, commas"\n2;Bob;"Normal field"\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ';')

        assert quoted is True

    def test_detect_with_unicode(self):
        """Test detection with Unicode characters."""
        content = 'ID,Name,City\n1,"José","São Paulo"\n2,"François","Montréal"\n'.encode('utf-8')
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        assert quoted is True
        assert confidence > 0.7

    def test_detect_no_quotes_at_all(self):
        """Test detection when no quotes are present anywhere."""
        content = b"ID|Name|Age|City|Country\n1|Alice|30|NYC|USA\n2|Bob|25|LA|USA\n"
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, '|')

        assert quoted is False
        assert confidence > 0.9  # Very confident: no quotes anywhere

    def test_detect_custom_sample_size(self):
        """Test detection with custom sample size."""
        content = b'"ID","Name"\n' + b'\n'.join([f'"{i}","Name{i}"'.encode() for i in range(100)])
        detector = QuotingDetector(sample_size=100)  # Very small sample
        quoted, confidence = detector.detect(content, ',')

        # Should still detect quoting from small sample
        assert quoted is True

    def test_detect_large_file(self):
        """Test detection with large file (sample size limit)."""
        # Create large content (> 8KB default sample size)
        lines = [b'"ID","Name","Value"']
        for i in range(1000):
            lines.append(f'"{i}","Name{i}","Value{i}"'.encode('utf-8'))
        content = b"\n".join(lines)

        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        # Should detect from sample, not entire file
        assert quoted is True
        assert confidence > 0.7

    def test_detect_edge_case_single_quote_in_field(self):
        """Test detection when single quote appears in unquoted field."""
        content = b"ID,Name,Description\n1,Alice,It's nice\n2,Bob,He's here\n"
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        # Single quotes (') should not be confused with double quotes (")
        assert quoted is False

    def test_detect_quoted_empty_fields(self):
        """Test detection with quoted empty fields."""
        content = b'ID,Name,Age\n1,"","30"\n2,"Bob",""\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        assert quoted is True

    def test_detect_few_quoted_fields(self):
        """Test detection when very few fields are quoted."""
        # Only 1 field out of many is quoted
        content = b'ID,Name,Age,City,Country\n1,Alice,30,NYC,USA\n2,"Bob Smith",25,LA,USA\n3,Charlie,35,Chicago,USA\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        # Should detect as quoted, but with lower confidence
        assert quoted is False or confidence < 0.8

    def test_detect_embedded_newline_in_quotes(self):
        """Test detection with embedded newlines in quoted fields."""
        content = b'ID,Name,Description\n1,Alice,"Line 1\nLine 2"\n2,Bob,"Single line"\n'
        detector = QuotingDetector()
        quoted, confidence = detector.detect(content, ',')

        # Embedded newline in quotes is strong signal
        assert quoted is True
