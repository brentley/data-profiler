"""
Error Aggregation System Tests.

Tests the ErrorAggregator class that:
- Distinguishes catastrophic vs non-catastrophic errors
- Groups errors by code with count
- Maintains error message template
- Supports error codes like: E_UTF8_INVALID, E_HEADER_MISSING, E_JAGGED_ROW, etc.
"""

import pytest
from services.errors import (
    ErrorAggregator,
    ErrorCode,
    ErrorRecord,
    ErrorSummary,
    ERROR_MESSAGES,
    CATASTROPHIC_ERRORS,
)


class TestErrorAggregatorBasics:
    """Test basic error recording and retrieval."""

    def test_record_single_error(self):
        """Recording a single error should work."""
        aggregator = ErrorAggregator()

        aggregator.record(
            ErrorCode.E_NUMERIC_FORMAT,
            line_number=5,
            column_name="amount",
        )

        assert aggregator.get_error_count(ErrorCode.E_NUMERIC_FORMAT) == 1
        assert aggregator.get_error_count_total() == 1

    def test_record_multiple_same_errors(self):
        """Recording multiple instances of same error should increment count."""
        aggregator = ErrorAggregator()

        for i in range(10):
            aggregator.record(
                ErrorCode.E_MONEY_FORMAT,
                line_number=i + 1,
                column_name="price",
            )

        assert aggregator.get_error_count(ErrorCode.E_MONEY_FORMAT) == 10
        assert aggregator.get_error_count_total() == 10

    def test_record_multiple_different_errors(self):
        """Recording different error types should track separately."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=1)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=2)
        aggregator.record(ErrorCode.E_MONEY_FORMAT, line_number=3)
        aggregator.record(ErrorCode.E_DATE_MIXED_FORMAT, line_number=4)
        aggregator.record(ErrorCode.E_DATE_MIXED_FORMAT, line_number=5)
        aggregator.record(ErrorCode.E_DATE_MIXED_FORMAT, line_number=6)

        assert aggregator.get_error_count(ErrorCode.E_NUMERIC_FORMAT) == 2
        assert aggregator.get_error_count(ErrorCode.E_MONEY_FORMAT) == 1
        assert aggregator.get_error_count(ErrorCode.E_DATE_MIXED_FORMAT) == 3
        assert aggregator.get_error_count_total() == 6

    def test_default_error_messages(self):
        """Default error messages should be used when not provided."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        errors = aggregator.get_errors()
        assert len(errors) == 1
        assert errors[0].message == ERROR_MESSAGES[ErrorCode.E_NUMERIC_FORMAT]

    def test_custom_error_messages(self):
        """Custom error messages should override defaults."""
        aggregator = ErrorAggregator()

        custom_message = "Custom error message with context"
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, message=custom_message)

        errors = aggregator.get_errors()
        assert len(errors) == 1
        assert errors[0].message == custom_message


class TestErrorAggregatorCatastrophic:
    """Test catastrophic error handling."""

    def test_catastrophic_error_detection(self):
        """Catastrophic errors should be correctly identified."""
        aggregator = ErrorAggregator()

        # Record catastrophic errors
        aggregator.record(ErrorCode.E_UTF8_INVALID)
        aggregator.record(ErrorCode.E_HEADER_MISSING)
        aggregator.record(ErrorCode.E_JAGGED_ROW)

        assert aggregator.has_catastrophic_errors() is True
        assert aggregator.has_errors() is True

    def test_non_catastrophic_error_detection(self):
        """Non-catastrophic errors should not be flagged as catastrophic."""
        aggregator = ErrorAggregator()

        # Record non-catastrophic errors
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_MONEY_FORMAT)
        aggregator.record(ErrorCode.E_QUOTE_RULE)

        assert aggregator.has_catastrophic_errors() is False
        assert aggregator.has_errors() is True

    def test_mixed_catastrophic_and_non_catastrophic(self):
        """Mix of error types should still detect catastrophic."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_JAGGED_ROW)  # Catastrophic
        aggregator.record(ErrorCode.E_MONEY_FORMAT)

        assert aggregator.has_catastrophic_errors() is True

    def test_catastrophic_error_classification(self):
        """Error records should have correct catastrophic flag."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_JAGGED_ROW)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        errors = aggregator.get_errors()
        catastrophic_error = next(e for e in errors if e.code == ErrorCode.E_JAGGED_ROW)
        non_catastrophic_error = next(
            e for e in errors if e.code == ErrorCode.E_NUMERIC_FORMAT
        )

        assert catastrophic_error.is_catastrophic is True
        assert non_catastrophic_error.is_catastrophic is False


