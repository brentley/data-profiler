"""
Integration tests for full data profiler pipeline.

Tests the complete pipeline: UTF-8 → CRLF → CSV → Type → Profile
Covers all error scenarios, golden files, and large datasets.
"""

import pytest
import tempfile
from pathlib import Path
from io import BytesIO, StringIO
from typing import List

from services.ingest import (
    UTF8Validator,
    CRLFDetector,
    CSVParser,
    ParserConfig,
    ParserError,
    ValidationResult,
    LineEndingResult,
    LineEndingStyle
)
from services.types import TypeInferrer, TypeInferenceResult
from services.profile import (
    NumericProfiler,
    StringProfiler,
    MoneyValidator,
    DateValidator,
    MoneyProfiler,
    DateProfiler,
    CodeProfiler
)


@pytest.mark.integration
class TestFullPipelineValidData:
    """Test full pipeline with valid data."""

    def test_simple_pipe_delimited_full_pipeline(self, temp_workspace):
        """Test complete pipeline with simple pipe-delimited data."""
        # Arrange: Create test data
        csv_content = b"""id|name|amount|date|status
1|Alice|100.50|20230101|active
2|Bob|250.75|20230102|inactive
3|Charlie|99.99|20230103|active
4|Diana|1000.00|20230104|pending
5|Eve|50.25|20230105|active"""

        # Stage 1: UTF-8 Validation
        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        validation_result = utf8_validator.validate()

        assert validation_result.is_valid
        assert not validation_result.has_bom

        # Stage 2: CRLF Detection and Normalization
        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        line_ending_result = crlf_detector.detect()

        assert line_ending_result.style == LineEndingStyle.LF
        normalized_content = crlf_detector.normalize()

        # Stage 3: CSV Parsing
        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)

        header_result = csv_parser.parse_header()
        assert header_result.success
        assert header_result.headers == ['id', 'name', 'amount', 'date', 'status']
        assert header_result.column_count == 5

        rows = list(csv_parser.parse_rows())
        assert len(rows) == 5
        assert rows[0] == ['1', 'Alice', '100.50', '20230101', 'active']

        # Stage 4: Type Inference
        # Write to temp file for type inference
        temp_file = temp_workspace / "test_data.csv"
        temp_file.write_text(normalized_content.decode('utf-8'))

        type_inferrer = TypeInferrer()
        type_result = type_inferrer.infer_column_types(temp_file, delimiter='|')

        assert 'id' in type_result.columns
        assert 'name' in type_result.columns
        assert 'amount' in type_result.columns
        assert 'date' in type_result.columns
        assert 'status' in type_result.columns

        assert type_result.columns['id'].inferred_type == 'numeric'
        assert type_result.columns['name'].inferred_type in ['alpha', 'varchar']
        assert type_result.columns['amount'].inferred_type == 'money'
        assert type_result.columns['date'].inferred_type == 'date'
        assert type_result.columns['status'].inferred_type in ['code', 'alpha']

        # Stage 5: Statistical Profiling
        # Profile amount column (money)
        money_profiler = MoneyProfiler()
        for row in rows:
            money_profiler.update(row[2])  # amount column
        money_stats = money_profiler.finalize()

        assert money_stats.valid_count == 5
        assert money_stats.invalid_count == 0
        assert money_stats.min_value == 50.25
        assert money_stats.max_value == 1000.00

        # Profile date column
        date_profiler = DateProfiler()
        for row in rows:
            date_profiler.update(row[3])  # date column
        date_stats = date_profiler.finalize()

        assert date_stats.valid_count == 5
        assert date_stats.invalid_count == 0
        assert date_stats.detected_format == 'YYYYMMDD'

    def test_utf8_with_multibyte_characters(self, sample_utf8_multibyte):
        """Test pipeline with UTF-8 multibyte characters."""
        # Stage 1: UTF-8 Validation
        stream = BytesIO(sample_utf8_multibyte)
        utf8_validator = UTF8Validator(stream)
        validation_result = utf8_validator.validate()

        assert validation_result.is_valid
        assert not validation_result.has_bom

        # Stage 2: CRLF Detection
        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        # Stage 3: CSV Parsing
        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)

        header_result = csv_parser.parse_header()
        assert header_result.success

        rows = list(csv_parser.parse_rows())
        assert len(rows) == 4
        assert rows[0][1] == '张三'  # Chinese characters
        assert rows[1][1] == 'Müller'  # German umlaut
        assert rows[2][1] == 'José'  # Spanish accent

    def test_crlf_windows_line_endings(self):
        """Test pipeline with Windows CRLF line endings."""
        csv_content = b"id|name|amount\r\n1|Alice|100.50\r\n2|Bob|250.75\r\n"

        # Stage 1: UTF-8 Validation
        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        validation_result = utf8_validator.validate()
        assert validation_result.is_valid

        # Stage 2: CRLF Detection
        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        line_ending_result = crlf_detector.detect()

        assert line_ending_result.style == LineEndingStyle.CRLF
        assert line_ending_result.crlf_count == 3
        assert line_ending_result.lf_count == 0

        normalized_content = crlf_detector.normalize()
        assert b'\r\n' not in normalized_content  # All normalized to LF
        assert b'\n' in normalized_content

    def test_mixed_line_endings(self):
        """Test pipeline with mixed line endings."""
        csv_content = b"id|name|amount\r\n1|Alice|100.50\n2|Bob|250.75\r3|Charlie|99.99\n"

        stream = BytesIO(csv_content)
        crlf_detector = CRLFDetector(stream)
        line_ending_result = crlf_detector.detect()

        assert line_ending_result.mixed
        assert line_ending_result.crlf_count > 0
        assert line_ending_result.lf_count > 0

        normalized_content = crlf_detector.normalize()
        # All line endings normalized to LF
        assert b'\r\n' not in normalized_content
        assert b'\r' not in normalized_content


