"""
UTF-8 validation and ingest services.

This module provides streaming UTF-8 validation for uploaded files.
"""

import csv
from dataclasses import dataclass, field
from enum import Enum
from io import StringIO, TextIOWrapper
from typing import BinaryIO, Optional, Iterator, List


class LineEndingStyle(Enum):
    """Line ending styles."""
    CRLF = "CRLF"  # Windows: \r\n
    LF = "LF"      # Unix/Linux/Mac: \n
    CR = "CR"      # Legacy Mac: \r
    UNKNOWN = "UNKNOWN"  # No line endings detected


@dataclass
class ValidationResult:
    """Result of UTF-8 validation."""
    is_valid: bool
    error: Optional[str] = None
    byte_offset: Optional[int] = None
    has_bom: bool = False


@dataclass
class LineEndingResult:
    """Result of line ending detection."""
    style: LineEndingStyle
    original_style: str
    mixed: bool = False
    sample_count: int = 0
    crlf_count: int = 0
    lf_count: int = 0
    cr_count: int = 0
    warnings: List[str] = field(default_factory=list)

    @property
    def detected_style(self) -> str:
        """Alias for original_style for backward compatibility."""
        return self.original_style

    @property
    def has_mixed(self) -> bool:
        """Alias for mixed for backward compatibility."""
        return self.mixed

    @property
    def lf_only_count(self) -> int:
        """Alias for lf_count for backward compatibility."""
        return self.lf_count

    @property
    def cr_only_count(self) -> int:
        """Alias for cr_count for backward compatibility."""
        return self.cr_count

    @property
    def total_lines(self) -> int:
        """Total line count (sum of all line ending types)."""
        return self.crlf_count + self.lf_count + self.cr_count

    def to_audit_dict(self) -> dict:
        """Convert to dictionary for audit trail."""
        return {
            'original_style': self.original_style,
            'normalized_to': 'LF',
            'mixed': self.mixed,
            'sample_count': self.sample_count,
            'crlf_count': self.crlf_count,
            'lf_count': self.lf_count,
            'cr_count': self.cr_count
        }


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


class CRLFDetector:
    """
    Stream-based CRLF/line ending detector and normalizer.

    Detects line ending patterns (CRLF, LF, CR) and normalizes to LF for internal processing.
    Records original format for audit trail.
    """

    def __init__(
        self,
        stream: BinaryIO,
        chunk_size: int = 8192,
        sample_size: Optional[int] = None,
        quoted_aware: bool = False
    ):
        """
        Initialize detector.

        Args:
            stream: Binary stream to analyze
            chunk_size: Size of chunks to read (default 8KB)
            sample_size: Maximum number of line endings to sample (None = all)
            quoted_aware: Whether to be aware of quoted fields in CSV (experimental)
        """
        self.stream = stream
        self.chunk_size = chunk_size
        self.sample_size = sample_size
        self.quoted_aware = quoted_aware
        self._content: Optional[bytes] = None

    def detect(self) -> LineEndingResult:
        """
        Detect line ending style in the stream.

        Returns:
            LineEndingResult with detected style and statistics
        """
        self.stream.seek(0)

        crlf_count = 0
        lf_count = 0
        cr_count = 0
        in_quotes = False
        prev_byte = None
        sample_count = 0

        while True:
            chunk = self.stream.read(self.chunk_size)
            if not chunk:
                break

            for i, byte in enumerate(chunk):
                # Simple quote tracking for CSV (experimental)
                if self.quoted_aware and byte == ord(b'"'):
                    in_quotes = not in_quotes

                # Skip line endings inside quotes if quote-aware
                if self.quoted_aware and in_quotes:
                    prev_byte = byte
                    continue

                # Detect line endings
                if byte == ord(b'\n'):
                    if prev_byte == ord(b'\r'):
                        # This is part of CRLF, already counted
                        pass
                    else:
                        # Standalone LF
                        lf_count += 1
                        sample_count += 1
                elif byte == ord(b'\r'):
                    # Look ahead to see if it's CRLF or CR
                    next_byte = chunk[i + 1] if i + 1 < len(chunk) else None
                    if next_byte is None and i + 1 == len(chunk):
                        # Need to peek at next chunk
                        pos = self.stream.tell()
                        peek = self.stream.read(1)
                        self.stream.seek(pos)
                        next_byte = peek[0] if peek else None

                    if next_byte == ord(b'\n'):
                        crlf_count += 1
                        sample_count += 1
                    else:
                        cr_count += 1
                        sample_count += 1

                prev_byte = byte

                # Stop if we've sampled enough
                if self.sample_size and sample_count >= self.sample_size:
                    break

            if self.sample_size and sample_count >= self.sample_size:
                break

        # Determine predominant style
        if sample_count == 0:
            style = LineEndingStyle.UNKNOWN
            original_style = "NONE"
        elif crlf_count > lf_count and crlf_count > cr_count:
            style = LineEndingStyle.CRLF
            original_style = "CRLF"
        elif lf_count > crlf_count and lf_count > cr_count:
            style = LineEndingStyle.LF
            original_style = "LF"
        elif cr_count > crlf_count and cr_count > lf_count:
            style = LineEndingStyle.CR
            original_style = "CR"
        elif crlf_count > 0 or lf_count > 0 or cr_count > 0:
            # Mixed, pick the most common
            if crlf_count >= lf_count and crlf_count >= cr_count:
                style = LineEndingStyle.CRLF
                original_style = "CRLF"
            elif lf_count >= crlf_count and lf_count >= cr_count:
                style = LineEndingStyle.LF
                original_style = "LF"
            else:
                style = LineEndingStyle.CR
                original_style = "CR"
        else:
            style = LineEndingStyle.UNKNOWN
            original_style = "NONE"

        # Check if mixed
        endings_present = sum([
            1 if crlf_count > 0 else 0,
            1 if lf_count > 0 else 0,
            1 if cr_count > 0 else 0
        ])
        mixed = endings_present > 1

        # Generate warnings for mixed line endings
        warnings = []
        if mixed:
            warnings.append(
                f"Mixed line endings detected: {crlf_count} CRLF, {lf_count} LF, {cr_count} CR"
            )

        return LineEndingResult(
            style=style,
            original_style=original_style,
            mixed=mixed,
            sample_count=sample_count,
            crlf_count=crlf_count,
            lf_count=lf_count,
            cr_count=cr_count,
            warnings=warnings
        )

    def normalize(self) -> bytes:
        """
        Normalize all line endings to LF.

        Returns:
            Content with all line endings normalized to LF
        """
        # Read entire content if not already cached
        if self._content is None:
            self.stream.seek(0)
            self._content = self.stream.read()

        # Normalize: CRLF -> LF, then CR -> LF
        normalized = self._content.replace(b'\r\n', b'\n')  # CRLF to LF
        normalized = normalized.replace(b'\r', b'\n')       # CR to LF

        return normalized


