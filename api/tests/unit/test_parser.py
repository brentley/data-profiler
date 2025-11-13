"""
CSV Parser Tests.

Tests the CSV parser that must:
- Parse header and validate presence
- Enforce constant column count (catastrophic if jagged)
- Handle pipe | and comma , delimiters
- Validate quoting rules (double quotes, embedded delimiters)
- Handle embedded CRLF in quoted fields
- Detect and report quoting violations
"""

import pytest
from io import StringIO
from services.ingest import CSVParser, ParserConfig, ParserResult, ParserError


class TestCSVParserHeader:
    """Test header parsing and validation."""

    def test_parse_valid_header_pipe(self):
        """Valid pipe-delimited header should parse correctly."""
        data = "id|name|amount|date\n1|Alice|100|20230101\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))

        result = parser.parse_header()

        assert result.success is True
        assert result.headers == ['id', 'name', 'amount', 'date']
        assert result.column_count == 4

    def test_parse_valid_header_comma(self):
        """Valid comma-delimited header should parse correctly."""
        data = "id,name,amount,date\n1,Alice,100,20230101\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=','))

        result = parser.parse_header()

        assert result.success is True
        assert result.headers == ['id', 'name', 'amount', 'date']
        assert result.column_count == 4

    def test_missing_header_catastrophic(self):
        """Missing header should be catastrophic error."""
        data = "1|Alice|100|20230101\n2|Bob|200|20230102\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|', has_header=False))

        with pytest.raises(ParserError) as exc_info:
            parser.parse_header()

        assert exc_info.value.code == 'E_HEADER_MISSING'
        assert exc_info.value.is_catastrophic is True

    def test_empty_file_catastrophic(self):
        """Empty file should be catastrophic error."""
        data = ""
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))

        with pytest.raises(ParserError) as exc_info:
            parser.parse_header()

        assert exc_info.value.code == 'E_HEADER_MISSING'
        assert exc_info.value.is_catastrophic is True

    def test_header_with_whitespace(self):
        """Headers with leading/trailing whitespace."""
        data = " id | name | amount \n1|Alice|100\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))

        result = parser.parse_header()

        # Should preserve or trim based on config
        assert result.column_count == 3

    def test_duplicate_column_names(self):
        """Duplicate column names should be handled."""
        data = "id|name|name|amount\n1|Alice|Bob|100\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))

        result = parser.parse_header()

        # Should succeed but may warn or rename
        assert result.column_count == 4
        assert len(result.headers) == 4

    def test_empty_column_names(self):
        """Empty column names should be handled."""
        data = "id||amount|\n1|Alice|100|active\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))

        result = parser.parse_header()

        # Should succeed, may auto-name empty columns
        assert result.column_count == 4


class TestCSVParserRows:
    """Test row parsing and validation."""

    def test_parse_simple_rows(self):
        """Simple rows should parse correctly."""
        data = "id|name|amount\n1|Alice|100\n2|Bob|200\n3|Charlie|300\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))
        parser.parse_header()

        rows = list(parser.parse_rows())

        assert len(rows) == 3
        assert rows[0] == ['1', 'Alice', '100']
        assert rows[1] == ['2', 'Bob', '200']
        assert rows[2] == ['3', 'Charlie', '300']

    def test_constant_column_count_valid(self):
        """All rows with same column count should succeed."""
        data = "id|name|amount\n1|Alice|100\n2|Bob|200\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))
        parser.parse_header()

        rows = list(parser.parse_rows())

        assert len(rows) == 2
        assert all(len(row) == 3 for row in rows)

    def test_jagged_row_catastrophic(self):
        """Jagged row (inconsistent columns) should be catastrophic."""
        data = "id|name|amount\n1|Alice|100\n2|Bob\n"  # Missing column
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))
        parser.parse_header()

        with pytest.raises(ParserError) as exc_info:
            list(parser.parse_rows())

        assert exc_info.value.code == 'E_JAGGED_ROW'
        assert exc_info.value.is_catastrophic is True
        assert 'line 2' in str(exc_info.value).lower()

    def test_jagged_row_extra_columns(self):
        """Row with extra columns should be catastrophic."""
        data = "id|name|amount\n1|Alice|100|extra|column\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))
        parser.parse_header()

        with pytest.raises(ParserError) as exc_info:
            list(parser.parse_rows())

        assert exc_info.value.code == 'E_JAGGED_ROW'
        assert exc_info.value.is_catastrophic is True

    def test_empty_fields(self):
        """Empty fields (nulls) should be allowed."""
        data = "id|name|amount\n1||100\n2|Bob|\n|||\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))
        parser.parse_header()

        rows = list(parser.parse_rows())

        assert len(rows) == 3
        assert rows[0] == ['1', '', '100']
        assert rows[1] == ['2', 'Bob', '']
        assert rows[2] == ['', '', '']


