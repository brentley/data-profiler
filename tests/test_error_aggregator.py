"""
Test suite for error aggregation and roll-up.

RED PHASE: These tests define expected error aggregation behavior.

Requirements from spec:
- Roll up errors by error code/type with counts
- Catastrophic errors: stop processing
- Non-catastrophic errors: continue processing, report counts
- Provide error code, message, and count for each error type
- Support error filtering and sorting
"""
import pytest
from pathlib import Path


class TestErrorAggregator:
    """Test error aggregation and roll-up functionality."""

    def test_aggregate_single_error_type(self):
        """Test aggregation of single error type."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid numeric format", row=1)
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid numeric format", row=3)
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid numeric format", row=5)

        rollup = aggregator.get_rollup()

        assert len(rollup) == 1
        assert rollup[0].code == "E_NUMERIC_FORMAT"
        assert rollup[0].count == 3

    def test_aggregate_multiple_error_types(self):
        """Test aggregation of multiple error types."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid numeric", row=1)
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid numeric", row=2)
        aggregator.add_error("E_MONEY_FORMAT", "Invalid money", row=3)
        aggregator.add_error("E_DATE_FORMAT", "Invalid date", row=4)

        rollup = aggregator.get_rollup()

        assert len(rollup) == 3
        codes = [e.code for e in rollup]
        assert "E_NUMERIC_FORMAT" in codes
        assert "E_MONEY_FORMAT" in codes
        assert "E_DATE_FORMAT" in codes

    def test_error_count_accuracy(self):
        """Test that error counts are accurate."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()

        # Add 100 numeric errors
        for i in range(100):
            aggregator.add_error("E_NUMERIC_FORMAT", "Invalid numeric", row=i)

        # Add 50 money errors
        for i in range(50):
            aggregator.add_error("E_MONEY_FORMAT", "Invalid money", row=i)

        rollup = aggregator.get_rollup()

        numeric_error = next(e for e in rollup if e.code == "E_NUMERIC_FORMAT")
        money_error = next(e for e in rollup if e.code == "E_MONEY_FORMAT")

        assert numeric_error.count == 100
        assert money_error.count == 50

    def test_catastrophic_vs_noncatastrophic(self):
        """Test distinction between catastrophic and non-catastrophic errors."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()
        aggregator.add_error("E_UTF8_INVALID", "Invalid UTF-8", row=1, catastrophic=True)
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid numeric", row=2, catastrophic=False)

        assert aggregator.has_catastrophic_errors() is True
        assert aggregator.should_stop_processing() is True

        rollup = aggregator.get_rollup()
        catastrophic = [e for e in rollup if e.is_catastrophic]
        assert len(catastrophic) == 1

    def test_error_rollup_sorted_by_count(self):
        """Test that error rollup is sorted by count (descending)."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()

        # Add varying counts
        for i in range(5):
            aggregator.add_error("E_TYPE_A", "Type A error", row=i)

        for i in range(15):
            aggregator.add_error("E_TYPE_B", "Type B error", row=i)

        for i in range(10):
            aggregator.add_error("E_TYPE_C", "Type C error", row=i)

        rollup = aggregator.get_rollup()

        # Should be sorted by count: B(15), C(10), A(5)
        assert rollup[0].code == "E_TYPE_B"
        assert rollup[1].code == "E_TYPE_C"
        assert rollup[2].code == "E_TYPE_A"

    def test_error_with_context(self):
        """Test that errors can include context information."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()
        aggregator.add_error(
            "E_NUMERIC_FORMAT",
            "Invalid numeric format",
            row=5,
            column="Amount",
            value="$1,000"
        )

        errors = aggregator.get_errors_by_code("E_NUMERIC_FORMAT")

        assert errors[0].row == 5
        assert errors[0].column == "Amount"
        assert errors[0].value == "$1,000"

    def test_error_sampling(self):
        """Test that error sampling limits stored error details."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator(sample_size=10)

        # Add 100 errors
        for i in range(100):
            aggregator.add_error("E_TEST", "Test error", row=i)

        errors = aggregator.get_errors_by_code("E_TEST")

        # Should only store sample_size examples
        assert len(errors) <= 10

        # But count should still be 100
        rollup = aggregator.get_rollup()
        assert rollup[0].count == 100

    def test_warning_vs_error_distinction(self):
        """Test distinction between warnings and errors."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid numeric", row=1, severity="error")
        aggregator.add_warning("W_DATE_RANGE", "Date out of range", row=2)

        assert aggregator.error_count() > 0
        assert aggregator.warning_count() > 0

        errors = aggregator.get_rollup(severity="error")
        warnings = aggregator.get_rollup(severity="warning")

        assert len(errors) == 1
        assert len(warnings) == 1

    def test_error_code_standards(self):
        """Test that error codes follow standard naming convention."""
        from api.services.errors import ErrorCode

        # Catastrophic errors start with E_
        assert ErrorCode.UTF8_INVALID.startswith("E_")
        assert ErrorCode.HEADER_MISSING.startswith("E_")
        assert ErrorCode.JAGGED_ROW.startswith("E_")

        # Warnings start with W_
        assert ErrorCode.DATE_RANGE.startswith("W_")
        assert ErrorCode.LINE_ENDING.startswith("W_")

    def test_error_message_templates(self):
        """Test that error messages use templates for consistency."""
        from api.services.errors import ErrorAggregator, ErrorMessages

        aggregator = ErrorAggregator()

        # Using template
        aggregator.add_error_from_template(
            "E_NUMERIC_FORMAT",
            row=5,
            column="Amount",
            value="$100"
        )

        errors = aggregator.get_errors_by_code("E_NUMERIC_FORMAT")
        assert "Amount" in errors[0].message
        assert "5" in errors[0].message or errors[0].row == 5

    def test_error_grouping_by_column(self):
        """Test that errors can be grouped by column."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid", row=1, column="Col1")
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid", row=2, column="Col2")
        aggregator.add_error("E_NUMERIC_FORMAT", "Invalid", row=3, column="Col1")

        errors_by_column = aggregator.get_errors_by_column()

        assert "Col1" in errors_by_column
        assert "Col2" in errors_by_column
        assert errors_by_column["Col1"]["E_NUMERIC_FORMAT"] == 2
        assert errors_by_column["Col2"]["E_NUMERIC_FORMAT"] == 1

    def test_error_statistics(self):
        """Test error statistics calculation."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()

        for i in range(100):
            if i < 10:
                aggregator.add_error("E_TYPE_A", "Error A", row=i)
            elif i < 30:
                aggregator.add_error("E_TYPE_B", "Error B", row=i)

        stats = aggregator.get_statistics()

        assert stats.total_errors == 30
        assert stats.unique_error_types == 2
        assert stats.most_common_error == "E_TYPE_B"
        assert abs(stats.error_rate - 0.3) < 0.01  # 30/100

    def test_clear_errors(self):
        """Test that errors can be cleared."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()
        aggregator.add_error("E_TEST", "Test", row=1)
        aggregator.add_error("E_TEST", "Test", row=2)

        assert aggregator.error_count() == 2

        aggregator.clear()

        assert aggregator.error_count() == 0

    def test_error_export_formats(self):
        """Test exporting errors in different formats."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator()
        aggregator.add_error("E_TEST", "Test error", row=1, column="Col1")

        # Export as JSON
        json_export = aggregator.export_json()
        assert "E_TEST" in json_export

        # Export as CSV
        csv_export = aggregator.export_csv()
        assert "E_TEST" in csv_export
        assert "Col1" in csv_export

    def test_error_threshold_exceeded(self):
        """Test detection when error threshold is exceeded."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator(error_threshold=10)

        for i in range(15):
            aggregator.add_error("E_TEST", "Test", row=i)

        assert aggregator.threshold_exceeded() is True
        assert aggregator.should_warn_user() is True

    def test_error_deduplication(self):
        """Test that identical errors on same row are deduplicated."""
        from api.services.errors import ErrorAggregator

        aggregator = ErrorAggregator(deduplicate=True)
        aggregator.add_error("E_TEST", "Same error", row=1, column="Col1")
        aggregator.add_error("E_TEST", "Same error", row=1, column="Col1")
        aggregator.add_error("E_TEST", "Same error", row=1, column="Col1")

        # Should only count once per unique row+column+code combination
        assert aggregator.error_count() == 1

    def test_catastrophic_error_codes(self):
        """Test standard catastrophic error codes."""
        from api.services.errors import CatastrophicError

        # These should all be catastrophic
        catastrophic_codes = [
            "E_UTF8_INVALID",
            "E_HEADER_MISSING",
            "E_JAGGED_ROW",
            "E_FILE_NOT_FOUND",
            "E_PERMISSION_DENIED"
        ]

        for code in catastrophic_codes:
            error = CatastrophicError(code, f"Test {code}")
            assert error.is_catastrophic is True

    def test_noncatastrophic_error_codes(self):
        """Test standard non-catastrophic error codes."""
        from api.services.errors import ErrorCode

        # These should all be non-catastrophic
        noncatastrophic_codes = [
            "E_QUOTE_RULE",
            "E_UNQUOTED_DELIM",
            "E_NUMERIC_FORMAT",
            "E_MONEY_FORMAT",
            "E_DATE_MIXED_FORMAT"
        ]

        for code in noncatastrophic_codes:
            assert not ErrorCode.is_catastrophic(code)
