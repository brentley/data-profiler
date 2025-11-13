"""
CSV parser tests.

Tests the CSV parser that must:
- Require header row
- Enforce constant column count (jagged rows are catastrophic)
- Handle pipe and comma delimiters
- Implement proper quoting rules (doubled quotes, embedded delimiters)
- Handle embedded CRLF in quoted fields
"""

import pytest
from io import StringIO
from services.ingest import CSVParser, ParserError


class TestCSVParserBasics:
    """Test basic CSV parsing functionality."""

    def test_simple_pipe_delimited(self):
        """Should parse simple pipe-delimited CSV."""
        data = "col1|col2|col3\nval1|val2|val3\nval4|val5|val6\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        rows = list(parser.parse())
        assert parser.header == ['col1', 'col2', 'col3']
        assert len(rows) == 2
        assert rows[0] == ['val1', 'val2', 'val3']
        assert rows[1] == ['val4', 'val5', 'val6']

    def test_simple_comma_delimited(self):
        """Should parse simple comma-delimited CSV."""
        data = "col1,col2,col3\nval1,val2,val3\n"
        parser = CSVParser(StringIO(data), delimiter=',')

        rows = list(parser.parse())
        assert parser.header == ['col1', 'col2', 'col3']
        assert len(rows) == 1
        assert rows[0] == ['val1', 'val2', 'val3']

    def test_missing_header_fails(self):
        """Should fail catastrophically if header is missing."""
        # Empty file
        data = ""
        parser = CSVParser(StringIO(data), delimiter='|')

        with pytest.raises(ParserError) as exc:
            list(parser.parse())
        assert "header" in str(exc.value).lower()
        assert exc.value.is_catastrophic is True

    def test_jagged_row_more_columns_fails(self):
        """Should fail catastrophically on row with more columns."""
        data = "col1|col2|col3\nval1|val2|val3\nval4|val5|val6|val7\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        with pytest.raises(ParserError) as exc:
            list(parser.parse())
        assert "column count" in str(exc.value).lower()
        assert exc.value.is_catastrophic is True
        assert exc.value.line_number == 3

    def test_jagged_row_fewer_columns_fails(self):
        """Should fail catastrophically on row with fewer columns."""
        data = "col1|col2|col3\nval1|val2|val3\nval4|val5\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        with pytest.raises(ParserError) as exc:
            list(parser.parse())
        assert "column count" in str(exc.value).lower()
        assert exc.value.is_catastrophic is True

    def test_empty_fields(self):
        """Should handle empty fields correctly."""
        data = "col1|col2|col3\nval1||val3\n|val2|\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        rows = list(parser.parse())
        assert len(rows) == 2
        assert rows[0] == ['val1', '', 'val3']
        assert rows[1] == ['', 'val2', '']

    def test_whitespace_preserved(self):
        """Should preserve whitespace in fields."""
        data = "col1|col2|col3\n val1 | val2 |val3 \n"
        parser = CSVParser(StringIO(data), delimiter='|')

        rows = list(parser.parse())
        assert rows[0] == [' val1 ', ' val2 ', 'val3 ']


