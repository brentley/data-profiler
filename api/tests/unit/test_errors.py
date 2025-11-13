"""
Comprehensive tests for error aggregation and management.

Tests for services/errors.py module.
"""

import pytest
from services.errors import (
    ErrorCode,
    ErrorRecord,
    ErrorSummary,
    ErrorAggregator,
    ERROR_MESSAGES,
    CATASTROPHIC_ERRORS,
)


class TestErrorCode:
    """Test error code constants."""

    def test_catastrophic_error_codes_exist(self):
        """Catastrophic error codes should be defined."""
        assert ErrorCode.E_UTF8_INVALID
        assert ErrorCode.E_HEADER_MISSING
        assert ErrorCode.E_JAGGED_ROW

    def test_non_catastrophic_error_codes_exist(self):
        """Non-catastrophic error codes should be defined."""
        assert ErrorCode.E_QUOTE_RULE
        assert ErrorCode.E_UNQUOTED_DELIM
        assert ErrorCode.E_NUMERIC_FORMAT
        assert ErrorCode.E_MONEY_FORMAT
        assert ErrorCode.E_DATE_MIXED_FORMAT

    def test_warning_codes_exist(self):
        """Warning codes should be defined."""
        assert ErrorCode.W_DATE_RANGE
        assert ErrorCode.W_LINE_ENDING


class TestErrorMessages:
    """Test error message templates."""

    def test_all_error_codes_have_messages(self):
        """All error codes should have corresponding messages."""
        error_codes = [
            ErrorCode.E_UTF8_INVALID,
            ErrorCode.E_HEADER_MISSING,
            ErrorCode.E_JAGGED_ROW,
            ErrorCode.E_QUOTE_RULE,
            ErrorCode.E_UNQUOTED_DELIM,
            ErrorCode.E_NUMERIC_FORMAT,
            ErrorCode.E_MONEY_FORMAT,
            ErrorCode.E_DATE_MIXED_FORMAT,
            ErrorCode.W_DATE_RANGE,
            ErrorCode.W_LINE_ENDING,
        ]

        for code in error_codes:
            assert code in ERROR_MESSAGES
            assert len(ERROR_MESSAGES[code]) > 0

    def test_catastrophic_errors_set(self):
        """Catastrophic errors set should contain expected codes."""
        assert ErrorCode.E_UTF8_INVALID in CATASTROPHIC_ERRORS
        assert ErrorCode.E_HEADER_MISSING in CATASTROPHIC_ERRORS
        assert ErrorCode.E_JAGGED_ROW in CATASTROPHIC_ERRORS

        # Non-catastrophic should not be in the set
        assert ErrorCode.E_QUOTE_RULE not in CATASTROPHIC_ERRORS
        assert ErrorCode.W_DATE_RANGE not in CATASTROPHIC_ERRORS


class TestErrorRecord:
    """Test ErrorRecord dataclass."""

    def test_create_minimal_error_record(self):
        """Should create error record with minimal fields."""
        record = ErrorRecord(
            code=ErrorCode.E_NUMERIC_FORMAT,
            message="Test error",
            is_catastrophic=False
        )

        assert record.code == ErrorCode.E_NUMERIC_FORMAT
        assert record.message == "Test error"
        assert record.is_catastrophic is False
        assert record.line_number is None
        assert record.column_name is None
        assert record.byte_offset is None
        assert record.details is None

    def test_create_full_error_record(self):
        """Should create error record with all fields."""
        details = {"value": "invalid", "expected": "numeric"}
        record = ErrorRecord(
            code=ErrorCode.E_NUMERIC_FORMAT,
            message="Invalid numeric value",
            is_catastrophic=False,
            line_number=42,
            column_name="amount",
            byte_offset=1024,
            details=details
        )

        assert record.code == ErrorCode.E_NUMERIC_FORMAT
        assert record.message == "Invalid numeric value"
        assert record.is_catastrophic is False
        assert record.line_number == 42
        assert record.column_name == "amount"
        assert record.byte_offset == 1024
        assert record.details == details


class TestErrorSummary:
    """Test ErrorSummary dataclass."""

    def test_create_error_summary(self):
        """Should create error summary."""
        first_occurrence = ErrorRecord(
            code=ErrorCode.E_NUMERIC_FORMAT,
            message="Test",
            is_catastrophic=False,
            line_number=1
        )

        summary = ErrorSummary(
            code=ErrorCode.E_NUMERIC_FORMAT,
            message="Invalid numeric format detected",
            count=10,
            is_catastrophic=False,
            percentage=0.10,
            first_occurrence=first_occurrence
        )

        assert summary.code == ErrorCode.E_NUMERIC_FORMAT
        assert summary.count == 10
        assert summary.percentage == 0.10
        assert summary.is_catastrophic is False
        assert summary.first_occurrence == first_occurrence


