"""
UTF-8 validation tests.

Tests the UTF-8 stream validator that must:
- Accept valid UTF-8 byte sequences
- Reject invalid UTF-8 at the first bad byte (catastrophic error)
- Report the exact byte offset of the failure
"""

import pytest
from io import BytesIO
from services.ingest import UTF8Validator


class TestUTF8Validator:
    """Test UTF-8 validation with streaming."""

    def test_valid_ascii(self):
        """Valid ASCII text should pass."""
        data = b"Hello, World!\n"
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is True
        assert result.error is None
        assert result.byte_offset is None

    def test_valid_utf8_multibyte(self):
        """Valid UTF-8 with multibyte characters should pass."""
        data = "Hello 世界 🌍\n".encode('utf-8')
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is True
        assert result.error is None

    def test_invalid_utf8_first_byte(self):
        """Invalid UTF-8 at first byte should fail immediately."""
        # 0xFF is invalid start byte in UTF-8
        data = b'\xFF\x00\x00'
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is False
        assert result.byte_offset == 0
        assert "Invalid UTF-8" in result.error

    def test_invalid_utf8_middle(self):
        """Invalid UTF-8 in the middle should fail at exact position."""
        # Valid UTF-8 followed by invalid byte
        data = b"Hello\xFF World"
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is False
        assert result.byte_offset == 5
        assert "byte 5" in result.error.lower()

    def test_invalid_continuation_byte(self):
        """Invalid UTF-8 continuation sequence should fail."""
        # Start of 2-byte sequence but invalid continuation
        data = b"Hello\xC0\xFF"
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is False
        assert result.byte_offset >= 5

    def test_truncated_multibyte(self):
        """Truncated multibyte sequence should fail."""
        # Start of 3-byte sequence but truncated
        data = b"Hello\xE0\xA0"  # Missing third byte
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is False

    def test_empty_stream(self):
        """Empty stream should be valid."""
        stream = BytesIO(b"")
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is True

    def test_large_valid_stream(self):
        """Large valid UTF-8 stream should pass efficiently."""
        # Generate 1MB of valid UTF-8
        data = ("Hello 世界 " * 100000).encode('utf-8')
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is True

    def test_streaming_validation(self):
        """Validator should work in streaming mode with chunks."""
        data = "Hello 世界\n" * 1000
        stream = BytesIO(data.encode('utf-8'))
        validator = UTF8Validator(stream, chunk_size=1024)

        result = validator.validate()
        assert result.is_valid is True

    def test_bom_handling(self):
        """UTF-8 BOM should be handled correctly."""
        # UTF-8 BOM is EF BB BF
        data = b'\xef\xbb\xbfHello World'
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is True
        # BOM should be stripped or noted
        assert hasattr(result, 'has_bom')

    def test_null_bytes(self):
        """Null bytes in valid UTF-8 should pass."""
        data = b"Hello\x00World"
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        assert result.is_valid is True

    def test_overlong_encoding(self):
        """Overlong UTF-8 encoding should be rejected."""
        # Overlong encoding of '/' (should be 2F, not C0 AF)
        data = b"Hello\xC0\xAF"
        stream = BytesIO(data)
        validator = UTF8Validator(stream)

        result = validator.validate()
        # Modern UTF-8 validators reject overlong sequences
        assert result.is_valid is False
