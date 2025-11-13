"""
Test suite for date format validation and detection.

RED PHASE: These tests define expected date validation behavior.

Requirements from spec:
- Prefer YYYYMMDD format
- Accept other formats if consistent within column
- Detect format automatically
- Out-of-range warnings (year < 1900 or > current_year + 1)
- Allow nulls
- Mixed formats → error
"""
import pytest
from pathlib import Path
from datetime import datetime


class TestDateValidator:
    """Test date format validation and detection."""

    def test_valid_date_yyyymmdd(self):
        """Test that YYYYMMDD dates are validated correctly."""
        from api.services.validators import DateValidator

        validator = DateValidator()

        assert validator.is_valid("20221109", format_hint="YYYYMMDD") is True
        assert validator.is_valid("20230115", format_hint="YYYYMMDD") is True
        assert validator.is_valid("20000229", format_hint="YYYYMMDD") is True  # Leap year

    def test_invalid_date_yyyymmdd(self):
        """Test that invalid YYYYMMDD dates are rejected."""
        from api.services.validators import DateValidator

        validator = DateValidator()

        assert validator.is_valid("20221301", format_hint="YYYYMMDD") is False  # Month 13
        assert validator.is_valid("20220230", format_hint="YYYYMMDD") is False  # Feb 30
        assert validator.is_valid("20210229", format_hint="YYYYMMDD") is False  # Not leap year

    def test_detect_yyyymmdd_format(self, temp_dir: Path):
        """Test automatic detection of YYYYMMDD format."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_yyyymmdd.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|20221109\n"
            "2|20230115\n"
            "3|20220301\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        detected_format = validator.detect_format_from_file(csv_path, "Date", delimiter="|")

        assert detected_format == "YYYYMMDD"

    def test_detect_iso8601_format(self, temp_dir: Path):
        """Test automatic detection of ISO-8601 format (YYYY-MM-DD)."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_iso.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|2022-11-09\n"
            "2|2023-01-15\n"
            "3|2022-03-01\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        detected_format = validator.detect_format_from_file(csv_path, "Date", delimiter="|")

        assert detected_format in ["YYYY-MM-DD", "ISO8601"]

    def test_detect_us_format(self, temp_dir: Path):
        """Test automatic detection of US date format (MM/DD/YYYY)."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_us.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|11/09/2022\n"
            "2|01/15/2023\n"
            "3|03/01/2022\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        detected_format = validator.detect_format_from_file(csv_path, "Date", delimiter="|")

        assert detected_format in ["MM/DD/YYYY", "US"]

    def test_detect_european_format(self, temp_dir: Path):
        """Test automatic detection of European date format (DD/MM/YYYY)."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_eu.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|09/11/2022\n"
            "2|15/01/2023\n"
            "3|31/12/2022\n",  # Day 31 makes it unambiguous
            encoding="utf-8"
        )

        validator = DateValidator()
        detected_format = validator.detect_format_from_file(csv_path, "Date", delimiter="|")

        assert detected_format in ["DD/MM/YYYY", "EUROPEAN"]

    def test_consistent_format_within_column(self, temp_dir: Path):
        """Test that consistent date format is accepted."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_consistent.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|20221109\n"
            "2|20230115\n"
            "3|20220301\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        result = validator.validate_column_consistency(csv_path, "Date", delimiter="|")

        assert result.is_consistent is True
        assert len(result.format_violations) == 0

    def test_inconsistent_format_within_column(self, sample_csv_dates: Path):
        """Test that mixed date formats are flagged."""
        from api.services.validators import DateValidator

        validator = DateValidator()
        result = validator.validate_column_consistency(sample_csv_dates, "DateMixed", delimiter="|")

        assert result.is_consistent is False
        assert len(result.format_violations) > 0

    def test_out_of_range_year_too_old(self):
        """Test warning for dates with year < 1900."""
        from api.services.validators import DateValidator

        validator = DateValidator()

        result = validator.is_valid("18991231", format_hint="YYYYMMDD")
        assert result is True  # Valid format

        range_check = validator.check_range("18991231", format_hint="YYYYMMDD")
        assert range_check.in_range is False
        assert range_check.warning_reason == "year_too_old"

    def test_out_of_range_year_too_new(self):
        """Test warning for dates with year > current_year + 1."""
        from api.services.validators import DateValidator

        validator = DateValidator()
        current_year = datetime.now().year
        future_year = current_year + 2
        future_date = f"{future_year}0101"

        result = validator.is_valid(future_date, format_hint="YYYYMMDD")
        assert result is True  # Valid format

        range_check = validator.check_range(future_date, format_hint="YYYYMMDD")
        assert range_check.in_range is False
        assert range_check.warning_reason == "year_too_new"

    def test_in_range_dates(self):
        """Test that reasonable dates are in range."""
        from api.services.validators import DateValidator

        validator = DateValidator()

        dates = ["19500101", "20000101", "20221109", "20231231"]
        for date in dates:
            range_check = validator.check_range(date, format_hint="YYYYMMDD")
            assert range_check.in_range is True

    def test_null_dates_allowed(self, temp_dir: Path):
        """Test that null/empty dates are allowed."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_with_nulls.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|20221109\n"
            "2|\n"
            "3|20230115\n"
            "4|\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        result = validator.validate_column_consistency(csv_path, "Date", delimiter="|")

        assert result.is_consistent is True
        assert result.null_count == 2

    def test_date_parsing_to_datetime(self):
        """Test conversion of date strings to datetime objects."""
        from api.services.validators import DateValidator

        validator = DateValidator()

        dt1 = validator.parse_to_datetime("20221109", format_hint="YYYYMMDD")
        assert dt1.year == 2022
        assert dt1.month == 11
        assert dt1.day == 9

        dt2 = validator.parse_to_datetime("2022-11-09", format_hint="YYYY-MM-DD")
        assert dt2.year == 2022
        assert dt2.month == 11
        assert dt2.day == 9

    def test_date_min_max_detection(self, temp_dir: Path):
        """Test detection of min and max dates in column."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_minmax.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|20220101\n"
            "2|20221109\n"
            "3|20231231\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        result = validator.analyze_column(csv_path, "Date", delimiter="|")

        assert result.min_date == "20220101"
        assert result.max_date == "20231231"

    def test_date_distribution_by_year(self, temp_dir: Path):
        """Test date distribution analysis by year."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_dist.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|20210101\n"
            "2|20210615\n"
            "3|20220101\n"
            "4|20220301\n"
            "5|20230101\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        result = validator.analyze_column(csv_path, "Date", delimiter="|")

        assert result.distribution_by_year["2021"] == 2
        assert result.distribution_by_year["2022"] == 2
        assert result.distribution_by_year["2023"] == 1

    def test_date_distribution_by_month(self, temp_dir: Path):
        """Test date distribution analysis by month."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_month.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|20220101\n"
            "2|20220115\n"
            "3|20220201\n"
            "4|20220301\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        result = validator.analyze_column(csv_path, "Date", delimiter="|")

        assert result.distribution_by_month["01"] == 2
        assert result.distribution_by_month["02"] == 1
        assert result.distribution_by_month["03"] == 1

    def test_ambiguous_date_format(self, temp_dir: Path):
        """Test handling of ambiguous date formats."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_ambiguous.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|01/02/2022\n"  # Could be Jan 2 or Feb 1
            "2|03/04/2022\n"
            "3|05/06/2022\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        result = validator.detect_format_from_file(csv_path, "Date", delimiter="|")

        # Should detect but flag as ambiguous
        assert result.is_ambiguous is True or result.confidence < 1.0

    def test_yyyymmdd_preferred_over_others(self, temp_dir: Path):
        """Test that YYYYMMDD is recognized as preferred format."""
        from api.services.validators import DateValidator

        validator = DateValidator()

        # YYYYMMDD should have highest preference score
        assert validator.format_preference("YYYYMMDD") > validator.format_preference("YYYY-MM-DD")
        assert validator.format_preference("YYYYMMDD") > validator.format_preference("MM/DD/YYYY")

    def test_date_validation_with_gzip(self, temp_dir: Path):
        """Test date validation in gzipped files."""
        import gzip
        from api.services.validators import DateValidator

        gz_path = temp_dir / "dates.csv.gz"
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            f.write("ID|Date\n")
            f.write("1|20221109\n")
            f.write("2|20230115\n")

        validator = DateValidator()
        detected_format = validator.detect_format_from_file(gz_path, "Date", delimiter="|")

        assert detected_format == "YYYYMMDD"

    def test_date_format_inference_confidence(self, temp_dir: Path):
        """Test that date format detection includes confidence score."""
        from api.services.validators import DateValidator

        csv_path = temp_dir / "dates_conf.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|20221109\n"
            "2|20230115\n"
            "3|20220301\n"
            "4|20221225\n",
            encoding="utf-8"
        )

        validator = DateValidator()
        result = validator.detect_format_from_file(csv_path, "Date", delimiter="|")

        # High confidence for consistent YYYYMMDD
        assert result.confidence >= 0.95
