"""
Test suite for column type inference.

RED PHASE: These tests define expected type inference behavior.

Requirements from spec:
- Types: alpha, varchar, code, numeric, money, date, mixed, unknown
- Single detected type per column (or "mixed" if inconsistent)
- Numeric: digits and optional single .
- Money: exactly 2 decimals, no $, ,, or parentheses
- Date: prefer YYYYMMDD; otherwise one consistent format per column
- Code: string/dictionary-like
"""
import pytest
from pathlib import Path


class TestTypeInference:
    """Test type inference for CSV columns."""

    def test_infer_numeric_type(self, temp_dir: Path):
        """Test inference of numeric type."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "numeric.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|123\n"
            "2|456.78\n"
            "3|999\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        assert result.columns["Value"].inferred_type == "numeric"

    def test_infer_money_type(self, temp_dir: Path):
        """Test inference of money type (exactly 2 decimals)."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "money.csv"
        csv_path.write_text(
            "ID|Amount\n"
            "1|100.00\n"
            "2|250.50\n"
            "3|99.99\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        assert result.columns["Amount"].inferred_type == "money"

    def test_infer_date_type_yyyymmdd(self, temp_dir: Path):
        """Test inference of date type with YYYYMMDD format."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "date_yyyymmdd.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|20221109\n"
            "2|20230115\n"
            "3|20220301\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        assert result.columns["Date"].inferred_type == "date"
        assert result.columns["Date"].detected_format == "YYYYMMDD"

    def test_infer_date_type_other_format(self, temp_dir: Path):
        """Test inference of date type with non-YYYYMMDD format."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "date_other.csv"
        csv_path.write_text(
            "ID|Date\n"
            "1|2022-11-09\n"
            "2|2023-01-15\n"
            "3|2022-03-01\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        assert result.columns["Date"].inferred_type == "date"
        assert result.columns["Date"].detected_format in ["YYYY-MM-DD", "ISO8601"]

    def test_infer_alpha_type(self, temp_dir: Path):
        """Test inference of alpha (string) type."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "alpha.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Alice\n"
            "2|Bob\n"
            "3|Charlie\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        assert result.columns["Name"].inferred_type in ["alpha", "varchar"]

    def test_infer_varchar_type(self, temp_dir: Path):
        """Test inference of varchar (variable length string) type."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "varchar.csv"
        csv_path.write_text(
            "ID|Description\n"
            "1|Short\n"
            "2|This is a much longer description\n"
            "3|Medium length\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        assert result.columns["Description"].inferred_type in ["varchar", "alpha"]

    def test_infer_code_type(self, temp_dir: Path):
        """Test inference of code (dictionary-like) type."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "code.csv"
        csv_path.write_text(
            "ID|Status\n"
            "1|ACTIVE\n"
            "2|INACTIVE\n"
            "3|ACTIVE\n"
            "4|PENDING\n"
            "5|ACTIVE\n"
            "6|INACTIVE\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        # Code type should be detected when low cardinality relative to row count
        assert result.columns["Status"].inferred_type == "code"

    def test_infer_mixed_type(self, sample_csv_mixed_types: Path):
        """Test inference of mixed type when column has inconsistent types."""
        from api.services.types import TypeInferrer

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(sample_csv_mixed_types, delimiter="|")

        assert result.columns["MixedColumn"].inferred_type == "mixed"

    def test_infer_unknown_type(self, temp_dir: Path):
        """Test inference of unknown type when type cannot be determined."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "unknown.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|\n"
            "2|\n"
            "3|\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        # All null/empty values should result in unknown
        assert result.columns["Value"].inferred_type == "unknown"

    def test_numeric_excludes_values_with_commas(self, temp_dir: Path):
        """Test that numeric type excludes values with commas."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "numeric_with_comma.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|123\n"
            "2|1,456\n"  # Should be flagged as error
            "3|789\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        # Should still infer as numeric but flag the comma value as error
        assert result.columns["Value"].inferred_type in ["numeric", "mixed"]
        assert result.columns["Value"].error_count > 0

    def test_numeric_excludes_values_with_dollar_sign(self, temp_dir: Path):
        """Test that numeric type excludes values with dollar signs."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "numeric_with_dollar.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|123\n"
            "2|$456\n"  # Should be flagged as error
            "3|789\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        assert result.columns["Value"].inferred_type in ["numeric", "mixed"]
        assert result.columns["Value"].error_count > 0

    def test_numeric_allows_optional_single_decimal(self, temp_dir: Path):
        """Test that numeric allows optional single decimal point."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "numeric_decimal.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|123\n"
            "2|456.7\n"
            "3|789.12345\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        assert result.columns["Value"].inferred_type == "numeric"
        assert result.columns["Value"].error_count == 0

    def test_money_requires_exactly_two_decimals(self, temp_dir: Path):
        """Test that money type requires exactly 2 decimal places."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "money_decimals.csv"
        csv_path.write_text(
            "ID|Amount\n"
            "1|100.00\n"
            "2|250.5\n"   # Only 1 decimal - should be error
            "3|99.999\n"  # 3 decimals - should be error
            "4|1000\n",   # No decimals - should be error
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        # May infer as money or mixed depending on error threshold
        assert result.columns["Amount"].error_count >= 3

    def test_money_rejects_dollar_signs(self, sample_csv_money_violations: Path):
        """Test that money type rejects dollar signs."""
        from api.services.types import TypeInferrer

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(sample_csv_money_violations, delimiter="|")

        assert result.columns["InvalidAmount"].error_count >= 1
        # Should detect dollar sign violation

    def test_money_rejects_commas(self, sample_csv_money_violations: Path):
        """Test that money type rejects commas."""
        from api.services.types import TypeInferrer

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(sample_csv_money_violations, delimiter="|")

        # 1,250.50 should be rejected
        assert result.columns["InvalidAmount"].error_count >= 1

    def test_money_rejects_parentheses(self, sample_csv_money_violations: Path):
        """Test that money type rejects parentheses for negative values."""
        from api.services.types import TypeInferrer

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(sample_csv_money_violations, delimiter="|")

        # (99.99) should be rejected
        assert result.columns["InvalidAmount"].error_count >= 1

    def test_date_consistency_check(self, sample_csv_dates: Path):
        """Test that date format consistency is checked."""
        from api.services.types import TypeInferrer

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(sample_csv_dates, delimiter="|")

        # DateMixed has inconsistent formats
        assert result.columns["DateMixed"].warning_count > 0 or \
               result.columns["DateMixed"].inferred_type == "mixed"

    def test_date_yyyymmdd_preferred(self, temp_dir: Path):
        """Test that YYYYMMDD format is preferred for dates."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "date_formats.csv"
        csv_path.write_text(
            "ID|DateA|DateB\n"
            "1|20221109|2022-11-09\n"
            "2|20230115|2023-01-15\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        assert result.columns["DateA"].detected_format == "YYYYMMDD"
        assert result.columns["DateB"].detected_format != "YYYYMMDD"

    def test_type_inference_with_nulls(self, temp_dir: Path):
        """Test type inference correctly handles null values."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "with_nulls.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|100\n"
            "2|\n"
            "3|200\n"
            "4|\n"
            "5|300\n",
            encoding="utf-8"
        )

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        # Should infer as numeric despite nulls
        assert result.columns["Value"].inferred_type == "numeric"
        assert result.columns["Value"].null_count == 2

    def test_type_inference_sampling_strategy(self, temp_dir: Path):
        """Test that type inference can use sampling for large files."""
        from api.services.types import TypeInferrer

        large_csv = temp_dir / "large.csv"
        with large_csv.open("w", encoding="utf-8") as f:
            f.write("ID|Value\n")
            for i in range(100000):
                f.write(f"{i}|Value{i}\n")

        inferrer = TypeInferrer(sample_size=1000)
        result = inferrer.infer_column_types(large_csv, delimiter="|")

        # Should infer types using sample, not full scan
        assert result.columns["Value"].inferred_type in ["alpha", "varchar"]
        assert result.inference_method == "sample"

    def test_code_type_threshold(self, temp_dir: Path):
        """Test that code type is inferred based on cardinality threshold."""
        from api.services.types import TypeInferrer

        csv_path = temp_dir / "code_threshold.csv"
        lines = ["ID|Status\n"]
        # Create 100 rows with only 3 distinct values
        for i in range(100):
            status = ["ACTIVE", "INACTIVE", "PENDING"][i % 3]
            lines.append(f"{i}|{status}\n")
        csv_path.write_text("".join(lines), encoding="utf-8")

        inferrer = TypeInferrer()
        result = inferrer.infer_column_types(csv_path, delimiter="|")

        # Low cardinality (3/100 = 3%) should trigger code type
        assert result.columns["Status"].inferred_type == "code"
        assert result.columns["Status"].cardinality_ratio < 0.1
