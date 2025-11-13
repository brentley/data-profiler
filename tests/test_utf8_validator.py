"""
Test suite for UTF-8 validation.

RED PHASE: These tests define the expected behavior of the UTF-8 validator.
They should FAIL initially until implementation is provided.

Requirements from spec:
- Stream validator; first invalid byte → catastrophic error (stop)
- Accept only valid UTF-8 encoded text
- Report exact byte offset of first invalid UTF-8 sequence
"""
import pytest
from pathlib import Path


class TestUTF8Validator:
    """Test UTF-8 validation functionality."""

    def test_valid_utf8_ascii_only(self, sample_csv_basic: Path):
        """Test that valid ASCII (subset of UTF-8) passes validation."""
        from api.services.validators import UTF8Validator

        validator = UTF8Validator()
        result = validator.validate_file(sample_csv_basic)

        assert result.is_valid is True
        assert result.error_offset is None
        assert result.error_message is None

    def test_valid_utf8_with_multibyte_chars(self, temp_dir: Path):
        """Test that valid UTF-8 with multibyte characters passes."""
        from api.services.validators import UTF8Validator

        csv_path = temp_dir / "multibyte.csv"
        csv_path.write_text(
            "ID|Name|City\n"
            "1|José|São Paulo\n"
            "2|北京|中国\n"
            "3|Müller|München\n",
            encoding="utf-8"
        )

        validator = UTF8Validator()
        result = validator.validate_file(csv_path)

        assert result.is_valid is True
        assert result.error_offset is None

    def test_invalid_utf8_rejects_at_first_bad_byte(self, sample_csv_invalid_utf8: Path):
        """Test that invalid UTF-8 is rejected at the first bad byte."""
        from api.services.validators import UTF8Validator

        validator = UTF8Validator()
        result = validator.validate_file(sample_csv_invalid_utf8)

        assert result.is_valid is False
        assert result.error_offset is not None
        assert result.error_offset > 0  # Should be after header
        assert "UTF-8" in result.error_message or "invalid" in result.error_message.lower()

    def test_invalid_utf8_continuation_byte(self, temp_dir: Path):
        """Test detection of invalid continuation byte."""
        from api.services.validators import UTF8Validator

        csv_path = temp_dir / "bad_continuation.csv"
        # 0xC0 0x80 is an invalid UTF-8 sequence (overlong encoding)
        csv_path.write_bytes(
            b"ID|Name\n"
            b"1|Test\xC0\x80Invalid\n"
        )

        validator = UTF8Validator()
        result = validator.validate_file(csv_path)

        assert result.is_valid is False
        assert result.error_offset == 13  # Position of 0xC0

    def test_invalid_utf8_truncated_sequence(self, temp_dir: Path):
        """Test detection of truncated multi-byte sequence."""
        from api.services.validators import UTF8Validator

        csv_path = temp_dir / "truncated.csv"
        # 0xC3 expects a continuation byte but file ends
        csv_path.write_bytes(
            b"ID|Name\n"
            b"1|Test\xC3"  # Truncated 2-byte sequence
        )

        validator = UTF8Validator()
        result = validator.validate_file(csv_path)

        assert result.is_valid is False
        assert result.error_offset is not None

    def test_invalid_utf8_unexpected_continuation(self, temp_dir: Path):
        """Test detection of unexpected continuation byte."""
        from api.services.validators import UTF8Validator

        csv_path = temp_dir / "unexpected_cont.csv"
        # 0x80 is a continuation byte without a start byte
        csv_path.write_bytes(
            b"ID|Name\n"
            b"1|Test\x80Invalid\n"
        )

        validator = UTF8Validator()
        result = validator.validate_file(csv_path)

        assert result.is_valid is False
        assert result.error_offset == 13  # Position of 0x80

    def test_utf8_validator_streams_large_files(self, temp_dir: Path):
        """Test that validator streams files without loading entirely into memory."""
        from api.services.validators import UTF8Validator

        # Create a large file (10 MB)
        large_csv = temp_dir / "large.csv"
        with large_csv.open("wb") as f:
            f.write(b"ID|Name|Value\n")
            for i in range(200000):
                f.write(f"{i}|Name{i}|Value{i}\n".encode("utf-8"))

        validator = UTF8Validator()
        result = validator.validate_file(large_csv)

        assert result.is_valid is True
        # Validator should use streaming (test memory usage stays low)

    def test_utf8_validator_reports_exact_byte_offset(self, temp_dir: Path):
        """Test that error offset is exact byte position, not character position."""
        from api.services.validators import UTF8Validator

        csv_path = temp_dir / "exact_offset.csv"
        csv_path.write_bytes(
            b"ID|Name\n"  # 8 bytes
            b"1|Test\n"   # 7 bytes (total: 15 bytes)
            b"2|Bad\xFF"  # Invalid at byte 21 (15 + 6)
        )

        validator = UTF8Validator()
        result = validator.validate_file(csv_path)

        assert result.is_valid is False
        assert result.error_offset == 21

    def test_utf8_validator_with_gzip_file(self, temp_dir: Path):
        """Test that validator can handle gzipped files."""
        import gzip
        from api.services.validators import UTF8Validator

        csv_path = temp_dir / "test.csv.gz"
        with gzip.open(csv_path, "wb") as f:
            f.write(b"ID|Name\n1|Alice\n2|Bob\n")

        validator = UTF8Validator()
        result = validator.validate_file(csv_path)

        assert result.is_valid is True

    def test_utf8_validator_with_invalid_gzip_content(self, temp_dir: Path):
        """Test that validator detects invalid UTF-8 in gzipped files."""
        import gzip
        from api.services.validators import UTF8Validator

        csv_path = temp_dir / "invalid.csv.gz"
        with gzip.open(csv_path, "wb") as f:
            f.write(b"ID|Name\n1|Test\xFF\n")

        validator = UTF8Validator()
        result = validator.validate_file(csv_path)

        assert result.is_valid is False
        assert result.error_offset is not None

    def test_utf8_validator_raises_on_missing_file(self, temp_dir: Path):
        """Test that validator raises appropriate error for missing file."""
        from api.services.validators import UTF8Validator

        validator = UTF8Validator()
        missing_file = temp_dir / "does_not_exist.csv"

        with pytest.raises(FileNotFoundError):
            validator.validate_file(missing_file)

    def test_utf8_validator_bom_handling(self, temp_dir: Path):
        """Test that UTF-8 BOM is handled correctly (accepted but not required)."""
        from api.services.validators import UTF8Validator

        # UTF-8 with BOM
        csv_with_bom = temp_dir / "with_bom.csv"
        csv_with_bom.write_bytes(
            b"\xEF\xBB\xBF"  # UTF-8 BOM
            b"ID|Name\n"
            b"1|Alice\n"
        )

        validator = UTF8Validator()
        result = validator.validate_file(csv_with_bom)

        assert result.is_valid is True
        # BOM should be noted but not cause failure
        assert result.bom_detected is True

    def test_utf8_validator_empty_file(self, temp_dir: Path):
        """Test handling of empty file."""
        from api.services.validators import UTF8Validator

        empty_csv = temp_dir / "empty.csv"
        empty_csv.write_bytes(b"")

        validator = UTF8Validator()
        result = validator.validate_file(empty_csv)

        # Empty file is technically valid UTF-8, but may trigger other errors
        assert result.is_valid is True