@pytest.mark.integration
@pytest.mark.catastrophic
class TestPipelineCatastrophicErrors:
    """Test pipeline with catastrophic errors that should stop processing."""

    def test_invalid_utf8_stops_pipeline(self, sample_invalid_utf8):
        """Test that invalid UTF-8 stops pipeline immediately."""
        stream = BytesIO(sample_invalid_utf8)
        utf8_validator = UTF8Validator(stream)
        validation_result = utf8_validator.validate()

        # Should fail validation
        assert not validation_result.is_valid
        assert validation_result.error is not None
        assert validation_result.byte_offset is not None

        # Pipeline should NOT proceed to CRLF detection
        # This is a catastrophic error

    def test_empty_file_header_stops_pipeline(self):
        """Test that completely empty file stops pipeline at header parsing."""
        csv_content = b""  # Truly empty

        # Stage 1-2: UTF-8 valid for empty, CRLF normalize
        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        # Stage 3: CSV Parsing should fail on empty file
        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)

        with pytest.raises(ParserError) as exc:
            csv_parser.parse_header()

        assert exc.value.is_catastrophic
        assert 'header' in exc.value.message.lower() or 'empty' in exc.value.message.lower()

    def test_jagged_row_stops_pipeline(self):
        """Test that jagged rows stop pipeline."""
        csv_content = b"""id|name|amount
1|Alice|100.50
2|Bob
3|Charlie|99.99"""

        # Stages 1-2: Pass
        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        # Stage 3: CSV Parsing should fail on jagged row
        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)

        csv_parser.parse_header()

        with pytest.raises(ParserError) as exc:
            list(csv_parser.parse_rows())

        assert exc.value.is_catastrophic
        assert 'column count' in exc.value.message.lower() or 'jagged' in exc.value.code.lower()

    def test_empty_file_stops_pipeline(self):
        """Test that empty file stops pipeline."""
        csv_content = b""

        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        validation_result = utf8_validator.validate()

        # Empty file is valid UTF-8
        assert validation_result.is_valid

        # But CSV parsing should fail
        text_stream = StringIO(csv_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)

        with pytest.raises(ParserError) as exc:
            csv_parser.parse_header()

        assert exc.value.is_catastrophic


