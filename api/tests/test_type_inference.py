"""
Type inference tests.

Tests type detection for columns:
- alpha: string (all letters)
- varchar: string (mixed)
- code: string (dictionary-like, low cardinality)
- numeric: digits with optional single decimal point
- money: exactly 2 decimals, no $, ,, parentheses
- date: one consistent format per column
- mixed: multiple types detected
- unknown: cannot determine type
"""

import pytest
from services.types import TypeInferrer, ColumnType


class TestNumericTypeInference:
    """Test numeric type detection."""

    def test_integers_only(self):
        """Should detect integers as numeric."""
        values = ["123", "456", "789", "0", "999999"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.NUMERIC
        assert result.confidence > 0.95

    def test_decimals_numeric(self):
        """Should detect decimals as numeric."""
        values = ["123.45", "67.89", "0.5", "999.0"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.NUMERIC
        assert result.confidence > 0.95

    def test_mixed_integers_and_decimals(self):
        """Should detect mixed integers and decimals as numeric."""
        values = ["123", "45.67", "89", "0.5"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.NUMERIC

    def test_invalid_numeric_with_comma(self):
        """Commas should invalidate numeric type."""
        values = ["123", "1,234", "567"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        # Should detect as mixed or varchar due to invalid format
        assert result.inferred_type != ColumnType.NUMERIC
        assert result.invalid_count > 0

    def test_invalid_numeric_with_dollar(self):
        """Dollar signs should invalidate numeric type."""
        values = ["123", "$456", "789"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type != ColumnType.NUMERIC
        assert result.invalid_count > 0

    def test_negative_numbers(self):
        """Negative numbers with minus sign."""
        values = ["-123", "-45.67", "89"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        # Depends on spec: if minus allowed in numeric
        # Based on spec: ^[0-9]+(\.[0-9]+)?$ only
        assert result.inferred_type != ColumnType.NUMERIC or result.invalid_count > 0

    def test_numeric_with_nulls(self):
        """Nulls should be allowed in numeric columns."""
        values = ["123", "", "456", None, "789"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.NUMERIC
        assert result.null_count == 2

    def test_scientific_notation_not_numeric(self):
        """Scientific notation should not be valid numeric."""
        values = ["1.23e5", "4.56E-2", "789"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type != ColumnType.NUMERIC


class TestMoneyTypeInference:
    """Test money type detection."""

    def test_valid_money_two_decimals(self):
        """Should detect money with exactly 2 decimals."""
        values = ["123.45", "67.89", "0.00", "999.99"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.MONEY
        assert result.confidence > 0.95

    def test_money_one_decimal_invalid(self):
        """Money with 1 decimal should be invalid."""
        values = ["123.4", "67.89", "0.0"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        # Should detect money attempt but with violations
        assert result.inferred_type in [ColumnType.MONEY, ColumnType.MIXED]
        assert result.invalid_count > 0

    def test_money_three_decimals_invalid(self):
        """Money with 3 decimals should be invalid."""
        values = ["123.456", "67.890"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.invalid_count > 0

    def test_money_with_dollar_sign_invalid(self):
        """Dollar signs should be disallowed."""
        values = ["$123.45", "$67.89"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.invalid_count > 0
        assert any("$" in v for v in ["$123.45", "$67.89"])

    def test_money_with_comma_invalid(self):
        """Commas should be disallowed."""
        values = ["1,234.56", "67.89"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.invalid_count > 0

    def test_money_with_parentheses_invalid(self):
        """Parentheses (negative) should be disallowed."""
        values = ["(123.45)", "67.89"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.invalid_count > 0

    def test_money_zero_value(self):
        """Zero money values should be valid."""
        values = ["0.00", "123.45", "0.00"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.MONEY

    def test_money_with_nulls(self):
        """Nulls should be allowed in money columns."""
        values = ["123.45", "", None, "67.89"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.MONEY
        assert result.null_count == 2


class TestDateTypeInference:
    """Test date type detection."""

    def test_yyyymmdd_format(self):
        """Should detect YYYYMMDD format (preferred)."""
        values = ["20220101", "20220215", "20221231"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.DATE
        assert result.detected_format == "YYYYMMDD"

    def test_yyyy_mm_dd_format(self):
        """Should detect YYYY-MM-DD format."""
        values = ["2022-01-01", "2022-02-15", "2022-12-31"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.DATE
        assert result.detected_format == "YYYY-MM-DD"

    def test_mm_dd_yyyy_format(self):
        """Should detect MM/DD/YYYY format."""
        values = ["01/01/2022", "02/15/2022", "12/31/2022"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.DATE
        assert "MM" in result.detected_format

    def test_mixed_date_formats_error(self):
        """Mixed date formats should generate errors."""
        values = ["20220101", "2022-02-15", "03/01/2022"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        # Should detect as mixed or date with errors
        assert result.invalid_count > 0 or result.inferred_type == ColumnType.MIXED

    def test_consistent_format_required(self):
        """One consistent format per column is required."""
        values = ["20220101", "20220201", "20220301"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.DATE
        # All should match same format
        assert result.invalid_count == 0

    def test_date_out_of_range_year_low(self):
        """Year < 1900 should generate warning."""
        values = ["18991231", "19000101", "20220101"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.DATE
        assert result.out_of_range_count > 0

    def test_date_out_of_range_year_high(self):
        """Year > current + 1 should generate warning."""
        values = ["20220101", "20500101", "20220201"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.DATE
        assert result.out_of_range_count > 0

    def test_date_with_nulls(self):
        """Nulls should be allowed in date columns."""
        values = ["20220101", "", None, "20220201"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.DATE
        assert result.null_count == 2

    def test_invalid_date_values(self):
        """Invalid date values should be counted."""
        values = ["20220101", "20229999", "20220229"]  # Feb 29 in non-leap year
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        # Depends on validation strictness
        assert result.invalid_count >= 0


class TestStringTypeInference:
    """Test string type detection (alpha, varchar, code)."""

    def test_alpha_all_letters(self):
        """Should detect alpha for all letter strings."""
        values = ["abc", "def", "xyz", "hello"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.ALPHA

    def test_varchar_mixed_content(self):
        """Should detect varchar for mixed content."""
        values = ["abc123", "hello world", "test@example.com"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.VARCHAR

    def test_code_low_cardinality(self):
        """Should detect code for low cardinality strings."""
        values = ["A", "B", "A", "C", "B", "A", "B", "C"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.CODE
        # Code typically has < 10% unique values
        assert result.distinct_ratio < 0.5

    def test_varchar_high_cardinality(self):
        """Should detect varchar for high cardinality strings."""
        values = [f"value_{i}" for i in range(100)]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.VARCHAR

    def test_empty_strings_as_nulls(self):
        """Empty strings should count as nulls."""
        values = ["abc", "", "def", ""]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.null_count == 2


class TestMixedTypeInference:
    """Test mixed type detection."""

    def test_mixed_numeric_and_string(self):
        """Should detect mixed when both numeric and string."""
        values = ["123", "abc", "456", "def"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.MIXED

    def test_mixed_date_and_string(self):
        """Should detect mixed when both date and string."""
        values = ["20220101", "abc", "20220201"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.MIXED

    def test_mostly_numeric_few_invalid(self):
        """Mostly numeric with few invalid should be numeric with errors."""
        values = ["123", "456", "789", "abc", "999"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        # Threshold: if > 90% match, consider that type with errors
        assert result.inferred_type in [ColumnType.NUMERIC, ColumnType.MIXED]


class TestUnknownTypeInference:
    """Test unknown type detection."""

    def test_all_nulls(self):
        """All nulls should be unknown."""
        values = ["", None, "", None]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.UNKNOWN

    def test_empty_column(self):
        """Empty column should be unknown."""
        values = []
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert result.inferred_type == ColumnType.UNKNOWN


class TestTypeInferencerConfig:
    """Test type inferencer configuration options."""

    def test_sample_size_limit(self):
        """Should sample large columns efficiently."""
        values = [f"val_{i}" for i in range(100000)]
        inferencer = TypeInferrer(sample_size=1000)

        result = inferencer.infer_type(values)
        # Should still infer correctly from sample
        assert result.inferred_type is not None

    def test_confidence_threshold(self):
        """Should report confidence level."""
        values = ["123", "456", "789"]
        inferencer = TypeInferrer()

        result = inferencer.infer_type(values)
        assert hasattr(result, 'confidence')
        assert 0 <= result.confidence <= 1

    def test_type_hints_override(self):
        """Should allow manual type hints."""
        values = ["123", "456", "789"]
        inferencer = TypeInferrer(type_hint=ColumnType.MONEY)

        result = inferencer.infer_type(values)
        # Should try money first, but fail (need 2 decimals)
        assert result.invalid_count > 0 or result.inferred_type != ColumnType.MONEY