class TestErrorAggregatorRollup:
    """Test error rollup and aggregation."""

    def test_get_error_rollup(self):
        """Error rollup should group by code."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_MONEY_FORMAT)
        aggregator.record(ErrorCode.E_MONEY_FORMAT)
        aggregator.record(ErrorCode.E_QUOTE_RULE)

        rollup = aggregator.get_error_rollup()

        assert rollup[ErrorCode.E_NUMERIC_FORMAT] == 3
        assert rollup[ErrorCode.E_MONEY_FORMAT] == 2
        assert rollup[ErrorCode.E_QUOTE_RULE] == 1

    def test_error_summaries(self):
        """Error summaries should include all metadata."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(100)

        # Record errors
        for i in range(10):
            aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=i + 1)

        for i in range(5):
            aggregator.record(ErrorCode.E_MONEY_FORMAT, line_number=i + 11)

        summaries = aggregator.get_summaries()

        assert len(summaries) == 2

        # Should be sorted by count (descending)
        assert summaries[0].code == ErrorCode.E_NUMERIC_FORMAT
        assert summaries[0].count == 10
        assert summaries[0].percentage == 0.10

        assert summaries[1].code == ErrorCode.E_MONEY_FORMAT
        assert summaries[1].count == 5
        assert summaries[1].percentage == 0.05

    def test_error_summaries_sorted_by_count(self):
        """Error summaries should be sorted by count descending."""
        aggregator = ErrorAggregator()

        # Record in random order
        aggregator.record(ErrorCode.E_MONEY_FORMAT)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_QUOTE_RULE)
        aggregator.record(ErrorCode.E_QUOTE_RULE)

        summaries = aggregator.get_summaries()

        # Should be sorted: E_NUMERIC_FORMAT (3), E_QUOTE_RULE (2), E_MONEY_FORMAT (1)
        assert summaries[0].code == ErrorCode.E_NUMERIC_FORMAT
        assert summaries[0].count == 3
        assert summaries[1].code == ErrorCode.E_QUOTE_RULE
        assert summaries[1].count == 2
        assert summaries[2].code == ErrorCode.E_MONEY_FORMAT
        assert summaries[2].count == 1

    def test_first_occurrence_tracking(self):
        """First occurrence of each error should be tracked."""
        aggregator = ErrorAggregator()

        # Record multiple instances
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=5)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=10)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=15)

        summaries = aggregator.get_summaries()
        summary = summaries[0]

        assert summary.first_occurrence is not None
        assert summary.first_occurrence.line_number == 5


class TestErrorAggregatorContext:
    """Test error context information."""

    def test_error_with_line_number(self):
        """Error should store line number."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_JAGGED_ROW, line_number=42)

        errors = aggregator.get_errors()
        assert errors[0].line_number == 42

    def test_error_with_column_name(self):
        """Error should store column name."""
        aggregator = ErrorAggregator()

        aggregator.record(
            ErrorCode.E_NUMERIC_FORMAT,
            line_number=10,
            column_name="amount",
        )

        errors = aggregator.get_errors()
        assert errors[0].column_name == "amount"

    def test_error_with_byte_offset(self):
        """Error should store byte offset."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_UTF8_INVALID, byte_offset=42891)

        errors = aggregator.get_errors()
        assert errors[0].byte_offset == 42891

    def test_error_with_details(self):
        """Error should store additional details."""
        aggregator = ErrorAggregator()

        details = {
            "expected_columns": 5,
            "actual_columns": 3,
            "raw_line": "1|Alice|100",
        }

        aggregator.record(
            ErrorCode.E_JAGGED_ROW,
            line_number=10,
            details=details,
        )

        errors = aggregator.get_errors()
        assert errors[0].details == details