@pytest.mark.integration
class TestPipelineNonCatastrophicErrors:
    """Test pipeline with non-catastrophic errors that continue processing."""

    def test_money_format_violations_continue(self):
        """Test that money format violations are logged but processing continues."""
        csv_content = b"""id|amount
1|100.50
2|$250.75
3|99.99
4|1,000.00
5|(50.00)"""

        # Stages 1-3: Should all pass
        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)

        csv_parser.parse_header()
        rows = list(csv_parser.parse_rows())
        assert len(rows) == 5  # All rows parsed

        # Stage 5: Money validation should detect violations
        money_validator = MoneyValidator()
        values = [row[1] for row in rows]
        result = money_validator.validate_column(values)

        assert result.total_count == 5
        assert result.valid_count == 2  # Only rows 1 and 3
        assert result.invalid_count == 3  # Rows 2, 4, 5
        assert result.disallowed_symbols_found
        assert 'dollar_sign' in result.violations_by_type
        assert 'comma' in result.violations_by_type
        assert 'parentheses' in result.violations_by_type

    def test_date_format_violations_continue(self):
        """Test that date format violations are logged but processing continues."""
        csv_content = b"""id|date
1|20230101
2|2023-01-02
3|20230103
4|invalid
5|99991231"""

        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)

        csv_parser.parse_header()
        rows = list(csv_parser.parse_rows())
        assert len(rows) == 5

        # Date validation
        date_validator = DateValidator()
        values = [row[1] for row in rows]
        result = date_validator.validate_column(values)

        assert result.count == 5
        assert result.valid_count >= 2  # At least rows 1 and 3
        assert result.invalid_count >= 1  # Row 4
        assert not result.format_consistent  # Mixed formats

    def test_numeric_with_commas_continue(self):
        """Test that numeric values with commas are detected but processing continues."""
        csv_content = b"""id|value
1|100
2|1,000
3|250
4|10,000.50"""

        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)

        csv_parser.parse_header()
        rows = list(csv_parser.parse_rows())
        assert len(rows) == 4

        # Numeric profiling
        numeric_profiler = NumericProfiler()
        for row in rows:
            numeric_profiler.update(row[1])

        stats = numeric_profiler.finalize()
        assert stats.valid_count == 2  # Only rows 1 and 3
        assert stats.invalid_count == 2  # Rows 2 and 4 have commas


@pytest.mark.integration
class TestPipelineMixedTypes:
    """Test pipeline with mixed type columns."""

    def test_mixed_numeric_and_alpha(self):
        """Test column with mixed numeric and alpha values."""
        csv_content = b"""id|value
1|100
2|abc
3|200
4|def
5|300"""

        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        temp_file = Path(tempfile.mktemp(suffix='.csv'))
        temp_file.write_bytes(normalized_content)

        try:
            type_inferrer = TypeInferrer()
            result = type_inferrer.infer_column_types(temp_file, delimiter='|')

            # Should detect as mixed type
            assert 'value' in result.columns
            assert result.columns['value'].inferred_type in ['mixed', 'varchar']
        finally:
            temp_file.unlink()

    def test_money_with_inconsistent_decimals(self):
        """Test money column with inconsistent decimal places."""
        csv_content = b"""id|amount
1|100.50
2|250.5
3|99.99
4|1000
5|50.999"""

        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        temp_file = Path(tempfile.mktemp(suffix='.csv'))
        temp_file.write_bytes(normalized_content)

        try:
            type_inferrer = TypeInferrer()
            result = type_inferrer.infer_column_types(temp_file, delimiter='|')

            # Should detect as numeric or mixed due to inconsistent decimals
            assert 'amount' in result.columns
            # Type could be money, numeric, or mixed depending on thresholds
            assert result.columns['amount'].inferred_type in ['money', 'numeric', 'mixed']
        finally:
            temp_file.unlink()