@dataclass
class ParserConfig:
    """Configuration for CSV parser."""
    delimiter: str = '|'
    quoting: bool = True
    has_header: bool = True
    continue_on_error: bool = False


@dataclass
class ParserResult:
    """Result of header parsing."""
    success: bool
    headers: List[str]
    column_count: int
    error: Optional[str] = None


class ParserError(Exception):
    """
    CSV parser error.

    Can be catastrophic (must stop processing) or non-catastrophic (can continue).
    """

    def __init__(
        self,
        message: str,
        code: str,
        is_catastrophic: bool = False,
        line_number: Optional[int] = None
    ):
        """
        Initialize parser error.

        Args:
            message: Error message
            code: Error code (e.g., E_JAGGED_ROW, E_HEADER_MISSING)
            is_catastrophic: Whether this error should stop processing
            line_number: Line number where error occurred (if applicable)
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.is_catastrophic = is_catastrophic
        self.line_number = line_number

    def __str__(self) -> str:
        """String representation of error."""
        parts = [self.message]
        if self.line_number is not None:
            parts.append(f"(line {self.line_number})")
        return " ".join(parts)


class CSVParser:
    """
    Stream-based CSV parser with constant column count enforcement.

    Parses CSV files with configurable delimiters and quoting rules.
    Enforces that all rows have the same number of columns as the header.
    """

    def __init__(
        self,
        stream,
        config: ParserConfig
    ):
        """
        Initialize CSV parser.

        Args:
            stream: Text stream (StringIO or TextIOWrapper) to parse
            config: Parser configuration
        """
        self.stream = stream
        self.config = config
        self.headers: List[str] = []
        self.column_count: int = 0
        self.line_number: int = 0
        self.errors: List[ParserError] = []

        # Configure CSV reader based on quoting setting
        if config.quoting:
            self.quoting = csv.QUOTE_MINIMAL
        else:
            self.quoting = csv.QUOTE_NONE

    def parse_header(self) -> ParserResult:
        """
        Parse and validate the CSV header.

        Returns:
            ParserResult with header information

        Raises:
            ParserError: If header is missing or file is empty (catastrophic)
        """
        # Reset stream to beginning
        self.stream.seek(0)

        # Create CSV reader
        reader = csv.reader(
            self.stream,
            delimiter=self.config.delimiter,
            quotechar='"',
            quoting=self.quoting,
            skipinitialspace=False,
            strict=False  # We'll handle errors ourselves
        )

        try:
            # Read first row as header
            self.headers = next(reader)
            self.line_number = 1
        except StopIteration:
            # Empty file
            raise ParserError(
                "File is empty or header is missing",
                code="E_HEADER_MISSING",
                is_catastrophic=True
            )
        except csv.Error as e:
            # CSV parsing error in header
            raise ParserError(
                f"Error parsing header: {str(e)}",
                code="E_HEADER_MISSING",
                is_catastrophic=True
            )

        # Check if we have a header
        if not self.config.has_header:
            raise ParserError(
                "Header is required but has_header is False",
                code="E_HEADER_MISSING",
                is_catastrophic=True
            )

        # Check if header is empty
        if not self.headers or all(h == '' for h in self.headers):
            raise ParserError(
                "Header row is empty",
                code="E_HEADER_MISSING",
                is_catastrophic=True
            )

        self.column_count = len(self.headers)

        return ParserResult(
            success=True,
            headers=self.headers,
            column_count=self.column_count
        )

    def parse_rows(self) -> Iterator[List[str]]:
        """
        Parse data rows from the CSV file.

        Yields rows as lists of strings. Enforces constant column count.

        Yields:
            List[str]: Row data

        Raises:
            ParserError: If row has inconsistent column count (catastrophic)
        """
        if not self.headers:
            raise ParserError(
                "Must call parse_header() before parse_rows()",
                code="E_HEADER_MISSING",
                is_catastrophic=True
            )

        # Create CSV reader at current position (after header)
        if self.config.quoting:
            reader = csv.reader(
                self.stream,
                delimiter=self.config.delimiter,
                quotechar='"',
                quoting=self.quoting,
                skipinitialspace=False,
                strict=True  # Strict mode to catch quote errors
            )
        else:
            reader = csv.reader(
                self.stream,
                delimiter=self.config.delimiter,
                quoting=csv.QUOTE_NONE,
                skipinitialspace=False,
                strict=False
            )

        row_number = 0  # Track data row number (0-indexed after header)
        while True:
            try:
                row = next(reader)
                row_number += 1
                # Line number in file = row number + 1 (for header)
                file_line = row_number + 1

                # Strip trailing empty fields if they exceed column count
                # This handles cases like "a|b|c|" which creates ['a','b','c','']
                while len(row) > self.column_count and row[-1] == '':
                    row = row[:-1]

                # Check column count (catastrophic if wrong)
                if len(row) != self.column_count:
                    # If we have exactly 1 extra column and quoting is enabled, likely unquoted delimiter
                    # If we have many extra columns, it's just jagged
                    if len(row) == self.column_count + 1 and self.config.quoting:
                        error = ParserError(
                            f"Row has {len(row)} columns but expected {self.column_count} - possible unquoted delimiter",
                            code="E_UNQUOTED_DELIM",
                            is_catastrophic=False,  # Non-catastrophic for unquoted delimiters
                            line_number=row_number
                        )
                    else:
                        error = ParserError(
                            f"Row has {len(row)} columns but expected {self.column_count}",
                            code="E_JAGGED_ROW",
                            is_catastrophic=True,
                            line_number=row_number
                        )

                    if self.config.continue_on_error:
                        self.errors.append(error)
                        continue
                    else:
                        raise error

                yield row

            except StopIteration:
                # End of file
                break

            except csv.Error as e:
                row_number += 1  # Increment for the errored row
                # CSV module detected a quote error
                error_msg = str(e).lower()
                if 'quote' in error_msg or 'delimiter' in error_msg:
                    error = ParserError(
                        f"CSV quoting or delimiter error: {str(e)}",
                        code="E_QUOTE_RULE",
                        is_catastrophic=False,
                        line_number=row_number
                    )
                else:
                    error = ParserError(
                        f"CSV parsing error: {str(e)}",
                        code="E_QUOTE_RULE",
                        is_catastrophic=False,
                        line_number=row_number
                    )

                if self.config.continue_on_error:
                    self.errors.append(error)
                    continue
                else:
                    raise error

    def _validate_quoting(self, row: List[str]) -> None:
        """
        Validate quoting rules for a row.

        Args:
            row: Row to validate

        Raises:
            ParserError: If quoting rules are violated (non-catastrophic)
        """
        # Note: The csv module handles most quoting validation automatically.
        # We'll detect issues by checking for parsing problems.
        # More sophisticated validation could be added here if needed.
        pass

    def get_errors(self) -> List[ParserError]:
        """
        Get accumulated non-catastrophic errors.

        Returns:
            List of ParserError objects
        """
        return self.errors

    def get_error_rollup(self) -> dict:
        """
        Get error counts rolled up by error code.

        Returns:
            Dictionary mapping error codes to counts
        """
        rollup = {}
        for error in self.errors:
            rollup[error.code] = rollup.get(error.code, 0) + 1
        return rollup