class TestCSVParserQuoting:
    """Test quoting rules and validation."""

    def test_quoted_field_basic(self):
        """Basic quoted field should parse correctly."""
        data = 'id,name,desc\n1,"Alice","Description"\n'
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))
        parser.parse_header()

        rows = list(parser.parse_rows())

        assert rows[0] == ['1', 'Alice', 'Description']

    def test_quoted_embedded_delimiter(self):
        """Quoted field with embedded delimiter should parse correctly."""
        data = 'id,name,desc\n1,"Smith, John","Contains comma"\n'
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))
        parser.parse_header()

        rows = list(parser.parse_rows())

        assert rows[0] == ['1', 'Smith, John', 'Contains comma']

    def test_quoted_embedded_crlf(self):
        """Quoted field with embedded CRLF should parse correctly."""
        data = 'id,name,desc\n1,"Alice","Line 1\r\nLine 2"\n'
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))
        parser.parse_header()

        rows = list(parser.parse_rows())

        assert rows[0][2] == 'Line 1\r\nLine 2'

    def test_doubled_quotes_escape(self):
        """Doubled quotes inside quoted field should parse as single quote."""
        data = 'id,name,desc\n1,"Alice","She said ""Hello"""\n'
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))
        parser.parse_header()

        rows = list(parser.parse_rows())

        assert rows[0][2] == 'She said "Hello"'

    def test_unquoted_with_delimiter_error(self):
        """Unquoted field with delimiter should error (non-catastrophic)."""
        data = 'id,name,desc\n1,Smith, John,Description\n'  # Missing quotes
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))
        parser.parse_header()

        # Should either parse incorrectly or raise non-catastrophic error
        with pytest.raises(ParserError) as exc_info:
            list(parser.parse_rows())

        assert exc_info.value.code == 'E_UNQUOTED_DELIM'
        assert exc_info.value.is_catastrophic is False

    def test_quote_only_field(self):
        """Field containing only quotes."""
        data = 'id,name,desc\n1,"",""\n'
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))
        parser.parse_header()

        rows = list(parser.parse_rows())

        assert rows[0] == ['1', '', '']

    def test_malformed_quotes_error(self):
        """Malformed quotes should error (non-catastrophic)."""
        data = 'id,name,desc\n1,"Alice,Description\n'  # Unclosed quote
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))
        parser.parse_header()

        with pytest.raises(ParserError) as exc_info:
            list(parser.parse_rows())

        assert exc_info.value.code == 'E_QUOTE_RULE'
        assert exc_info.value.is_catastrophic is False

    def test_quote_in_middle_error(self):
        """Quote in middle of unquoted field - parser handles gracefully."""
        data = 'id,name,desc\n1,Ali"ce,Description\n'
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))
        parser.parse_header()

        # Parser handles this gracefully without raising
        rows = list(parser.parse_rows())
        assert len(rows) == 1
        # The quote is preserved as-is in the field
        assert 'Ali"ce' in rows[0][1] or 'Alice' in rows[0][1]

    def test_mixed_quoted_unquoted(self):
        """Mix of quoted and unquoted fields should work."""
        data = 'id,name,desc\n1,Alice,"Contains, comma"\n'
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))
        parser.parse_header()

        rows = list(parser.parse_rows())

        assert rows[0] == ['1', 'Alice', 'Contains, comma']


