"""
Date validation and format detection tests.

Tests date handling:
- Detect one consistent format per column (prefer YYYYMMDD)
- Allow nulls
- Count format inconsistencies
- Warn on out-of-range dates (year < 1900 or > current + 1)
- Track min/max dates
- Distribution by month/year
"""

import pytest
from datetime import datetime
from services.types import DateValidator


class TestDateFormatDetection:
    """Test date format detection."""

    def test_detect_yyyymmdd(self):
        """Should detect YYYYMMDD format (preferred)."""
        validator = DateValidator()
        values = ["20220101", "20220215", "20221231"]

        result = validator.detect_format(values)
        assert result.detected_format == "YYYYMMDD"
        assert result.confidence > 0.95

    def test_detect_yyyy_mm_dd(self):
        """Should detect YYYY-MM-DD format."""
        validator = DateValidator()
        values = ["2022-01-01", "2022-02-15", "2022-12-31"]

        result = validator.detect_format(values)
        assert result.detected_format == "YYYY-MM-DD"

    def test_detect_mm_dd_yyyy(self):
        """Should detect MM/DD/YYYY format."""
        validator = DateValidator()
        values = ["01/01/2022", "02/15/2022", "12/31/2022"]

        result = validator.detect_format(values)
        assert result.detected_format == "MM/DD/YYYY"

    def test_detect_dd_mm_yyyy(self):
        """Should detect DD/MM/YYYY format."""
        validator = DateValidator()
        # Use dates that are unambiguous
        values = ["31/12/2022", "15/06/2022", "01/01/2022"]

        result = validator.detect_format(values)
        assert result.detected_format == "DD/MM/YYYY"

    def test_ambiguous_format_resolution(self):
        """Should handle ambiguous dates (01/02/2022)."""
        validator = DateValidator()
        # All dates could be either MM/DD or DD/MM
        values = ["01/02/2022", "03/04/2022", "05/06/2022"]

        result = validator.detect_format(values)
        # Should pick one based on majority pattern or preference
        assert result.detected_format in ["MM/DD/YYYY", "DD/MM/YYYY"]
        assert result.has_ambiguity is True

    def test_consistent_format_required(self):
        """Should require one consistent format per column."""
        validator = DateValidator()
        values = ["20220101", "20220215", "20221231"]

        result = validator.validate_column(values)
        assert result.format_consistent is True
        assert result.invalid_count == 0

    def test_mixed_formats_error(self):
        """Mixed formats should generate errors."""
        validator = DateValidator()
        values = ["20220101", "2022-02-15", "03/01/2022"]

        result = validator.validate_column(values)
        assert result.format_consistent is False
        assert result.invalid_count > 0

    def test_detect_with_nulls(self):
        """Should detect format ignoring nulls."""
        validator = DateValidator()
        values = ["20220101", "", "20220215", None, "20221231"]

        result = validator.detect_format(values)
        assert result.detected_format == "YYYYMMDD"
        assert result.null_count == 2


class TestDateValidation:
    """Test date value validation."""

    def test_valid_dates_yyyymmdd(self):
        """Valid YYYYMMDD dates should pass."""
        validator = DateValidator()
        values = ["20220101", "20220630", "20221231"]

        result = validator.validate_column(values)
        assert result.valid_count == 3
        assert result.invalid_count == 0

    def test_invalid_month(self):
        """Invalid month should fail."""
        validator = DateValidator()
        values = ["20221301", "20220001"]  # Month 13 and 00

        result = validator.validate_column(values)
        assert result.invalid_count == 2

    def test_invalid_day(self):
        """Invalid day should fail."""
        validator = DateValidator()
        values = ["20220132", "20220600"]  # Day 32 and 00

        result = validator.validate_column(values)
        assert result.invalid_count == 2

    def test_leap_year_handling(self):
        """Should validate leap years correctly."""
        validator = DateValidator()

        # 2020 was a leap year
        assert validator.is_valid("20200229", "YYYYMMDD") is True

        # 2022 was not a leap year
        assert validator.is_valid("20220229", "YYYYMMDD") is False

    def test_days_in_month(self):
        """Should validate days per month correctly."""
        validator = DateValidator()

        # 30-day months
        assert validator.is_valid("20220431", "YYYYMMDD") is False  # April
        assert validator.is_valid("20220631", "YYYYMMDD") is False  # June

        # 31-day months
        assert validator.is_valid("20220131", "YYYYMMDD") is True  # January
        assert validator.is_valid("20220731", "YYYYMMDD") is True  # July