class TestErrorAggregatorPercentages:
    """Test error percentage calculations."""

    def test_percentage_calculation(self):
        """Error percentages should be calculated correctly."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(1000)

        # Record 42 errors
        for i in range(42):
            aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=i + 1)

        summaries = aggregator.get_summaries()
        assert summaries[0].percentage == 0.042  # 42/1000

    def test_percentage_without_total_rows(self):
        """Percentage should be 0.0 if total rows not set."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        summaries = aggregator.get_summaries()
        assert summaries[0].percentage == 0.0

    def test_percentage_multiple_error_types(self):
        """Percentages should be calculated per error type."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(500)

        # E_NUMERIC_FORMAT: 10 errors (2%)
        for i in range(10):
            aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=i + 1)

        # E_MONEY_FORMAT: 25 errors (5%)
        for i in range(25):
            aggregator.record(ErrorCode.E_MONEY_FORMAT, line_number=i + 11)

        summaries = aggregator.get_summaries()

        numeric_summary = next(s for s in summaries if s.code == ErrorCode.E_NUMERIC_FORMAT)
        money_summary = next(s for s in summaries if s.code == ErrorCode.E_MONEY_FORMAT)

        assert numeric_summary.percentage == 0.02
        assert money_summary.percentage == 0.05


class TestErrorAggregatorSerialization:
    """Test error aggregator serialization."""

    def test_to_dict_basic(self):
        """to_dict should produce correct structure."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(100)

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_MONEY_FORMAT)

        result = aggregator.to_dict()

        assert result["total_errors"] == 3
        assert result["has_catastrophic"] is False
        assert len(result["summaries"]) == 2

    def test_to_dict_with_catastrophic(self):
        """to_dict should flag catastrophic errors."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_JAGGED_ROW)

        result = aggregator.to_dict()

        assert result["has_catastrophic"] is True

    def test_to_dict_summary_structure(self):
        """to_dict summaries should have correct structure."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(100)

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        result = aggregator.to_dict()
        summary = result["summaries"][0]

        assert "code" in summary
        assert "message" in summary
        assert "count" in summary
        assert "percentage" in summary
        assert "is_catastrophic" in summary