@pytest.mark.integration
class TestPipelineCodeType:
    """Test pipeline with code/dictionary columns."""

    def test_code_type_detection(self):
        """Test detection of code type (low cardinality strings)."""
        csv_content = b"""id|status|code
1|active|A
2|inactive|B
3|active|A
4|pending|C
5|active|A
6|inactive|B"""

        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        temp_file = Path(tempfile.mktemp(suffix='.csv'))
        temp_file.write_bytes(normalized_content)

        try:
            type_inferrer = TypeInferrer()
            result = type_inferrer.infer_column_types(temp_file, delimiter='|')

            # Status column should be code type (low cardinality)
            assert result.columns['status'].inferred_type in ['code', 'alpha']
            assert result.columns['code'].inferred_type in ['code', 'alpha']

            # Profile code column
            text_stream = StringIO(normalized_content.decode('utf-8'))
            config = ParserConfig(delimiter='|', quoting=True, has_header=True)
            csv_parser = CSVParser(text_stream, config)
            csv_parser.parse_header()
            rows = list(csv_parser.parse_rows())

            code_profiler = CodeProfiler()
            for row in rows:
                code_profiler.update(row[2])  # code column

            stats = code_profiler.finalize()
            assert stats.distinct_count == 3  # A, B, C
            assert stats.count == 6
            assert stats.cardinality_ratio == 0.5  # 3/6
        finally:
            temp_file.unlink()


@pytest.mark.integration
class TestPipelineCandidateKeys:
    """Test pipeline with candidate key detection."""

    def test_unique_column_as_candidate_key(self):
        """Test detection of unique column as candidate key."""
        csv_content = b"""id|name|email
1|Alice|alice@example.com
2|Bob|bob@example.com
3|Charlie|charlie@example.com"""

        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)
        csv_parser.parse_header()
        rows = list(csv_parser.parse_rows())

        # Profile each column for distinctness
        id_profiler = StringProfiler()
        email_profiler = StringProfiler()

        for row in rows:
            id_profiler.update(row[0])
            email_profiler.update(row[2])

        id_stats = id_profiler.finalize()
        email_stats = email_profiler.finalize()

        # Both should have 100% distinct values (cardinality ratio = 1.0)
        assert id_stats.count == 3
        assert len(id_stats.top_values) == 3
        assert email_stats.count == 3


@pytest.mark.integration
@pytest.mark.slow
class TestPipelineLargeDatasets:
    """Test pipeline with large datasets."""

    def test_large_file_10k_rows(self, temp_workspace):
        """Test pipeline with 10,000 rows."""
        # Generate large CSV
        rows = ["id|name|amount|date|status"]
        for i in range(10000):
            rows.append(f"{i}|user{i}|{100.00 + i * 0.01:.2f}|2023{(i%12)+1:02d}{(i%28)+1:02d}|active")

        csv_content = "\n".join(rows).encode('utf-8')

        # Stage 1-2: UTF-8 and CRLF
        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        validation_result = utf8_validator.validate()
        assert validation_result.is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        # Stage 3: CSV Parsing
        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)
        csv_parser.parse_header()

        row_count = 0
        for row in csv_parser.parse_rows():
            row_count += 1
            assert len(row) == 5

        assert row_count == 10000

        # Stage 4-5: Type inference and profiling on sample
        temp_file = temp_workspace / "large_test.csv"
        temp_file.write_bytes(normalized_content)

        type_inferrer = TypeInferrer(sample_size=1000)  # Sample for speed
        result = type_inferrer.infer_column_types(temp_file, delimiter='|')

        assert result.inference_method == "sample"
        assert 'id' in result.columns
        assert result.columns['id'].inferred_type == 'numeric'

    def test_large_file_streaming_memory_efficiency(self, temp_workspace):
        """Test that large files are processed with streaming (constant memory)."""
        # Generate 50,000 rows
        rows = ["id|value"]
        for i in range(50000):
            rows.append(f"{i}|value{i}")

        csv_content = "\n".join(rows).encode('utf-8')
        temp_file = temp_workspace / "very_large_test.csv"
        temp_file.write_bytes(csv_content)

        # UTF-8 validation should stream
        with open(temp_file, 'rb') as f:
            utf8_validator = UTF8Validator(f, chunk_size=8192)
            validation_result = utf8_validator.validate()
            assert validation_result.is_valid

        # CSV parsing should stream
        with open(temp_file, 'r', encoding='utf-8') as f:
            config = ParserConfig(delimiter='|', quoting=True, has_header=True)
            csv_parser = CSVParser(f, config)
            csv_parser.parse_header()

            row_count = 0
            for row in csv_parser.parse_rows():
                row_count += 1
                if row_count > 100:  # Sample first 100 rows
                    break

            assert row_count == 101  # Read 101 rows successfully


