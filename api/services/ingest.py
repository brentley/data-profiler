"""
UTF-8 validation and ingest services.

This module provides streaming UTF-8 validation for uploaded files.
"""

from dataclasses import dataclass
from typing import BinaryIO, Optional


@dataclass
class ValidationResult:
    """Result of UTF-8 validation."""
    is_valid: bool
    error: Optional[str] = None
    byte_offset: Optional[int] = None
    has_bom: bool = False


class UTF8Validator:
    """
    Stream-based UTF-8 validator.

    Validates UTF-8 encoding without loading the entire file into memory.
    Stops at the first invalid byte and reports its exact offset.
    """

    # UTF-8 BOM (Byte Order Mark)
    BOM = b'\xef\xbb\xbf'

    def __init__(self, stream: BinaryIO, chunk_size: int = 8192):
        """
        Initialize validator.

        Args:
            stream: Binary stream to validate
            chunk_size: Size of chunks to read (default 8KB)
        """
        self.stream = stream
        self.chunk_size = chunk_size

    def validate(self) -> ValidationResult:
        """
        Validate UTF-8 encoding of the stream.

        Returns:
            ValidationResult with validation status and error details
        """
        byte_offset = 0
        has_bom = False
        pending_bytes = b''

        # Reset stream to beginning
        self.stream.seek(0)

        # Check for BOM at start
        first_chunk = self.stream.read(3)
        if first_chunk.startswith(self.BOM):
            has_bom = True
            byte_offset = 3
            # If chunk is exactly BOM, read more
            if len(first_chunk) == 3:
                first_chunk = self.stream.read(self.chunk_size)
            else:
                first_chunk = first_chunk[3:]

        # Reset stream and skip BOM if present
        self.stream.seek(0)
        if has_bom:
            self.stream.read(3)  # Skip BOM

        # Process stream in chunks
        while True:
            chunk = self.stream.read(self.chunk_size)
            if not chunk:
                # Check if we have pending bytes at EOF
                if pending_bytes:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Truncated UTF-8 sequence at byte {byte_offset - len(pending_bytes)}",
                        byte_offset=byte_offset - len(pending_bytes)
                    )
                break

            # Combine pending bytes from previous chunk with new chunk
            data = pending_bytes + chunk

            i = 0
            while i < len(data):
                byte = data[i]

                # Determine sequence length
                if byte < 0x80:
                    # 1-byte sequence (ASCII)
                    seq_len = 1
                elif byte < 0xC0:
                    # Invalid start byte (continuation byte)
                    return ValidationResult(
                        is_valid=False,
                        error=f"Invalid UTF-8 start byte at byte {byte_offset + i}",
                        byte_offset=byte_offset + i
                    )
                elif byte < 0xE0:
                    # 2-byte sequence
                    seq_len = 2
                elif byte < 0xF0:
                    # 3-byte sequence
                    seq_len = 3
                elif byte < 0xF8:
                    # 4-byte sequence
                    seq_len = 4
                else:
                    # Invalid start byte (>= 0xF8)
                    return ValidationResult(
                        is_valid=False,
                        error=f"Invalid UTF-8 start byte at byte {byte_offset + i}",
                        byte_offset=byte_offset + i
                    )

                # Check if we have enough bytes for the sequence
                if i + seq_len > len(data):
                    # Not enough bytes in this chunk, save for next iteration
                    pending_bytes = data[i:]
                    break

                # Validate the sequence
                sequence = data[i:i+seq_len]
                error = self._validate_sequence(sequence, byte_offset + i)
                if error:
                    return error

                i += seq_len
            else:
                # Processed all bytes in this chunk
                pending_bytes = b''

            byte_offset += len(data) - len(pending_bytes)

        return ValidationResult(is_valid=True, has_bom=has_bom)

    def _validate_sequence(self, sequence: bytes, offset: int) -> Optional[ValidationResult]:
        """
        Validate a UTF-8 sequence.

        Args:
            sequence: Bytes to validate
            offset: Byte offset of the sequence start

        Returns:
            ValidationResult if invalid, None if valid
        """
        if len(sequence) == 1:
            # ASCII, already validated
            return None

        first_byte = sequence[0]

        # Validate continuation bytes
        for i in range(1, len(sequence)):
            byte = sequence[i]
            if not (0x80 <= byte < 0xC0):
                return ValidationResult(
                    is_valid=False,
                    error=f"Invalid UTF-8 continuation byte at byte {offset + i}",
                    byte_offset=offset + i
                )

        # Check for overlong encodings
        if len(sequence) == 2:
            # 2-byte sequence: 110xxxxx 10xxxxxx
            # Valid range: U+0080 to U+07FF
            code_point = ((first_byte & 0x1F) << 6) | (sequence[1] & 0x3F)
            if code_point < 0x80:
                return ValidationResult(
                    is_valid=False,
                    error=f"Overlong UTF-8 encoding at byte {offset}",
                    byte_offset=offset
                )
        elif len(sequence) == 3:
            # 3-byte sequence: 1110xxxx 10xxxxxx 10xxxxxx
            # Valid range: U+0800 to U+FFFF
            code_point = ((first_byte & 0x0F) << 12) | \
                        ((sequence[1] & 0x3F) << 6) | \
                        (sequence[2] & 0x3F)
            if code_point < 0x800:
                return ValidationResult(
                    is_valid=False,
                    error=f"Overlong UTF-8 encoding at byte {offset}",
                    byte_offset=offset
                )
            # Check for surrogate pairs (invalid in UTF-8)
            if 0xD800 <= code_point <= 0xDFFF:
                return ValidationResult(
                    is_valid=False,
                    error=f"Invalid UTF-8 surrogate pair at byte {offset}",
                    byte_offset=offset
                )
        elif len(sequence) == 4:
            # 4-byte sequence: 11110xxx 10xxxxxx 10xxxxxx 10xxxxxx
            # Valid range: U+10000 to U+10FFFF
            code_point = ((first_byte & 0x07) << 18) | \
                        ((sequence[1] & 0x3F) << 12) | \
                        ((sequence[2] & 0x3F) << 6) | \
                        (sequence[3] & 0x3F)
            if code_point < 0x10000:
                return ValidationResult(
                    is_valid=False,
                    error=f"Overlong UTF-8 encoding at byte {offset}",
                    byte_offset=offset
                )
            if code_point > 0x10FFFF:
                return ValidationResult(
                    is_valid=False,
                    error=f"Invalid UTF-8 code point at byte {offset}",
                    byte_offset=offset
                )

        return None
