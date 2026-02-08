"""
Security tests for VQ8 Data Profiler.

Tests all security utility functions and their integrations.
"""

import gzip
import os
import re
import pytest
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from api.utils.security import (
    sanitize_filename,
    safe_gzip_decompress,
    safe_pattern_match,
    sanitize_for_logging,
    sanitize_error_message,
)


class TestSanitizeFilename:
    """Tests for sanitize_filename - prevents path traversal attacks."""

    def test_normal_filename(self):
        assert sanitize_filename("data.csv") == "data.csv"
        assert sanitize_filename("report_2024.txt") == "report_2024.txt"
        assert sanitize_filename("my-file.txt.gz") == "my-file.txt.gz"

    def test_empty_returns_default(self):
        assert sanitize_filename("") == "uploaded_file"

    def test_none_returns_default(self):
        assert sanitize_filename(None) == "uploaded_file"

    def test_dot_returns_default(self):
        assert sanitize_filename(".") == "uploaded_file"

    def test_double_dot_returns_default(self):
        assert sanitize_filename("..") == "uploaded_file"

    def test_unix_path_traversal_basename(self):
        # os.path.basename extracts just the last component
        assert sanitize_filename("../etc/passwd") == "passwd"
        assert sanitize_filename("../../secrets.txt") == "secrets.txt"
        assert sanitize_filename("../../../etc/shadow") == "shadow"

    def test_absolute_unix_path(self):
        assert sanitize_filename("/etc/passwd") == "passwd"
        assert sanitize_filename("/var/log/system.log") == "system.log"

    def test_null_byte_removal(self):
        assert "\x00" not in sanitize_filename("file\x00.csv")
        assert "\x00" not in sanitize_filename("\x00hidden.txt")

    def test_newline_tab_replacement(self):
        result = sanitize_filename("file\nname.csv")
        assert "\n" not in result
        result = sanitize_filename("file\rname.csv")
        assert "\r" not in result
        result = sanitize_filename("file\tname.csv")
        assert "\t" not in result

    def test_double_dot_in_name_replaced(self):
        # ".." inside a filename (not as path) gets replaced with "__"
        result = sanitize_filename("file..name.csv")
        assert ".." not in result

    def test_length_limit(self):
        long_name = "a" * 300 + ".csv"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".csv")

    def test_unicode_preserved(self):
        assert sanitize_filename("données.csv") == "données.csv"
        assert sanitize_filename("文件.txt") == "文件.txt"

    def test_hidden_files_preserved(self):
        assert sanitize_filename(".gitignore") == ".gitignore"
        assert sanitize_filename(".env") == ".env"

    def test_result_has_no_path_separators(self):
        """After sanitization, no path separators should remain."""
        dangerous_names = [
            "../../../etc/passwd.csv",
            "/var/log/test.csv",
            "test/../../../etc.csv",
        ]
        for name in dangerous_names:
            result = sanitize_filename(name)
            assert "/" not in result
            assert ".." not in result


class TestSafeGzipDecompress:
    """Tests for safe_gzip_decompress - prevents gzip bomb attacks."""

    def test_normal_decompression(self):
        original = b"This is test data that will be compressed"
        compressed = gzip.compress(original)
        result = safe_gzip_decompress(compressed)
        assert result == original

    def test_empty_data(self):
        compressed = gzip.compress(b"")
        result = safe_gzip_decompress(compressed)
        assert result == b""

    def test_large_valid_data(self):
        original = b"x" * (1024 * 1024)  # 1MB
        compressed = gzip.compress(original)
        result = safe_gzip_decompress(compressed)
        assert result == original

    def test_gzip_bomb_rejected(self):
        """Data exceeding max_size is rejected."""
        original = b"a" * 10000  # 10KB
        compressed = gzip.compress(original)

        with pytest.raises(HTTPException) as exc_info:
            safe_gzip_decompress(compressed, max_size=1024)  # 1KB limit
        assert exc_info.value.status_code == 413

    def test_invalid_gzip_data(self):
        with pytest.raises(HTTPException) as exc_info:
            safe_gzip_decompress(b"This is not gzip data")
        assert exc_info.value.status_code == 400

    def test_corrupted_gzip_data(self):
        original = b"test data"
        compressed = gzip.compress(original)
        corrupted = compressed[:10] + b"CORRUPTED" + compressed[20:]
        with pytest.raises(HTTPException):
            safe_gzip_decompress(corrupted)

    def test_custom_max_size(self):
        original = b"x" * 5000
        compressed = gzip.compress(original)

        # Should succeed with 10KB limit
        result = safe_gzip_decompress(compressed, max_size=10000)
        assert result == original

        # Should fail with 1KB limit
        with pytest.raises(HTTPException):
            safe_gzip_decompress(compressed, max_size=1000)

    def test_exact_limit_boundary(self):
        original = b"x" * 1000
        compressed = gzip.compress(original)

        # Should succeed at exact limit
        result = safe_gzip_decompress(compressed, max_size=1000)
        assert result == original

        # Should fail at 1 byte under
        with pytest.raises(HTTPException):
            safe_gzip_decompress(compressed, max_size=999)


