"""
Tests for MoneyProfiler streaming profiler.

Tests money profiling with streaming updates and finalization.
"""

import pytest
from services.profile import MoneyProfiler, MoneyValidationResult


class TestMoneyProfiler:
    """Test MoneyProfiler streaming interface."""

    def test_streaming_updates(self):
        """Should handle streaming updates."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("67.89")
        profiler.update("$12.34")
        profiler.update("0.00")

        result = profiler.finalize()

        assert result.total_count == 4
        assert result.valid_count == 3  # 123.45, 67.89, 0.00
        assert result.invalid_count == 1  # $12.34

    def test_empty_column(self):
        """Should handle empty column."""
        profiler = MoneyProfiler()

        result = profiler.finalize()

        assert result.total_count == 0
        assert result.valid_count == 0
        assert result.invalid_count == 0
        assert result.null_count == 0

    def test_all_valid_values(self):
        """Should handle all valid values."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("67.89")
        profiler.update("0.00")
        profiler.update("999.99")

        result = profiler.finalize()

        assert result.total_count == 4
        assert result.valid_count == 4
        assert result.invalid_count == 0
        assert result.two_decimal_ok is True
        assert result.disallowed_symbols_found is False
        assert result.min_value == 0.0
        assert result.max_value == 999.99

    def test_all_invalid_values(self):
        """Should handle all invalid values."""
        profiler = MoneyProfiler()

        profiler.update("$123.45")
        profiler.update("1,234.56")
        profiler.update("(12.34)")
        profiler.update("123.456")

        result = profiler.finalize()

        assert result.total_count == 4
        assert result.valid_count == 0
        assert result.invalid_count == 4

    def test_mixed_valid_invalid(self):
        """Should handle mixed valid and invalid values."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("$67.89")
        profiler.update("100.00")
        profiler.update("1,234.56")

        result = profiler.finalize()

        assert result.valid_count == 2
        assert result.invalid_count == 2
        assert result.valid_values == ["123.45", "100.00"]

    def test_violation_tracking(self):
        """Should track violation types."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("$67.89")
        profiler.update("1,234.56")
        profiler.update("(12.34)")
        profiler.update("123.456")

        result = profiler.finalize()

        assert result.violations_by_type["dollar_sign"] == 1
        assert result.violations_by_type["comma"] == 1
        assert result.violations_by_type["parentheses"] == 1
        assert result.violations_by_type["wrong_decimals"] == 1

    def test_null_handling(self):
        """Should handle null values."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("")
        profiler.update("67.89")
        profiler.update(None)
        profiler.update("100.00")

        result = profiler.finalize()

        assert result.valid_count == 3
        assert result.null_count == 2
        assert result.total_count == 5

    def test_min_max_computation(self):
        """Should compute min/max for valid values."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("$67.89")  # Invalid
        profiler.update("500.00")
        profiler.update("1,234.56")  # Invalid
        profiler.update("10.00")

        result = profiler.finalize()

        assert result.min_value == 10.0
        assert result.max_value == 500.0

    def test_two_decimal_flag(self):
        """Should track two_decimal_ok flag."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("67.8")  # Wrong decimal count
        profiler.update("100.00")

        result = profiler.finalize()

        assert result.two_decimal_ok is False

    def test_disallowed_symbols_flag(self):
        """Should track disallowed_symbols_found flag."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("$67.89")
        profiler.update("100.00")

        result = profiler.finalize()

        assert result.disallowed_symbols_found is True

    def test_violation_examples(self):
        """Should collect violation examples."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("$67.89")
        profiler.update("1,234.56")
        profiler.update("100.00")

        result = profiler.finalize()

        assert "$67.89" in result.violation_examples["dollar_sign"]
        assert "1,234.56" in result.violation_examples["comma"]

    def test_large_dataset(self):
        """Should handle large datasets efficiently."""
        profiler = MoneyProfiler()

        # Add 1000 valid values
        for i in range(1000):
            profiler.update(f"{i}.00")

        result = profiler.finalize()

        assert result.total_count == 1000
        assert result.valid_count == 1000
        assert result.min_value == 0.0
        assert result.max_value == 999.0

    def test_summary_statistics(self):
        """Should provide summary statistics."""
        profiler = MoneyProfiler()

        profiler.update("123.45")
        profiler.update("$67.89")
        profiler.update("100.00")
        profiler.update("")
        profiler.update("1,234.56")

        result = profiler.finalize()
        summary = result.get_summary()

        assert summary["total"] == 5
        assert summary["valid"] == 2
        assert summary["invalid"] == 2
        assert summary["null"] == 1
        assert summary["valid_pct"] == 40.0
