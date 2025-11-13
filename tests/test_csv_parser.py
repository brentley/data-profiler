"""
Test suite for CSV parsing with strict validation.

RED PHASE: These tests define expected CSV parsing behavior.

Requirements from spec:
- Header required (catastrophic failure if missing)
- Constant column count across all rows (catastrophic failure if jagged)
- Delimiter: pipe | or comma ,
- Quoting: optional double quotes; inner quotes must be doubled
- Embedded delimiters/CRLF only when quoted
"""
import pytest
from pathlib import Path


class TestCSVParser:
    """Test CSV parsing functionality."""

    def test_parse_basic_pipe_delimited(self, sample_csv_basic: Path):
        """Test parsing basic pipe-delimited CSV."""
        from api.services.parser import CSVParser

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(sample_csv_basic)

        assert result.is_valid is True
        assert result.header == ["ID", "Name", "Age", "Salary"]
        assert result.row_count == 3
        assert result.column_count == 4

    def test_parse_comma_delimited(self, temp_dir: Path):
        """Test parsing comma-delimited CSV."""
        from api.services.parser import CSVParser

        csv_path = temp_dir / "comma.csv"
        csv_path.write_text(
            "ID,Name,Age\n"
            "1,Alice,30\n"
            "2,Bob,25\n",
            encoding="utf-8"
        )

        parser = CSVParser(delimiter=",")
        result = parser.parse_file(csv_path)

        assert result.is_valid is True
        assert result.header == ["ID", "Name", "Age"]
        assert result.column_count == 3

    def test_catastrophic_failure_missing_header(self, sample_csv_no_header: Path):
        """Test that missing header causes catastrophic failure."""
        from api.services.parser import CSVParser, CatastrophicParseError

        parser = CSVParser(delimiter="|", expect_header=True)

        with pytest.raises(CatastrophicParseError) as exc_info:
            parser.parse_file(sample_csv_no_header)

        assert "header" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "E_HEADER_MISSING"

    def test_catastrophic_failure_jagged_rows(self, sample_csv_jagged: Path):
        """Test that inconsistent column count causes catastrophic failure."""
        from api.services.parser import CSVParser, CatastrophicParseError

        parser = CSVParser(delimiter="|")

        with pytest.raises(CatastrophicParseError) as exc_info:
            parser.parse_file(sample_csv_jagged)

        assert "column" in str(exc_info.value).lower() or "jagged" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "E_JAGGED_ROW"
        assert exc_info.value.row_number is not None

    def test_quoted_fields_with_embedded_delimiters(self, sample_csv_quoted: Path):
        """Test parsing quoted fields containing delimiters."""
        from api.services.parser import CSVParser

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(sample_csv_quoted)

        assert result.is_valid is True
        rows = list(result.rows)
        # "Smith, John" should be parsed as single field
        assert "Smith, John" in rows[0]
        # "Uses | delimiter" should be parsed as single field
        assert "Uses | delimiter" in rows[0]

    def test_doubled_quotes_in_quoted_fields(self, sample_csv_quoted: Path):
        """Test that doubled quotes are correctly unescaped."""
        from api.services.parser import CSVParser

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(sample_csv_quoted)

        rows = list(result.rows)
        # 'Quote has ""doubled"" quotes' should become 'Quote has "doubled" quotes'
        assert any('Quote has "doubled" quotes' in str(row) for row in rows)

    def test_embedded_crlf_in_quoted_field(self, temp_dir: Path):
        """Test parsing quoted field with embedded CRLF."""
        from api.services.parser import CSVParser

        csv_path = temp_dir / "embedded_crlf.csv"
        csv_path.write_bytes(
            b'ID|Description\r\n'
            b'1|"Line 1\r\nLine 2"\r\n'
            b'2|Normal\r\n'
        )

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(csv_path)

        assert result.is_valid is True
        rows = list(result.rows)
        # The description field should contain the newline
        assert any("\n" in str(row) for row in rows)

    def test_error_unquoted_field_with_delimiter(self, temp_dir: Path):
        """Test non-catastrophic error for unquoted field containing delimiter."""
        from api.services.parser import CSVParser

        csv_path = temp_dir / "unquoted_delim.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Smith, John\n",  # Comma in unquoted field (should be error if comma is delimiter)
            encoding="utf-8"
        )

        parser = CSVParser(delimiter=",")
        result = parser.parse_file(csv_path)

        # This should parse but may generate warnings
        # The exact behavior depends on implementation
        assert len(result.warnings) > 0 or result.column_count != 2

    def test_error_quote_not_at_field_start(self, temp_dir: Path):
        """Test error for quote character not at field start."""
        from api.services.parser import CSVParser

        csv_path = temp_dir / "mid_quote.csv"
        csv_path.write_text(
            'ID|Name\n'
            '1|Some"Quote\n',
            encoding="utf-8"
        )

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(csv_path)

        # Non-catastrophic error
        assert len(result.errors) > 0 or len(result.warnings) > 0

    def test_error_undoubled_quote_inside_field(self, temp_dir: Path):
        """Test error for single quote inside quoted field."""
        from api.services.parser import CSVParser

        csv_path = temp_dir / "single_quote.csv"
        csv_path.write_text(
            'ID|Name\n'
            '1|"Has a " single quote"\n',  # Should be "" not "
            encoding="utf-8"
        )

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(csv_path)

        # Non-catastrophic error
        assert len(result.errors) > 0 or len(result.warnings) > 0

    def test_empty_fields(self, temp_dir: Path):
        """Test parsing of empty fields."""
        from api.services.parser import CSVParser

        csv_path = temp_dir / "empty_fields.csv"
        csv_path.write_text(
            "ID|Name|Age\n"
            "1||30\n"
            "2|Bob|\n"
            "|||\n",
            encoding="utf-8"
        )

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(csv_path)

        assert result.is_valid is True
        assert result.row_count == 3
        rows = list(result.rows)
        assert rows[0][1] == "" or rows[0][1] is None  # Empty name

    def test_quoted_empty_field(self, temp_dir: Path):
        """Test parsing of quoted empty field."""
        from api.services.parser import CSVParser

        csv_path = temp_dir / "quoted_empty.csv"
        csv_path.write_text(
            'ID|Name\n'
            '1|""\n'
            '2|Bob\n',
            encoding="utf-8"
        )

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(csv_path)

        assert result.is_valid is True
        rows = list(result.rows)
        assert rows[0][1] == ""

    def test_whitespace_handling(self, temp_dir: Path):
        """Test that whitespace in unquoted fields is preserved."""
        from api.services.parser import CSVParser

        csv_path = temp_dir / "whitespace.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1| Alice \n"
            "2|  Bob\n",
            encoding="utf-8"
        )

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(csv_path)

        rows = list(result.rows)
        # Whitespace should be preserved
        assert rows[0][1] == " Alice "
        assert rows[1][1] == "  Bob"

    def test_header_normalization(self, temp_dir: Path):
        """Test header field name normalization."""
        from api.services.parser import CSVParser

        csv_path = temp_dir / "header_spaces.csv"
        csv_path.write_text(
            " ID | Name | Age \n"
            "1|Alice|30\n",
            encoding="utf-8"
        )

        parser = CSVParser(delimiter="|", normalize_header=True)
        result = parser.parse_file(csv_path)

        # Headers should be trimmed
        assert result.header == ["ID", "Name", "Age"]

    def test_large_file_streaming(self, temp_dir: Path):
        """Test that parser can stream large files."""
        from api.services.parser import CSVParser

        large_csv = temp_dir / "large.csv"
        with large_csv.open("w", encoding="utf-8") as f:
            f.write("ID|Name|Value\n")
            for i in range(100000):
                f.write(f"{i}|Name{i}|Value{i}\n")

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(large_csv)

        assert result.is_valid is True
        assert result.row_count == 100000
        # Should process without loading entire file into memory

    def test_gzip_file_parsing(self, temp_dir: Path):
        """Test parsing of gzipped CSV files."""
        import gzip
        from api.services.parser import CSVParser

        gz_path = temp_dir / "test.csv.gz"
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            f.write("ID|Name\n")
            f.write("1|Alice\n")
            f.write("2|Bob\n")

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(gz_path)

        assert result.is_valid is True
        assert result.header == ["ID", "Name"]
        assert result.row_count == 2

    def test_parser_tracks_row_numbers(self, sample_csv_basic: Path):
        """Test that parser tracks row numbers for error reporting."""
        from api.services.parser import CSVParser

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(sample_csv_basic)

        for row in result.rows:
            assert hasattr(row, "row_number")
            assert row.row_number > 0

    def test_parser_provides_raw_line_access(self, sample_csv_basic: Path):
        """Test that parser can provide raw line for error context."""
        from api.services.parser import CSVParser

        parser = CSVParser(delimiter="|", include_raw_lines=True)
        result = parser.parse_file(sample_csv_basic)

        for row in result.rows:
            assert hasattr(row, "raw_line")
            assert isinstance(row.raw_line, str)
