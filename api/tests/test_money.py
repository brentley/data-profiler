"""
Money field validation tests.

Tests money validation rules:
- Must have exactly 2 decimal places
- No dollar signs ($)
- No commas (,)
- No parentheses for negatives ()
- Count violations but don't normalize
"""

import pytest
from services.types import MoneyValidator


class TestMoneyValidator:
    """Test money validation rules."""

    def test_valid_money_format(self):
        """Valid money with 2 decimals should pass."""
        validator = MoneyValidator()

        assert validator.is_valid("123.45") is True
        assert validator.is_valid("0.00") is True
        assert validator.is_valid("999999.99") is True
        assert validator.is_valid("1.00") is True

    def test_exact_two_decimals_required(self):
        """Exactly 2 decimals required."""
        validator = MoneyValidator()

        # Invalid: not 2 decimals
        assert validator.is_valid("123") is False
        assert validator.is_valid("123.4") is False
        assert validator.is_valid("123.456") is False
        assert validator.is_valid("123.") is False

    def test_dollar_sign_disallowed(self):
        """Dollar signs should be disallowed."""
        validator = MoneyValidator()

        assert validator.is_valid("$123.45") is False
        assert validator.is_valid("123.45$") is False
        assert validator.is_valid("$123.45$") is False

    def test_comma_disallowed(self):
        """Commas should be disallowed."""
        validator = MoneyValidator()

        assert validator.is_valid("1,234.56") is False
        assert validator.is_valid("12,34.56") is False
        assert validator.is_valid("123,456.78") is False

    def test_parentheses_disallowed(self):
        """Parentheses (for negatives) should be disallowed."""
        validator = MoneyValidator()

        assert validator.is_valid("(123.45)") is False
        assert validator.is_valid("(12.34)") is False

    def test_negative_sign(self):
        """Negative sign handling."""
        validator = MoneyValidator()

        # Based on spec: ^[0-9]+(\.[0-9]+)?$ - no minus allowed
        assert validator.is_valid("-123.45") is False

    def test_zero_values(self):
        """Zero values should be valid."""
        validator = MoneyValidator()

        assert validator.is_valid("0.00") is True
        assert validator.is_valid("00.00") is True
        assert validator.is_valid("000.00") is True

    def test_leading_zeros(self):
        """Leading zeros should be valid."""
        validator = MoneyValidator()

        assert validator.is_valid("0001.23") is True
        assert validator.is_valid("00.45") is True

    def test_large_amounts(self):
        """Large amounts should be valid if format correct."""
        validator = MoneyValidator()

        assert validator.is_valid("1234567890.12") is True
        assert validator.is_valid("999999999999.99") is True

    def test_whitespace_handling(self):
        """Whitespace should invalidate or be stripped."""
        validator = MoneyValidator()

        # Strict: whitespace invalidates
        assert validator.is_valid(" 123.45") is False
        assert validator.is_valid("123.45 ") is False
        assert validator.is_valid("123 .45") is False

    def test_null_empty_handling(self):
        """Null and empty should be handled specially."""
        validator = MoneyValidator()

        # Nulls are tracked separately, not validated
        assert validator.is_null("") is True
        assert validator.is_null(None) is True
        assert validator.is_null("123.45") is False


