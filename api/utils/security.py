"""
Security utilities for VQ8 Data Profiler.

Provides sanitization, validation, and protection functions.
"""

import gzip
import logging
import os
import re
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.

    Removes directory separators and dangerous characters.

    Args:
        filename: Original filename from user input

    Returns:
        Sanitized filename safe for file system operations
    """
    if not filename:
        return "uploaded_file"

    # Get basename only (removes any path components)
    safe_name = os.path.basename(filename)

    # Ensure it's not empty or a directory reference before further processing
    if not safe_name or safe_name in ['.', '..']:
        return "uploaded_file"

    # Remove null bytes
    safe_name = safe_name.replace('\x00', '')

    # Replace path separators and other dangerous chars
    dangerous_chars = ['..', '/', '\\', '\n', '\r', '\t']
    for char in dangerous_chars:
        safe_name = safe_name.replace(char, '_')

    # Ensure it's not empty after sanitization
    if not safe_name:
        return "uploaded_file"

    # Limit length
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:255 - len(ext)] + ext

    return safe_name


def safe_gzip_decompress(
    compressed_data: bytes,
    max_size: int = 10 * 1024 * 1024 * 1024
) -> bytes:
    """
    Safely decompress gzip data with size limit to prevent decompression bombs.

    Args:
        compressed_data: Gzipped bytes
        max_size: Maximum allowed decompressed size (default 10GB)

    Returns:
        Decompressed bytes

    Raises:
        HTTPException: If decompressed size exceeds limit or gzip is invalid
    """
    decompressed = BytesIO()
    bytes_written = 0

    try:
        with gzip.GzipFile(fileobj=BytesIO(compressed_data)) as gz:
            while True:
                chunk = gz.read(65536)  # 64KB chunks
                if not chunk:
                    break

                bytes_written += len(chunk)
                if bytes_written > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Decompressed file exceeds maximum allowed size (gzip bomb protection)"
                    )

                decompressed.write(chunk)

        return decompressed.getvalue()
    except (gzip.BadGzipFile, OSError, EOFError, Exception) as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid gzip file"
        )


def safe_pattern_match(
    pattern: re.Pattern,
    value: str,
    max_length: int = 256
) -> bool:
    """
    Safely match pattern with length check to prevent ReDoS.

    Args:
        pattern: Compiled regex pattern
        value: String to match
        max_length: Maximum string length to attempt match

    Returns:
        True if pattern matches, False otherwise
    """
    if len(value) > max_length:
        return False

    try:
        return bool(pattern.match(value))
    except (re.error, RecursionError):
        return False


def sanitize_for_logging(value: str, max_length: int = 256) -> str:
    """
    Sanitize string values for logging to prevent log injection.

    Removes control characters and newlines that could forge log entries.

    Args:
        value: String to sanitize
        max_length: Maximum length to allow

    Returns:
        Sanitized string safe for logging
    """
    if not value:
        return ""

    # Remove control characters and newlines
    sanitized = ''.join(
        char if ord(char) >= 32 else ' '
        for char in value
    )

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


def sanitize_error_message(error: Exception, user_message: str) -> str:
    """
    Sanitize error messages to prevent information leakage.

    In production, returns only the user-friendly message.
    In development, includes sanitized error details.

    Args:
        error: Original exception
        user_message: User-friendly message

    Returns:
        Sanitized error message
    """
    # Log full error internally
    logger.error("Error: %s", str(error), exc_info=True)

    # In production, only return generic message
    if os.getenv("ENVIRONMENT") == "production":
        return user_message

    # In development, include sanitized details
    error_str = str(error)
    # Remove absolute paths
    error_str = error_str.replace(str(Path.cwd()), "<app>")
    error_str = error_str.replace(str(Path.home()), "<home>")

    return f"{user_message}: {error_str}"