class TestSafePatternMatch:
    """Tests for safe_pattern_match - prevents ReDoS attacks."""

    def test_normal_matching(self):
        pattern = re.compile(r"^\d{3}-\d{2}-\d{4}$")
        assert safe_pattern_match(pattern, "123-45-6789") is True
        assert safe_pattern_match(pattern, "invalid") is False

    def test_empty_string(self):
        pattern = re.compile(r".*")
        assert safe_pattern_match(pattern, "") is True

        pattern2 = re.compile(r".+")
        assert safe_pattern_match(pattern2, "") is False

    def test_length_limit_rejects_long_strings(self):
        pattern = re.compile(r"^[a-z]+$")
        # At limit
        assert safe_pattern_match(pattern, "a" * 256) is True
        # Over limit
        assert safe_pattern_match(pattern, "a" * 257) is False

    def test_custom_max_length(self):
        pattern = re.compile(r"^[a-z]+$")
        assert safe_pattern_match(pattern, "a" * 100, max_length=100) is True
        assert safe_pattern_match(pattern, "a" * 100, max_length=50) is False

    def test_redos_protection_via_length(self):
        """Long strings that could cause ReDoS are rejected by length check."""
        redos_pattern = re.compile(r"^(a+)+$")
        # This would cause catastrophic backtracking, but length check rejects it
        assert safe_pattern_match(redos_pattern, "a" * 300 + "b", max_length=256) is False

    def test_email_pattern(self):
        email = re.compile(r'^[\w.+-]+@[\w.-]+\.[\w]{2,}$')
        assert safe_pattern_match(email, "user@example.com") is True
        assert safe_pattern_match(email, "not-an-email") is False

    def test_special_characters(self):
        pattern = re.compile(r"^\d+$")
        assert safe_pattern_match(pattern, "123") is True
        assert safe_pattern_match(pattern, "12.34") is False
        assert safe_pattern_match(pattern, "12+34") is False

    def test_unicode_patterns(self):
        pattern = re.compile(r"^[\u4e00-\u9fa5]+$")
        assert safe_pattern_match(pattern, "你好") is True
        assert safe_pattern_match(pattern, "hello") is False

    def test_case_sensitivity(self):
        pattern = re.compile(r"^[A-Z]+$")
        assert safe_pattern_match(pattern, "UPPER") is True
        assert safe_pattern_match(pattern, "lower") is False


class TestSanitizeForLogging:
    """Tests for sanitize_for_logging - prevents log injection attacks."""

    def test_normal_strings_unchanged(self):
        assert sanitize_for_logging("Normal log message") == "Normal log message"
        assert sanitize_for_logging("User ID: 12345") == "User ID: 12345"

    def test_empty_returns_empty(self):
        assert sanitize_for_logging("") == ""

    def test_none_returns_empty(self):
        assert sanitize_for_logging(None) == ""

    def test_newline_removed(self):
        assert "\n" not in sanitize_for_logging("Line1\nLine2")

    def test_carriage_return_removed(self):
        assert "\r" not in sanitize_for_logging("Line1\rLine2")

    def test_null_byte_removed(self):
        assert "\x00" not in sanitize_for_logging("Text\x00Hidden")

    def test_tab_removed(self):
        assert "\t" not in sanitize_for_logging("Data\tvalue")

    def test_log_injection_attack(self):
        attack = "user_input\n[ERROR] Fake error message\n[INFO] Malicious entry"
        sanitized = sanitize_for_logging(attack)
        assert "\n" not in sanitized
        assert "user_input" in sanitized

    def test_length_truncation(self):
        long_string = "a" * 300
        result = sanitize_for_logging(long_string)
        assert len(result) == 259  # 256 + "..."
        assert result.endswith("...")

    def test_at_limit_not_truncated(self):
        at_limit = "a" * 256
        assert sanitize_for_logging(at_limit) == at_limit

    def test_custom_max_length(self):
        result = sanitize_for_logging("x" * 100, max_length=50)
        assert len(result) == 53  # 50 + "..."
        assert result.endswith("...")

    def test_unicode_preserved(self):
        assert sanitize_for_logging("Données françaises") == "Données françaises"
        assert sanitize_for_logging("日本語テキスト") == "日本語テキスト"

    def test_printable_special_chars_preserved(self):
        assert sanitize_for_logging("Price: $19.99") == "Price: $19.99"
        assert sanitize_for_logging("Email: user@example.com") == "Email: user@example.com"