@pytest.mark.integration
class TestPipelineDuplicateDetection:
    """Test pipeline with duplicate detection."""

    def test_exact_duplicates(self):
        """Test detection of exact duplicate rows."""
        csv_content = b"""id|name|amount
1|Alice|100.50
2|Bob|250.75
1|Alice|100.50
3|Charlie|99.99
2|Bob|250.75"""

        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)
        csv_parser.parse_header()
        rows = list(csv_parser.parse_rows())

        # Track row hashes for duplicates
        row_hashes = set()
        duplicate_count = 0

        for row in rows:
            row_hash = tuple(row)
            if row_hash in row_hashes:
                duplicate_count += 1
            else:
                row_hashes.add(row_hash)

        assert duplicate_count == 2  # Rows 3 and 5 are duplicates

    def test_duplicate_key_values(self):
        """Test detection of duplicate values in potential key columns."""
        csv_content = b"""id|email|name
1|alice@example.com|Alice
2|bob@example.com|Bob
3|alice@example.com|Alice2
4|charlie@example.com|Charlie"""

        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)
        csv_parser.parse_header()
        rows = list(csv_parser.parse_rows())

        # Check email column for duplicates
        email_values = [row[1] for row in rows]
        email_distinct = len(set(email_values))

        assert len(email_values) == 4
        assert email_distinct == 3  # alice@example.com appears twice


@pytest.mark.integration
class TestPipelineGoldenFiles:
    """Test pipeline with golden reference files."""

    def test_golden_file_basic(self, temp_workspace):
        """Test pipeline against golden reference output."""
        # Golden input
        csv_content = b"""id|name|amount|date
1|Alice|100.50|20230101
2|Bob|250.75|20230102"""

        # Process through pipeline
        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()

        text_stream = StringIO(normalized_content.decode('utf-8'))
        config = ParserConfig(delimiter='|', quoting=True, has_header=True)
        csv_parser = CSVParser(text_stream, config)
        csv_parser.parse_header()
        rows = list(csv_parser.parse_rows())

        # Golden expectations
        assert len(rows) == 2
        assert rows[0] == ['1', 'Alice', '100.50', '20230101']
        assert rows[1] == ['2', 'Bob', '250.75', '20230102']

        # Type inference golden expectations
        temp_file = temp_workspace / "golden.csv"
        temp_file.write_bytes(normalized_content)

        type_inferrer = TypeInferrer()
        result = type_inferrer.infer_column_types(temp_file, delimiter='|')

        assert result.columns['id'].inferred_type == 'numeric'
        assert result.columns['name'].inferred_type in ['alpha', 'varchar']
        assert result.columns['amount'].inferred_type == 'money'
        assert result.columns['date'].inferred_type == 'date'
        assert result.columns['date'].detected_format == 'YYYYMMDD'