class TestDateRangeValidation:
    """Test out-of-range date detection."""

    def test_year_too_old_warning(self):
        """Year < 1900 should generate warning."""
        validator = DateValidator()
        values = ["18991231", "19000101", "20220101"]

        result = validator.validate_column(values)
        assert result.out_of_range_count > 0
        assert any("1899" in str(w) for w in result.warnings)

    def test_year_too_new_warning(self):
        """Year > current + 1 should generate warning."""
        validator = DateValidator()
        current_year = datetime.now().year
        future_year = current_year + 5

        values = [f"{future_year}0101", "20220101"]

        result = validator.validate_column(values)
        assert result.out_of_range_count > 0

    def test_current_year_plus_one_valid(self):
        """Current year + 1 should be valid (no warning)."""
        validator = DateValidator()
        current_year = datetime.now().year
        next_year = current_year + 1

        values = [f"{next_year}0101", "20220101"]

        result = validator.validate_column(values)
        # Should not warn about next year
        assert result.out_of_range_count == 0

    def test_reasonable_range(self):
        """Dates in reasonable range should be valid."""
        validator = DateValidator()
        values = ["19500101", "20000101", "20220101"]

        result = validator.validate_column(values)
        assert result.out_of_range_count == 0


class TestDateStatistics:
    """Test date statistics calculation."""

    def test_min_max_dates(self):
        """Should track min and max dates."""
        validator = DateValidator()
        values = ["20220101", "20220630", "20221231"]

        result = validator.validate_column(values)
        assert result.min_date == "20220101"
        assert result.max_date == "20221231"

    def test_date_range_span(self):
        """Should calculate date range span."""
        validator = DateValidator()
        values = ["20220101", "20221231"]

        result = validator.validate_column(values)
        assert result.span_days == 364  # 2022 not a leap year

    def test_distribution_by_month(self):
        """Should provide distribution by month."""
        validator = DateValidator()
        values = [
            "20220101", "20220115", "20220131",  # 3 in January
            "20220201", "20220215",  # 2 in February
            "20220301"  # 1 in March
        ]

        result = validator.validate_column(values)
        assert result.distribution_by_month["2022-01"] == 3
        assert result.distribution_by_month["2022-02"] == 2
        assert result.distribution_by_month["2022-03"] == 1

    def test_distribution_by_year(self):
        """Should provide distribution by year."""
        validator = DateValidator()
        values = [
            "20210101", "20210201",  # 2 in 2021
            "20220101", "20220201", "20220301"  # 3 in 2022
        ]

        result = validator.validate_column(values)
        assert result.distribution_by_year["2021"] == 2
        assert result.distribution_by_year["2022"] == 3

    def test_distribution_by_day_of_week(self):
        """Should provide distribution by day of week."""
        validator = DateValidator()
        values = ["20220103", "20220104", "20220105"]  # Mon, Tue, Wed

        result = validator.validate_column(values)
        # Should have counts for each day of week
        assert hasattr(result, 'distribution_by_dow')


class TestDateParsing:
    """Test date parsing and conversion."""

    def test_parse_yyyymmdd(self):
        """Should parse YYYYMMDD format."""
        validator = DateValidator()

        date = validator.parse_date("20220101", "YYYYMMDD")
        assert date.year == 2022
        assert date.month == 1
        assert date.day == 1

    def test_parse_yyyy_mm_dd(self):
        """Should parse YYYY-MM-DD format."""
        validator = DateValidator()

        date = validator.parse_date("2022-01-01", "YYYY-MM-DD")
        assert date.year == 2022
        assert date.month == 1
        assert date.day == 1

    def test_parse_mm_dd_yyyy(self):
        """Should parse MM/DD/YYYY format."""
        validator = DateValidator()

        date = validator.parse_date("01/15/2022", "MM/DD/YYYY")
        assert date.year == 2022
        assert date.month == 1
        assert date.day == 15

    def test_parse_with_time(self):
        """Should handle dates with timestamps."""
        validator = DateValidator()

        # If timestamps present, extract date part
        date = validator.parse_date("2022-01-01 14:30:00", "YYYY-MM-DD HH:MM:SS")
        assert date.year == 2022
        assert date.month == 1
        assert date.day == 1


class TestDateValidatorConfig:
    """Test date validator configuration."""

    def test_prefer_yyyymmdd(self):
        """Should prefer YYYYMMDD when ambiguous."""
        validator = DateValidator(prefer_format="YYYYMMDD")

        # If multiple formats possible, prefer YYYYMMDD
        values = ["20220101"]
        result = validator.detect_format(values)
        assert result.detected_format == "YYYYMMDD"

    def test_custom_range_limits(self):
        """Should allow custom year range limits."""
        validator = DateValidator(min_year=1950, max_year=2030)

        values = ["19400101", "20400101"]
        result = validator.validate_column(values)
        assert result.out_of_range_count == 2

    def test_strict_mode(self):
        """Strict mode should reject any inconsistencies."""
        validator = DateValidator(strict=True)

        values = ["20220101", "2022-01-01"]
        result = validator.validate_column(values)
        # In strict mode, mixed formats are invalid
        assert result.invalid_count > 0


class TestDateNullHandling:
    """Test null handling in dates."""

    def test_nulls_allowed(self):
        """Nulls should be allowed in date columns."""
        validator = DateValidator()
        values = ["20220101", "", None, "20220201"]

        result = validator.validate_column(values)
        assert result.null_count == 2
        assert result.valid_count == 2

    def test_empty_string_as_null(self):
        """Empty strings should count as null."""
        validator = DateValidator()

        assert validator.is_null("") is True
        assert validator.is_null("   ") is True  # Whitespace only
        assert validator.is_null(None) is True
        assert validator.is_null("20220101") is False