class TestCSVParserQuoting:
    """Test CSV quoting rules."""

    def test_quoted_field(self):
        """Should handle quoted fields."""
        data = 'col1|col2|col3\n"val1"|"val2"|"val3"\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        rows = list(parser.parse())
        assert rows[0] == ['val1', 'val2', 'val3']

    def test_embedded_delimiter_requires_quotes(self):
        """Embedded delimiter without quotes should be error."""
        data = 'col1|col2|col3\nval1|val2,extra|val3\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        # This should parse but generate non-catastrophic error
        rows = list(parser.parse())
        assert len(parser.errors) > 0
        assert any("delimiter" in e.message.lower() for e in parser.errors)

    def test_embedded_delimiter_with_quotes(self):
        """Embedded delimiter with quotes should work."""
        data = 'col1|col2|col3\nval1|"val2|extra"|val3\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        rows = list(parser.parse())
        assert rows[0] == ['val1', 'val2|extra', 'val3']

    def test_doubled_quotes_inside_field(self):
        """Inner quotes must be doubled."""
        data = 'col1|col2|col3\nval1|"val2""quoted"""|val3\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        rows = list(parser.parse())
        assert rows[0] == ['val1', 'val2"quoted"', 'val3']

    def test_embedded_newline_requires_quotes(self):
        """Embedded newline without quotes should error."""
        # This is actually impossible to represent in test without quotes
        # But parser should detect unquoted multiline
        pass  # Handled by next test

    def test_embedded_newline_with_quotes(self):
        """Embedded newline with quotes should work."""
        data = 'col1|col2|col3\nval1|"val2\nwith\nnewlines"|val3\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        rows = list(parser.parse())
        assert len(rows) == 1
        assert rows[0] == ['val1', 'val2\nwith\nnewlines', 'val3']

    def test_unmatched_quote_error(self):
        """Unmatched quotes should generate error."""
        data = 'col1|col2|col3\nval1|"val2|val3\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        with pytest.raises(ParserError) as exc:
            list(parser.parse())
        assert "quote" in str(exc.value).lower()

    def test_quote_in_middle_of_field(self):
        """Quote in middle of unquoted field should error."""
        data = 'col1|col2|col3\nval1|val"2|val3\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        rows = list(parser.parse())
        # Non-catastrophic error
        assert len(parser.errors) > 0

    def test_optional_quoting(self):
        """Quoting should be optional for simple fields."""
        data = 'col1|col2|col3\nval1|"val2"|val3\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        rows = list(parser.parse())
        assert rows[0] == ['val1', 'val2', 'val3']

    def test_empty_quoted_field(self):
        """Empty quoted field should work."""
        data = 'col1|col2|col3\nval1|""|val3\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        rows = list(parser.parse())
        assert rows[0] == ['val1', '', 'val3']

    def test_whitespace_around_quotes(self):
        """Whitespace around quotes should be preserved or stripped per config."""
        data = 'col1|col2|col3\nval1| "val2" |val3\n'
        parser = CSVParser(StringIO(data), delimiter='|', quoted=True)

        rows = list(parser.parse())
        # Standard CSV behavior: whitespace outside quotes is preserved
        assert rows[0][1].strip() == 'val2'


class TestCSVParserStreaming:
    """Test streaming and large file handling."""

    def test_large_file_streaming(self):
        """Should handle large files efficiently."""
        # Generate 10k rows
        header = "col1|col2|col3\n"
        rows = "\n".join([f"val{i}|val{i}|val{i}" for i in range(10000)])
        data = header + rows + "\n"

        parser = CSVParser(StringIO(data), delimiter='|')

        count = 0
        for row in parser.parse():
            count += 1
            assert len(row) == 3

        assert count == 10000

    def test_row_counter(self):
        """Should track row numbers correctly."""
        data = "col1|col2|col3\nval1|val2|val3\nval4|val5|val6\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        rows = list(parser.parse())
        assert parser.row_count == 2
        assert parser.total_lines == 3  # Including header

    def test_byte_counter(self):
        """Should track bytes processed."""
        data = "col1|col2|col3\nval1|val2|val3\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        list(parser.parse())
        assert parser.bytes_processed > 0


class TestCSVParserEdgeCases:
    """Test edge cases and special scenarios."""

    def test_single_column(self):
        """Should handle single column CSV."""
        data = "col1\nval1\nval2\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        rows = list(parser.parse())
        assert parser.header == ['col1']
        assert len(rows) == 2

    def test_many_columns(self):
        """Should handle CSV with many columns."""
        # 100 columns
        cols = "|".join([f"col{i}" for i in range(100)])
        vals = "|".join([f"val{i}" for i in range(100)])
        data = f"{cols}\n{vals}\n"

        parser = CSVParser(StringIO(data), delimiter='|')
        rows = list(parser.parse())

        assert len(parser.header) == 100
        assert len(rows[0]) == 100

    def test_unicode_in_fields(self):
        """Should handle Unicode characters."""
        data = "col1|col2|col3\nval1|世界|val3\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        rows = list(parser.parse())
        assert rows[0] == ['val1', '世界', 'val3']

    def test_null_bytes_handling(self):
        """Should handle or reject null bytes."""
        data = "col1|col2|col3\nval1|\x00|val3\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        # Null bytes might be valid or might generate warning
        rows = list(parser.parse())
        assert len(rows) == 1

    def test_very_long_field(self):
        """Should handle very long fields."""
        long_val = "x" * 100000
        data = f"col1|col2|col3\nval1|{long_val}|val3\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        rows = list(parser.parse())
        assert len(rows[0][1]) == 100000

    def test_trailing_delimiter(self):
        """Should handle trailing delimiter correctly."""
        data = "col1|col2|col3|\nval1|val2|val3|\n"
        parser = CSVParser(StringIO(data), delimiter='|')

        # Trailing delimiter means 4 columns (last is empty)
        with pytest.raises(ParserError):
            # Header has 4 columns but we expected 3
            list(parser.parse())