class TestErrorAggregatorUtilities:
    """Test utility methods."""

    def test_clear_errors(self):
        """Clearing should reset all state."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(100)

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)
        aggregator.record(ErrorCode.E_MONEY_FORMAT)

        # Verify errors exist
        assert aggregator.has_errors() is True

        # Clear
        aggregator.clear()

        # Verify cleared
        assert aggregator.has_errors() is False
        assert aggregator.get_error_count_total() == 0
        assert len(aggregator.get_errors()) == 0
        assert len(aggregator.get_error_rollup()) == 0

    def test_empty_aggregator(self):
        """Empty aggregator should handle queries correctly."""
        aggregator = ErrorAggregator()

        assert aggregator.has_errors() is False
        assert aggregator.has_catastrophic_errors() is False
        assert aggregator.get_error_count_total() == 0
        assert len(aggregator.get_errors()) == 0
        assert len(aggregator.get_summaries()) == 0

    def test_get_error_count_unknown_code(self):
        """Getting count for unknown code should return 0."""
        aggregator = ErrorAggregator()

        aggregator.record(ErrorCode.E_NUMERIC_FORMAT)

        assert aggregator.get_error_count("E_UNKNOWN_CODE") == 0


class TestErrorCodeDefinitions:
    """Test error code definitions and constants."""

    def test_catastrophic_error_codes_defined(self):
        """Catastrophic error codes should be defined."""
        assert ErrorCode.E_UTF8_INVALID in CATASTROPHIC_ERRORS
        assert ErrorCode.E_HEADER_MISSING in CATASTROPHIC_ERRORS
        assert ErrorCode.E_JAGGED_ROW in CATASTROPHIC_ERRORS

    def test_non_catastrophic_error_codes_not_in_set(self):
        """Non-catastrophic error codes should not be in catastrophic set."""
        assert ErrorCode.E_NUMERIC_FORMAT not in CATASTROPHIC_ERRORS
        assert ErrorCode.E_MONEY_FORMAT not in CATASTROPHIC_ERRORS
        assert ErrorCode.E_QUOTE_RULE not in CATASTROPHIC_ERRORS

    def test_all_error_codes_have_messages(self):
        """All error codes should have message templates."""
        codes = [
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

        for code in codes:
            assert code in ERROR_MESSAGES
            assert len(ERROR_MESSAGES[code]) > 0


class TestErrorAggregatorRealWorldScenarios:
    """Test real-world error aggregation scenarios."""

    def test_large_file_many_errors(self):
        """Handle large number of errors efficiently."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(100000)

        # Simulate 10,000 numeric format errors
        for i in range(10000):
            aggregator.record(ErrorCode.E_NUMERIC_FORMAT, line_number=i + 1)

        # Simulate 5,000 money format errors
        for i in range(5000):
            aggregator.record(ErrorCode.E_MONEY_FORMAT, line_number=i + 10001)

        assert aggregator.get_error_count_total() == 15000
        assert aggregator.get_error_count(ErrorCode.E_NUMERIC_FORMAT) == 10000
        assert aggregator.get_error_count(ErrorCode.E_MONEY_FORMAT) == 5000

        summaries = aggregator.get_summaries()
        assert len(summaries) == 2
        assert summaries[0].percentage == 0.10  # 10000/100000
        assert summaries[1].percentage == 0.05  # 5000/100000

    def test_mixed_error_types_with_context(self):
        """Handle mixed error types with context."""
        aggregator = ErrorAggregator()
        aggregator.set_total_rows(1000)

        # Numeric errors in amount column
        for i in range(42):
            aggregator.record(
                ErrorCode.E_NUMERIC_FORMAT,
                line_number=i + 1,
                column_name="amount",
                details={"value": f"$1,234.{i:02d}"},
            )

        # Money errors in price column
        for i in range(18):
            aggregator.record(
                ErrorCode.E_MONEY_FORMAT,
                line_number=i + 100,
                column_name="price",
                details={"value": f"99.9{i}"},
            )

        # Date format errors in date column
        for i in range(7):
            aggregator.record(
                ErrorCode.E_DATE_MIXED_FORMAT,
                line_number=i + 200,
                column_name="transaction_date",
                details={"formats": ["YYYYMMDD", "MM/DD/YYYY"]},
            )

        result = aggregator.to_dict()

        assert result["total_errors"] == 67
        assert len(result["summaries"]) == 3

        # Verify sorting (highest count first)
        assert result["summaries"][0]["code"] == ErrorCode.E_NUMERIC_FORMAT
        assert result["summaries"][0]["count"] == 42
        assert result["summaries"][1]["code"] == ErrorCode.E_MONEY_FORMAT
        assert result["summaries"][1]["count"] == 18
        assert result["summaries"][2]["code"] == ErrorCode.E_DATE_MIXED_FORMAT
        assert result["summaries"][2]["count"] == 7

    def test_early_catastrophic_error(self):
        """Catastrophic error early in processing."""
        aggregator = ErrorAggregator()

        # Process first few rows successfully (no errors)
        # ...

        # Hit catastrophic error on line 5
        aggregator.record(
            ErrorCode.E_JAGGED_ROW,
            line_number=5,
            details={
                "expected_columns": 10,
                "actual_columns": 7,
            },
        )

        assert aggregator.has_catastrophic_errors() is True
        assert aggregator.get_error_count_total() == 1

        summaries = aggregator.get_summaries()
        assert len(summaries) == 1
        assert summaries[0].is_catastrophic is True
        assert summaries[0].first_occurrence.line_number == 5