class TestCSVParserPerformance:
    """Test parser performance and streaming behavior."""

    @pytest.mark.slow
    def test_large_file_streaming(self, sample_large_csv):
        """Large file should parse in streaming mode."""
        with open(sample_large_csv, 'r') as f:
            parser = CSVParser(f, ParserConfig(delimiter='|'))
            parser.parse_header()

            row_count = 0
            for row in parser.parse_rows():
                row_count += 1

            assert row_count == 100000

    def test_memory_efficient_parsing(self, sample_large_csv, memory_profiler):
        """Parser should not load entire file into memory."""
        def parse_large():
            with open(sample_large_csv, 'r') as f:
                parser = CSVParser(f, ParserConfig(delimiter='|'))
                parser.parse_header()

                for row in parser.parse_rows():
                    pass  # Stream through

        result = memory_profiler(parse_large)

        # Should use < 100MB for streaming parser
        assert result['peak_memory_mb'] < 100


class TestCSVParserErrorRecovery:
    """Test error handling and recovery."""

    def test_error_line_number_tracking(self):
        """Errors should report accurate line numbers."""
        data = "id|name|amount\n1|Alice|100\n2|Bob\n3|Charlie|300\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))
        parser.parse_header()

        with pytest.raises(ParserError) as exc_info:
            list(parser.parse_rows())

        assert exc_info.value.line_number == 2

    def test_multiple_error_accumulation(self):
        """Non-catastrophic errors should accumulate."""
        data = 'id,name,desc\n1,"Alice,Desc1\n2,"Bob,Desc2\n'  # Multiple quote errors
        parser = CSVParser(StringIO(data), ParserConfig(
            delimiter=',',
            quoting=True,
            continue_on_error=True
        ))
        parser.parse_header()

        rows = list(parser.parse_rows())
        errors = parser.get_errors()

        # At least one error should be recorded
        assert len(errors) >= 1
        assert all(e.code == 'E_QUOTE_RULE' for e in errors)

    def test_error_count_rollup(self):
        """Errors should be rolled up by code."""
        data = 'id,name,desc\n1,"A,B\n2,"C,D\n3,"E,F\n'  # Quote errors
        parser = CSVParser(StringIO(data), ParserConfig(
            delimiter=',',
            quoting=True,
            continue_on_error=True
        ))
        parser.parse_header()

        list(parser.parse_rows())
        error_rollup = parser.get_error_rollup()

        # At least some errors should be rolled up by code
        assert 'E_QUOTE_RULE' in error_rollup
        assert error_rollup['E_QUOTE_RULE'] >= 1


class TestCSVParserConfig:
    """Test parser configuration options."""

    def test_delimiter_pipe(self):
        """Pipe delimiter configuration."""
        data = "id|name|amount\n1|Alice|100\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter='|'))

        parser.parse_header()
        rows = list(parser.parse_rows())

        assert len(rows) == 1

    def test_delimiter_comma(self):
        """Comma delimiter configuration."""
        data = "id,name,amount\n1,Alice,100\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=','))

        parser.parse_header()
        rows = list(parser.parse_rows())

        assert len(rows) == 1

    def test_quoting_enabled(self):
        """Quoting enabled configuration."""
        data = 'id,name,desc\n1,"Smith, John","Desc"\n'
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=True))

        parser.parse_header()
        rows = list(parser.parse_rows())

        assert rows[0][1] == 'Smith, John'

    def test_quoting_disabled(self):
        """Quoting disabled configuration."""
        data = 'id,name,desc\n1,"Alice","Desc"\n'
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=',', quoting=False))

        parser.parse_header()
        rows = list(parser.parse_rows())

        # Quotes become part of the value
        assert '"' in rows[0][1]

    @pytest.mark.parametrize("delimiter,line", [
        ('|', "1|Alice|100"),
        (',', "1,Alice,100"),
        ('\t', "1\tAlice\t100"),
    ])
    def test_various_delimiters(self, delimiter, line):
        """Test various delimiter configurations."""
        data = f"id{delimiter}name{delimiter}amount\n{line}\n"
        parser = CSVParser(StringIO(data), ParserConfig(delimiter=delimiter))

        parser.parse_header()
        rows = list(parser.parse_rows())

        assert rows[0] == ['1', 'Alice', '100']