class TestSanitizeErrorMessage:
    """Tests for sanitize_error_message - prevents information leakage."""

    def test_production_hides_details(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            error = Exception("Database connection failed at /var/lib/db")
            result = sanitize_error_message(error, "An error occurred")
            assert result == "An error occurred"
            assert "Database" not in result

    def test_development_includes_details(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            error = Exception("Something broke")
            result = sanitize_error_message(error, "Error occurred")
            assert "Error occurred" in result
            assert "Something broke" in result

    def test_default_env_includes_details(self):
        with patch.dict(os.environ, {}, clear=True):
            error = Exception("Internal error")
            result = sanitize_error_message(error, "Error occurred")
            assert "Error occurred" in result
            assert "Internal error" in result

    def test_empty_user_message(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            error = Exception("Something went wrong")
            result = sanitize_error_message(error, "")
            assert "Something went wrong" in result

    def test_none_error(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            result = sanitize_error_message(None, "Unknown error")
            assert "Unknown error" in result

    def test_production_hides_all_sensitive(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            errors = [
                Exception("Database password incorrect"),
                Exception("API key invalid: sk-1234567890"),
                Exception("Secret token: eyJhbGciOiJIUzI1NiJ9"),
            ]
            for error in errors:
                result = sanitize_error_message(error, "Service unavailable")
                assert result == "Service unavailable"


class TestIntegrations:
    """Integration tests for security functions in real-world scenarios."""

    def test_workspace_path_traversal_protection(self):
        """WorkspaceManager.get_run_dir() validates paths stay within workspace."""
        from api.storage.workspace import WorkspaceManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = WorkspaceManager(Path(tmpdir))
            # Valid UUID should work
            valid_uuid = UUID("550e8400-e29b-41d4-a716-446655440000")
            run_dir = workspace.get_run_dir(valid_uuid)
            assert str(valid_uuid) in str(run_dir)

    def test_sanitize_filename_blocks_traversal_in_upload(self):
        """Filenames from upload requests are sanitized."""
        dangerous_filenames = [
            "../../../etc/passwd.csv",
            "/var/log/test.csv",
            "..\\..\\windows\\system.csv",
        ]
        for name in dangerous_filenames:
            result = sanitize_filename(name)
            assert ".." not in result
            assert "/" not in result

    def test_gzip_in_upload_flow(self):
        """Gzip decompression in upload flow rejects bombs."""
        large_data = b"x" * (5 * 1024 * 1024)
        compressed = gzip.compress(large_data)

        with pytest.raises(HTTPException) as exc_info:
            safe_gzip_decompress(compressed, max_size=1024 * 1024)
        assert exc_info.value.status_code == 413

    def test_log_sanitization_blocks_injection(self):
        user_inputs = [
            "normal query",
            "query\nINJECTED: [ERROR] Fake error",
            "search\r\nADMIN: Unauthorized access",
        ]
        for user_input in user_inputs:
            sanitized = sanitize_for_logging(user_input)
            assert "\n" not in sanitized
            assert "\r" not in sanitized

    def test_error_message_in_api_context(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            try:
                raise FileNotFoundError("/var/lib/data/sensitive.db not found")
            except Exception as e:
                result = sanitize_error_message(e, "File not found")
                assert result == "File not found"
                assert "/var/lib" not in result


class TestSecurityBestPractices:
    """Tests for security best practices and edge cases."""

    def test_defense_in_depth(self):
        """Multiple security layers work together."""
        malicious = "../../../etc\x00/passwd\n\r"
        sanitized_filename = sanitize_filename(malicious)
        assert ".." not in sanitized_filename
        sanitized_log = sanitize_for_logging(sanitized_filename)
        assert "\n" not in sanitized_log
        assert "\r" not in sanitized_log

    def test_fail_secure_defaults(self):
        """Functions fail securely by default."""
        assert sanitize_filename(None) == "uploaded_file"
        assert sanitize_filename("") == "uploaded_file"
        assert sanitize_for_logging(None) == ""
        assert sanitize_for_logging("") == ""

        with pytest.raises(HTTPException):
            safe_gzip_decompress(b"not gzip data")

    def test_no_information_leakage_in_production(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            sensitive_errors = [
                Exception("postgres://user:pass@localhost/db"),
                Exception("API Key: sk-1234567890abcdef"),
            ]
            for error in sensitive_errors:
                result = sanitize_error_message(error, "Operation failed")
                assert result == "Operation failed"

    def test_boundary_filename_255(self):
        assert len(sanitize_filename("a" * 255)) == 255

    def test_boundary_logging_256(self):
        assert len(sanitize_for_logging("a" * 256)) == 256

    def test_boundary_pattern_256(self):
        pattern = re.compile(r"^a+$")
        assert safe_pattern_match(pattern, "a" * 256) is True
        assert safe_pattern_match(pattern, "a" * 257) is False

    def test_encoding_attacks(self):
        """URL-encoded and unicode attacks are handled."""
        encoded = "..%2F..%2F..%2Fetc%2Fpasswd"
        sanitized = sanitize_filename(encoded)
        # The ".." sequences inside are replaced
        assert ".." not in sanitized