@pytest.mark.integration
class TestPipelineEndToEnd:
    """Full end-to-end integration tests."""

    def test_complete_workflow_success(self, temp_workspace):
        """Test complete workflow from upload to profile."""
        # Simulate uploaded file
        csv_content = b"""transaction_id|customer_name|amount|date|status|category
TXN001|John Doe|1250.00|20231101|completed|retail
TXN002|Jane Smith|850.50|20231102|completed|online
TXN003|Bob Johnson|2100.75|20231103|pending|wholesale
TXN004|Alice Williams|450.00|20231104|completed|retail
TXN005|Charlie Brown|3200.25|20231105|completed|online"""

        # Full pipeline execution
        temp_file = temp_workspace / "transactions.csv"

        # Stage 1: UTF-8 Validation
        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        validation_result = utf8_validator.validate()

        if not validation_result.is_valid:
            pytest.fail(f"UTF-8 validation failed: {validation_result.error}")

        # Stage 2: CRLF Normalization
        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        line_ending_result = crlf_detector.detect()
        normalized_content = crlf_detector.normalize()

        # Write normalized content
        temp_file.write_bytes(normalized_content)

        # Stage 3: CSV Parsing
        with open(temp_file, 'r', encoding='utf-8') as f:
            config = ParserConfig(delimiter='|', quoting=True, has_header=True)
            csv_parser = CSVParser(f, config)

            header_result = csv_parser.parse_header()
            if not header_result.success:
                pytest.fail(f"CSV parsing failed: {header_result.error}")

            rows = list(csv_parser.parse_rows())

        # Stage 4: Type Inference
        type_inferrer = TypeInferrer()
        type_result = type_inferrer.infer_column_types(temp_file, delimiter='|')

        # Stage 5: Statistical Profiling
        profiles = {}

        # Profile transaction_id (should be code or varchar)
        string_profiler = StringProfiler()
        for row in rows:
            string_profiler.update(row[0])
        profiles['transaction_id'] = string_profiler.finalize()

        # Profile amount (money)
        money_profiler = MoneyProfiler()
        for row in rows:
            money_profiler.update(row[2])
        profiles['amount'] = money_profiler.finalize()

        # Profile date
        date_profiler = DateProfiler()
        for row in rows:
            date_profiler.update(row[3])
        profiles['date'] = date_profiler.finalize()

        # Profile status (code)
        code_profiler = CodeProfiler()
        for row in rows:
            code_profiler.update(row[4])
        profiles['status'] = code_profiler.finalize()

        # Assertions on complete workflow
        assert len(rows) == 5
        assert type_result.columns['amount'].inferred_type == 'money'
        assert profiles['amount'].valid_count == 5
        assert profiles['amount'].min_value == 450.00
        assert profiles['amount'].max_value == 3200.25

        assert type_result.columns['date'].inferred_type == 'date'
        assert profiles['date'].valid_count == 5
        assert profiles['date'].detected_format == 'YYYYMMDD'

        assert profiles['status'].distinct_count == 2  # completed, pending
        assert profiles['status'].cardinality_ratio < 0.5

    def test_complete_workflow_with_recoverable_errors(self, temp_workspace):
        """Test complete workflow with non-catastrophic errors."""
        csv_content = b"""id|amount|date
1|100.50|20230101
2|$250.75|20230102
3|99.99|invalid
4|1,000.00|20230104"""

        temp_file = temp_workspace / "data_with_errors.csv"

        # Full pipeline - should complete despite errors
        stream = BytesIO(csv_content)
        utf8_validator = UTF8Validator(stream)
        assert utf8_validator.validate().is_valid

        stream.seek(0)
        crlf_detector = CRLFDetector(stream)
        normalized_content = crlf_detector.normalize()
        temp_file.write_bytes(normalized_content)

        with open(temp_file, 'r', encoding='utf-8') as f:
            config = ParserConfig(delimiter='|', quoting=True, has_header=True)
            csv_parser = CSVParser(f, config)
            csv_parser.parse_header()
            rows = list(csv_parser.parse_rows())

        assert len(rows) == 4  # All rows parsed

        # Money validation - errors logged but not fatal
        money_validator = MoneyValidator()
        amount_values = [row[1] for row in rows]
        money_result = money_validator.validate_column(amount_values)

        assert money_result.valid_count == 2  # Rows 1 and 3
        assert money_result.invalid_count == 2  # Rows 2 and 4

        # Date validation - errors logged but not fatal
        date_validator = DateValidator()
        date_values = [row[2] for row in rows]
        date_result = date_validator.validate_column(date_values)

        assert date_result.valid_count == 3  # Rows 1, 2, 4
        assert date_result.invalid_count == 1  # Row 3