class TestMoneyValidatorBatch:
    """Test batch validation and statistics."""

    def test_validate_column(self):
        """Should validate entire column and return stats."""
        validator = MoneyValidator()
        values = ["123.45", "67.89", "$12.34", "0.00", "1,234.56"]

        result = validator.validate_column(values)

        assert result.total_count == 5
        assert result.valid_count == 3  # 123.45, 67.89, 0.00
        assert result.invalid_count == 2  # $12.34, 1,234.56
        assert result.null_count == 0

    def test_count_violations(self):
        """Should count each type of violation."""
        validator = MoneyValidator()
        values = ["123.45", "$67.89", "1,234.56", "(12.34)", "123.456"]

        result = validator.validate_column(values)

        assert result.violations_by_type["dollar_sign"] == 1
        assert result.violations_by_type["comma"] == 1
        assert result.violations_by_type["parentheses"] == 1
        assert result.violations_by_type["wrong_decimals"] == 1

    def test_two_decimal_ok_flag(self):
        """Should track if all values have 2 decimals."""
        validator = MoneyValidator()

        values_ok = ["123.45", "67.89", "0.00"]
        result_ok = validator.validate_column(values_ok)
        assert result_ok.two_decimal_ok is True

        values_bad = ["123.45", "67.8", "0.00"]
        result_bad = validator.validate_column(values_bad)
        assert result_bad.two_decimal_ok is False

    def test_disallowed_symbols_flag(self):
        """Should track if disallowed symbols found."""
        validator = MoneyValidator()

        values_clean = ["123.45", "67.89"]
        result_clean = validator.validate_column(values_clean)
        assert result_clean.disallowed_symbols_found is False

        values_dirty = ["$123.45", "67.89"]
        result_dirty = validator.validate_column(values_dirty)
        assert result_dirty.disallowed_symbols_found is True

    def test_exclude_invalid_from_stats(self):
        """Invalid values should be excluded from numeric stats."""
        validator = MoneyValidator()
        values = ["123.45", "$67.89", "100.00"]

        result = validator.validate_column(values)

        # Only valid values used for stats
        assert result.valid_values == ["123.45", "100.00"]
        # Can compute stats on these
        assert result.min_value == 100.00
        assert result.max_value == 123.45

    def test_all_valid_column(self):
        """Column with all valid values."""
        validator = MoneyValidator()
        values = ["123.45", "67.89", "0.00", "999.99"]

        result = validator.validate_column(values)

        assert result.valid_count == 4
        assert result.invalid_count == 0
        assert result.two_decimal_ok is True
        assert result.disallowed_symbols_found is False

    def test_all_invalid_column(self):
        """Column with all invalid values."""
        validator = MoneyValidator()
        values = ["$123.45", "1,234.56", "(12.34)", "123.456"]

        result = validator.validate_column(values)

        assert result.valid_count == 0
        assert result.invalid_count == 4

    def test_mixed_with_nulls(self):
        """Column with valid, invalid, and null values."""
        validator = MoneyValidator()
        values = ["123.45", "", "$67.89", None, "100.00"]

        result = validator.validate_column(values)

        assert result.valid_count == 2
        assert result.invalid_count == 1
        assert result.null_count == 2

    def test_pattern_validation(self):
        """Should use regex pattern for validation."""
        validator = MoneyValidator()

        # Pattern should be: ^\d+\.\d{2}$
        assert validator.is_valid("123.45") is True
        assert validator.is_valid("1.00") is True
        assert validator.is_valid(".45") is False  # No leading digits
        assert validator.is_valid("123.") is False  # No decimals
        assert validator.is_valid("123.4") is False  # Only 1 decimal
        assert validator.is_valid("123.456") is False  # 3 decimals


class TestMoneyValidatorReporting:
    """Test reporting and error messages."""

    def test_error_messages(self):
        """Should provide clear error messages."""
        validator = MoneyValidator()

        result = validator.validate_value("$123.45")
        assert result.is_valid is False
        assert "dollar" in result.error_message.lower()

        result = validator.validate_value("1,234.56")
        assert result.is_valid is False
        assert "comma" in result.error_message.lower()

        result = validator.validate_value("123.456")
        assert result.is_valid is False
        assert "decimal" in result.error_message.lower()

    def test_violation_examples(self):
        """Should provide examples of violations."""
        validator = MoneyValidator()
        values = ["123.45", "$67.89", "1,234.56", "100.00"]

        result = validator.validate_column(values)

        # Should include examples of each violation type
        assert len(result.violation_examples["dollar_sign"]) > 0
        assert "$67.89" in result.violation_examples["dollar_sign"]

    def test_summary_statistics(self):
        """Should provide summary statistics."""
        validator = MoneyValidator()
        values = ["123.45", "$67.89", "1,234.56", "100.00", ""]

        result = validator.validate_column(values)

        summary = result.get_summary()
        assert summary["total"] == 5
        assert summary["valid"] == 2
        assert summary["invalid"] == 2
        assert summary["null"] == 1
        assert summary["valid_pct"] == 40.0
