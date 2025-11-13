"""
Test suite for numeric format validation.

RED PHASE: These tests define expected numeric validation behavior.

Requirements from spec:
- Numeric: ^[0-9]+(\.[0-9]+)?$ only
- No commas, $, or parentheses
- Violations counted but values not normalized
- Invalid values excluded from stats
"""
import pytest
from pathlib import Path


class TestNumericValidator:
    """Test numeric format validation."""

    def test_valid_numeric_integer(self):
        """Test that valid integers pass validation."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("123") is True
        assert validator.is_valid("0") is True
        assert validator.is_valid("999999") is True

    def test_valid_numeric_decimal(self):
        """Test that valid decimals pass validation."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("123.45") is True
        assert validator.is_valid("0.5") is True
        assert validator.is_valid("999.999999") is True

    def test_valid_numeric_negative(self):
        """Test that negative numbers are valid."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("-123") is True
        assert validator.is_valid("-123.45") is True
        assert validator.is_valid("-0.5") is True

    def test_invalid_numeric_comma(self):
        """Test that commas are not allowed."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("1,000") is False
        assert validator.is_valid("1,000.50") is False
        assert validator.get_violation_reason("1,000") == "disallowed_symbol_comma"

    def test_invalid_numeric_dollar_sign(self):
        """Test that dollar signs are not allowed."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("$123") is False
        assert validator.is_valid("123$") is False
        assert validator.get_violation_reason("$123") == "disallowed_symbol_dollar"

    def test_invalid_numeric_parentheses(self):
        """Test that parentheses are not allowed."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("(123)") is False
        assert validator.is_valid("(123.45)") is False
        assert validator.get_violation_reason("(123)") == "disallowed_symbol_parentheses"

    def test_invalid_numeric_multiple_decimals(self):
        """Test that multiple decimal points are not allowed."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("123.45.67") is False
        assert validator.get_violation_reason("123.45.67") == "multiple_decimal_points"

    def test_invalid_numeric_letters(self):
        """Test that letters are not allowed."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("abc") is False
        assert validator.is_valid("123abc") is False
        assert validator.is_valid("abc123") is False
        assert validator.get_violation_reason("abc") == "non_numeric_characters"

    def test_invalid_numeric_special_characters(self):
        """Test that special characters are not allowed."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("123#") is False
        assert validator.is_valid("@123") is False
        assert validator.is_valid("123%") is False

    def test_valid_numeric_leading_zeros(self):
        """Test that leading zeros are allowed."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("00123") is True
        assert validator.is_valid("0.50") is True

    def test_invalid_numeric_only_decimal(self):
        """Test that standalone decimal point is invalid."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid(".") is False
        assert validator.is_valid(".5") is False  # Must have leading digit

    def test_invalid_numeric_trailing_decimal(self):
        """Test that trailing decimal without digits is invalid."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        assert validator.is_valid("123.") is False

    def test_numeric_validation_with_nulls(self):
        """Test that null/empty values are handled separately."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        # Nulls should not be considered invalid numeric format
        assert validator.is_valid("") is None
        assert validator.is_valid(None) is None

    def test_numeric_validation_with_whitespace(self):
        """Test that whitespace is not automatically trimmed."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        # Leading/trailing whitespace should make it invalid
        assert validator.is_valid(" 123") is False
        assert validator.is_valid("123 ") is False
        assert validator.is_valid("1 23") is False

    def test_numeric_validator_tracks_violation_counts(self, sample_csv_numeric_violations: Path):
        """Test that validator tracks counts of each violation type."""
        from api.services.validators import NumericValidator
        from api.services.parser import CSVParser

        parser = CSVParser(delimiter="|")
        result = parser.parse_file(sample_csv_numeric_violations)

        validator = NumericValidator()
        violation_counts = validator.validate_column(result, "InvalidValue")

        assert violation_counts["disallowed_symbol_dollar"] >= 1
        assert violation_counts["disallowed_symbol_comma"] >= 1
        assert violation_counts["non_numeric_characters"] >= 1

    def test_numeric_validator_excludes_invalid_from_stats(self):
        """Test that invalid numeric values are excluded from statistics."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()
        values = ["123", "$456", "789", "1,000", "999"]

        valid_values = validator.filter_valid(values)

        assert len(valid_values) == 3
        assert "123" in valid_values
        assert "789" in valid_values
        assert "999" in valid_values
        assert "$456" not in valid_values
        assert "1,000" not in valid_values

    def test_numeric_format_regex_pattern(self):
        """Test the regex pattern for valid numeric format."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()
        pattern = validator.get_pattern()

        import re
        # Valid numeric pattern: optional minus, digits, optional decimal + digits
        assert re.match(pattern, "123")
        assert re.match(pattern, "123.45")
        assert re.match(pattern, "-123")
        assert re.match(pattern, "-123.45")
        assert not re.match(pattern, "1,000")
        assert not re.match(pattern, "$123")
        assert not re.match(pattern, ".5")

    def test_numeric_validation_edge_cases(self):
        """Test edge cases for numeric validation."""
        from api.services.validators import NumericValidator

        validator = NumericValidator()

        # Zero
        assert validator.is_valid("0") is True
        assert validator.is_valid("0.0") is True

        # Very large number
        assert validator.is_valid("999999999999999999") is True

        # Very small decimal
        assert validator.is_valid("0.0000000001") is True

        # Scientific notation (should be invalid)
        assert validator.is_valid("1e10") is False
        assert validator.is_valid("1.5E-3") is False

        # Plus sign
        assert validator.is_valid("+123") is False  # Only minus allowed

        # Multiple minuses
        assert validator.is_valid("--123") is False

    def test_numeric_vs_money_distinction(self):
        """Test that numeric and money validators are distinct."""
        from api.services.validators import NumericValidator, MoneyValidator

        numeric_validator = NumericValidator()
        money_validator = MoneyValidator()

        # Numeric allows any decimal places
        assert numeric_validator.is_valid("123.4") is True
        assert money_validator.is_valid("123.4") is False

        # Both should reject commas
        assert numeric_validator.is_valid("1,000.00") is False
        assert money_validator.is_valid("1,000.00") is False

        # Money requires exactly 2 decimals
        assert numeric_validator.is_valid("123") is True
        assert money_validator.is_valid("123") is False