class TestErrorAggregator:
    """Test ErrorAggregator class."""

    def test_init(self):
        """Should initialize empty aggregator."""
        aggregator = ErrorAggregator()

        assert not aggregator.has_errors()
        assert not aggregator.has_catastrophic_errors()
        assert aggregator.get_error_count_total() == 0
        assert len(aggregator.get_errors()) == 0
        assert len(aggregator.get_error_rollup()) == 0

    def test_record_error_with_defaults(self):
        """Should record error using default message."""
        aggregator = ErrorAggregator()
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        assert aggregator.has_errors()
        assert aggregator.get_error_count(ErrorCode.E_NUMERIC_FORMAT) == 1
        assert aggregator.get_error_count_total() == 1

        errors = aggregator.get_errors()
        assert len(errors) == 1
        assert errors[0].code == ErrorCode.E_NUMERIC_FORMAT
        assert errors[0].message == ERROR_MESSAGES[ErrorCode.E_NUMERIC_FORMAT]

    def test_record_error_with_custom_message(self):
        """Should record error with custom message."""
        aggregator = ErrorAggregator()
        custom_message = "Custom error message"
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, message=custom_message)

        errors = aggregator.get_errors()
        assert errors[0].message == custom_message

    def test_record_error_with_context(self):
        """Should record error with full context."""
        aggregator = ErrorAggregator()
        details = {"value": "abc", "expected": "numeric"}

        aggregator.record(
            code=ErrorCode.E_NUMERIC_FORMAT,
            line_number=42,
            column_name="amount",
            byte_offset=1024,
            details=details
        )

        errors = aggregator.get_errors()
        assert len(errors) == 1
        error = errors[0]
        assert error.line_number == 42
        assert error.column_name == "amount"
        assert error.byte_offset == 1024
        assert error.details == details

    def test_record_multiple_same_errors(self):
        """Should count multiple occurrences of same error."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=1)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=2)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=3)

        assert aggregator.get_error_count(ErrorCode.E_NUMERIC_FORMAT) == 3
        assert aggregator.get_error_count_total() == 3
        assert len(aggregator.get_errors()) == 3

    def test_record_different_errors(self):
        """Should track different error codes separately."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_MONEY_FORMAT)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        assert aggregator.get_error_count(ErrorCode.E_NUMERIC_FORMAT) == 2
        assert aggregator.get_error_count(ErrorCode.E_MONEY_FORMAT) == 1
        assert aggregator.get_error_count_total() == 3

    def test_catastrophic_error_detection(self):
        """Should detect catastrophic errors."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        assert not aggregator.has_catastrophic_errors()

        aggregator.record(ErrorCode.E_JAGGED_ROW)
        assert aggregator.has_catastrophic_errors()

    def test_get_error_rollup(self):
        """Should return error counts by code."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_MONEY_FORMAT)

        rollup = aggregator.get_error_rollup()
        assert rollup[ErrorCode.E_NUMERIC_FORMAT] == 2
        assert rollup[ErrorCode.E_MONEY_FORMAT] == 1
        assert ErrorCode.E_DATE_MIXED_FORMAT not in rollup

    def test_get_summaries(self):
        """Should generate error summaries."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(100)

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=1)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=2)
        aggregator.record(ErrorCode.E_MONEY_FORMAT, line_number=3)

        summaries = aggregator.get_summaries()

        assert len(summaries) == 2

        # Should be sorted by count descending
        assert summaries[0].code == ErrorCode.E_NUMERIC_FORMAT
        assert summaries[0].count == 2
        assert summaries[0].percentage == 0.02  # 2/100

        assert summaries[1].code == ErrorCode.E_MONEY_FORMAT
        assert summaries[1].count == 1
        assert summaries[1].percentage == 0.01  # 1/100

    def test_summaries_include_first_occurrence(self):
        """Should include first occurrence in summaries."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=10)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=20)

        summaries = aggregator.get_summaries()
        assert summaries[0].first_occurrence is not None
        assert summaries[0].first_occurrence.line_number == 10  # First one

    def test_set_total_rows(self):
        """Should set total rows for percentage calculations."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(1000)

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        summaries = aggregator.get_summaries()
        assert summaries[0].percentage == 0.001  # 1/1000

    def test_percentage_zero_when_no_rows(self):
        """Should handle zero total rows."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(0)

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        summaries = aggregator.get_summaries()
        assert summaries[0].percentage == 0.0

    def test_to_dict(self):
        """Should convert to dictionary format."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(100)

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_JAGGED_ROW)

        result = aggregator.to_dict()

        assert result["total_errors"] == 3
        assert result["has_catastrophic"] is True
        assert len(result["summaries"]) == 2

        # Check summary format
        summary = result["summaries"][0]
        assert "code" in summary
        assert "message" in summary
        assert "count" in summary
        assert "percentage" in summary
        assert "is_catastrophic" in summary

    def test_clear(self):
        """Should clear all recorded errors."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(100)

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_MONEY_FORMAT)

        assert aggregator.has_errors()
        assert aggregator.get_error_count_total() == 2

        aggregator.clear()

        assert not aggregator.has_errors()
        assert aggregator.get_error_count_total() == 0
        assert len(aggregator.get_errors()) == 0
        assert len(aggregator.get_error_rollup()) == 0
        assert aggregator._total_rows == 0

    def test_get_errors_returns_copy(self):
        """Should return copy of errors list."""
        aggregator = ErrorAggregator()
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        errors1 = aggregator.get_errors()
        errors2 = aggregator.get_errors()

        assert errors1 is not errors2  # Different objects
        assert errors1 == errors2  # Same content

    def test_get_error_rollup_returns_copy(self):
        """Should return copy of rollup dict."""
        aggregator = ErrorAggregator()
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        rollup1 = aggregator.get_error_rollup()
        rollup2 = aggregator.get_error_rollup()

        assert rollup1 is not rollup2  # Different objects
        assert rollup1 == rollup2  # Same content

    def test_unknown_error_code_handling(self):
        """Should handle unknown error codes gracefully."""
        aggregator = ErrorAggregator()
        unknown_code = "E_UNKNOWN_ERROR"

        aggregator.record(unknown_code, message="Some error")

        errors = aggregator.get_errors()
        assert len(errors) == 1
        assert errors[0].code == unknown_code
        assert errors[0].message == "Some error"

    def test_unknown_error_code_default_message(self):
        """Should use default message for unknown codes."""
        aggregator = ErrorAggregator()
        unknown_code = "E_UNKNOWN_ERROR"

        aggregator.record(unknown_code)

        errors = aggregator.get_errors()
        assert errors[0].message == "Unknown error"
