"""
Test suite for money format validation.

RED PHASE: These tests define expected money validation behavior.

Requirements from spec:
- Money: exactly 2 decimals
- No $, ,, or parentheses allowed
- Violations counted but values not normalized
- Invalid values excluded from stats
"""
import pytest
from pathlib import Path


class TestMoneyValidator:
    """Test money format validation."""

    def test_valid_money_format(self):
        """Test that valid money values pass validation."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        assert validator.is_valid("100.00") is True
        assert validator.is_valid("0.50") is True
        assert validator.is_valid("999999.99") is True
        assert validator.is_valid("0.00") is True

    def test_invalid_money_no_decimals(self):
        """Test that money without decimals is invalid."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        assert validator.is_valid("100") is False
        assert validator.get_violation_reason("100") == "missing_decimals"

    def test_invalid_money_one_decimal(self):
        """Test that money with only 1 decimal place is invalid."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        assert validator.is_valid("100.5") is False
        assert validator.get_violation_reason("100.5") == "wrong_decimal_places"

    def test_invalid_money_three_decimals(self):
        """Test that money with 3+ decimal places is invalid."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        assert validator.is_valid("100.505") is False
        assert validator.is_valid("100.5000") is False

    def test_invalid_money_dollar_sign(self):
        """Test that dollar sign is not allowed."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        assert validator.is_valid("$100.00") is False
        assert validator.is_valid("100.00$") is False
        assert validator.get_violation_reason("$100.00") == "disallowed_symbol_dollar"

    def test_invalid_money_comma(self):
        """Test that commas are not allowed."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        assert validator.is_valid("1,000.00") is False
        assert validator.is_valid("100,000.00") is False
        assert validator.get_violation_reason("1,000.00") == "disallowed_symbol_comma"

    def test_invalid_money_parentheses(self):
        """Test that parentheses (negative notation) are not allowed."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        assert validator.is_valid("(100.00)") is False
        assert validator.is_valid("(99.99)") is False
        assert validator.get_violation_reason("(100.00)") == "disallowed_symbol_parentheses"

    def test_valid_money_negative_with_minus(self):
        """Test that negative money with minus sign is valid."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        assert validator.is_valid("-100.00") is True
        assert validator.is_valid("-0.50") is True

    def test_invalid_money_multiple_violations(self):
        """Test detection of multiple violations in one value."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        assert validator.is_valid("$1,000") is False
        violations = validator.get_all_violations("$1,000")
        assert "disallowed_symbol_dollar" in violations
        assert "disallowed_symbol_comma" in violations
        assert "missing_decimals" in violations

    def test_money_validation_with_nulls(self):
        """Test that null/empty values are handled separately."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        # Nulls should not be considered invalid money format
        assert validator.is_valid("") is None
        assert validator.is_valid(None) is None

    def test_money_validation_with_whitespace(self):
        """Test that whitespace is not automatically trimmed."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        # Leading/trailing whitespace should make it invalid
        assert validator.is_valid(" 100.00") is False
        assert validator.is_valid("100.00 ") is False

    def test_money_validator_tracks_violation_counts(self, sample_csv_money_violations: Path):
        """Test that validator tracks counts of each violation type."""
        from api.services.validators import MoneyValidator
        from api.services.parser import CSVParser

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(sample_csv_money_violations)

        validator = MoneyValidator()
        violation_counts = validator.validate_column(result, "InvalidAmount")

        assert violation_counts["disallowed_symbol_dollar"] >= 1
        assert violation_counts["disallowed_symbol_comma"] >= 1
        assert violation_counts["disallowed_symbol_parentheses"] >= 1
        assert violation_counts["missing_decimals"] >= 1

    def test_money_validator_excludes_invalid_from_stats(self):
        """Test that invalid money values are excluded from statistics."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()
        values = ["100.00", "$200.00", "300.00", "1,000.00", "50.00"]

        valid_values = validator.filter_valid(values)

        assert len(valid_values) == 3
        assert "100.00" in valid_values
        assert "300.00" in valid_values
        assert "50.00" in valid_values
        assert "$200.00" not in valid_values
        assert "1,000.00" not in valid_values

    def test_money_format_regex_pattern(self):
        """Test the regex pattern for valid money format."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()
        pattern = validator.get_pattern()

        import re
        # Valid money pattern: optional minus, digits, exactly 2 decimals
        assert re.match(pattern, "100.00")
        assert re.match(pattern, "-100.00")
        assert re.match(pattern, "0.50")
        assert not re.match(pattern, "100")
        assert not re.match(pattern, "100.5")
        assert not re.match(pattern, "$100.00")

    def test_money_validation_edge_cases(self):
        """Test edge cases for money validation."""
        from api.services.validators import MoneyValidator

        validator = MoneyValidator()

        # Zero
        assert validator.is_valid("0.00") is True

        # Very large amount
        assert validator.is_valid("999999999999.99") is True

        # Just decimals
        assert validator.is_valid(".50") is False  # Must have leading digit

        # Multiple decimal points
        assert validator.is_valid("100.00.00") is False

        # Non-numeric characters
        assert validator.is_valid("abc.00") is False
        assert validator.is_valid("100.ab") is False
