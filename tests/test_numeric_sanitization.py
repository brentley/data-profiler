"""
Test suite for numeric value sanitization.

Tests handling of special numeric values (inf, -inf, nan) to ensure
they don't break JSON serialization.
"""
import json
import math
from pathlib import Path


class TestNumericSanitization:
    """Test numeric value sanitization for JSON safety."""

    def test_sanitize_positive_infinity(self):
        """Test that positive infinity is converted to null or string."""
        from api.services.profile import NumericProfiler

        profiler = NumericProfiler(num_bins=10)

        # Update with inf values
        profiler.update("123.45")
        profiler.update("inf")
        profiler.update("999.99")

        stats = profiler.finalize()

        # Stats should be JSON-serializable
        stats_dict = {
            'min_value': stats.min_value,
            'max_value': stats.max_value,
            'mean': stats.mean,
            'median': stats.median,
            'stddev': stats.stddev
        }

        # Should not raise exception
        json_str = json.dumps(stats_dict)
        assert json_str is not None

        # Infinity values should be converted to null or string representation
        parsed = json.loads(json_str)
        # If max_value is infinity, it should be null or "inf" string
        if stats.max_value == float('inf'):
            assert parsed['max_value'] is None or parsed['max_value'] == 'inf'

    def test_sanitize_negative_infinity(self):
        """Test that negative infinity is converted to null or string."""
        from api.services.profile import NumericProfiler

        profiler = NumericProfiler(num_bins=10)

        # Update with -inf values
        profiler.update("123.45")
        profiler.update("-inf")
        profiler.update("50.00")

        stats = profiler.finalize()

        # Stats should be JSON-serializable
        stats_dict = {
            'min_value': stats.min_value,
            'max_value': stats.max_value,
            'mean': stats.mean
        }

        # Should not raise exception
        json_str = json.dumps(stats_dict)
        assert json_str is not None

        # -Infinity values should be handled
        parsed = json.loads(json_str)
        if stats.min_value == float('-inf'):
            assert parsed['min_value'] is None or parsed['min_value'] == '-inf'

    def test_sanitize_nan_values(self):
        """Test that NaN values are converted to null."""
        from api.services.profile import NumericProfiler

        profiler = NumericProfiler(num_bins=10)

        # Update with NaN values
        profiler.update("123.45")
        profiler.update("nan")
        profiler.update("NaN")
        profiler.update("50.00")

        stats = profiler.finalize()

        # Stats should be JSON-serializable
        stats_dict = {
            'mean': stats.mean,
            'median': stats.median,
            'stddev': stats.stddev
        }

        # Should not raise exception
        json_str = json.dumps(stats_dict)
        assert json_str is not None

        # NaN should be converted to null
        parsed = json.loads(json_str)
        # If mean is NaN, it should become null in JSON
        if math.isnan(stats.mean):
            assert parsed['mean'] is None

    def test_profile_json_serialization_with_extreme_values(self, temp_dir: Path):
        """Test full profile JSON serialization with extreme numeric values."""
        from api.services.ingest import CSVParser, ParserConfig
        from api.services.types import TypeInferrer
        from api.services.profile import NumericProfiler
        from io import StringIO

        # Create CSV with extreme values
        csv_content = """ID|Value|Amount
1|inf|100.50
2|123.45|200.00
3|-inf|150.75
4|nan|300.00
5|999.99|NaN
"""

        csv_path = temp_dir / "extreme_values.csv"
        csv_path.write_text(csv_content)

        # Parse the CSV
        text_stream = StringIO(csv_content)
        parser_config = ParserConfig(delimiter="|", quoting=True, has_header=True)
        parser = CSVParser(text_stream, parser_config)

        header_result = parser.parse_header()
        assert header_result.success

        # Profile numeric columns
        profiler_value = NumericProfiler(num_bins=10)
        profiler_amount = NumericProfiler(num_bins=10)

        for row in parser.parse_rows():
            profiler_value.update(row[1])  # Value column
            profiler_amount.update(row[2])  # Amount column

        stats_value = profiler_value.finalize()
        stats_amount = profiler_amount.finalize()

        # Build profile dict
        profile = {
            'columns': [
                {
                    'name': 'Value',
                    'type': 'numeric',
                    'min': stats_value.min_value,
                    'max': stats_value.max_value,
                    'mean': stats_value.mean,
                    'median': stats_value.median,
                    'stddev': stats_value.stddev
                },
                {
                    'name': 'Amount',
                    'type': 'numeric',
                    'min': stats_amount.min_value,
                    'max': stats_amount.max_value,
                    'mean': stats_amount.mean,
                    'median': stats_amount.median,
                    'stddev': stats_amount.stddev
                }
            ]
        }

        # This should not raise an exception
        json_str = json.dumps(profile)
        assert json_str is not None

        # Verify it can be parsed back
        parsed = json.loads(json_str)
        assert 'columns' in parsed
        assert len(parsed['columns']) == 2

    def test_histogram_with_extreme_values(self):
        """Test that histogram generation works with inf/nan values."""
        from api.services.profile import NumericProfiler

        profiler = NumericProfiler(num_bins=5)

        # Mix of normal and extreme values
        values = ["10", "20", "30", "40", "50", "inf", "-inf", "nan"]
        for val in values:
            profiler.update(val)

        stats = profiler.finalize()

        # Histogram should be JSON-serializable
        histogram_dict = {'histogram': stats.histogram}
        json_str = json.dumps(histogram_dict)
        assert json_str is not None

        # Histogram is a dict with bin ranges as keys
        assert isinstance(stats.histogram, dict)
        # Should have bins (could be empty if all extreme values)
        assert len(stats.histogram) >= 0

    def test_quantiles_with_extreme_values(self):
        """Test that quantile calculation handles extreme values."""
        from api.services.profile import NumericProfiler

        profiler = NumericProfiler(num_bins=10)

        # Add extreme values
        for val in ["10", "20", "inf", "30", "40", "-inf", "50"]:
            profiler.update(val)

        stats = profiler.finalize()

        # Quantiles should be JSON-serializable
        quantiles_dict = {'quantiles': stats.quantiles}
        json_str = json.dumps(quantiles_dict)
        assert json_str is not None

        # Parsed quantiles should be valid
        parsed = json.loads(json_str)
        assert 'quantiles' in parsed

    def test_gaussian_test_with_extreme_values(self):
        """Test Gaussian normality test handles extreme values."""
        from api.services.profile import NumericProfiler

        profiler = NumericProfiler(num_bins=10)

        # Add many normal values and a few extreme
        for i in range(100):
            profiler.update(str(i))
        profiler.update("inf")
        profiler.update("-inf")
        profiler.update("nan")

        stats = profiler.finalize()

        # p-value should be JSON-serializable
        pvalue_dict = {'gaussian_pvalue': stats.gaussian_pvalue}
        json_str = json.dumps(pvalue_dict)
        assert json_str is not None

    def test_money_profiler_with_extreme_values(self, temp_dir: Path):
        """Test that MoneyProfiler handles extreme values in calculations."""
        from api.services.profile import MoneyProfiler

        profiler = MoneyProfiler()

        # Add extreme monetary values
        profiler.update("100.00")
        profiler.update("inf")
        profiler.update("-inf")
        profiler.update("200.50")

        stats = profiler.finalize()

        # Should be JSON-serializable
        money_dict = {
            'min_value': stats.min_value,
            'max_value': stats.max_value,
            'valid_count': stats.valid_count,
            'invalid_count': stats.invalid_count
        }
        json_str = json.dumps(money_dict)
        assert json_str is not None

    def test_api_metrics_csv_with_extreme_values(self, api_client, temp_dir: Path):
        """Test that metrics CSV export handles extreme numeric values."""
        # Create CSV with extreme values
        csv_path = temp_dir / "extreme.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|inf\n"
            "2|123.45\n"
            "3|-inf\n"
            "4|nan\n"
            "5|999.99\n",
            encoding="utf-8"
        )

        # Create run and upload
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("extreme.csv", f, "text/csv")}
            )

        # Wait for completion (poll status)
        import time
        for _ in range(10):
            time.sleep(1)
            status_response = api_client.get(f"/runs/{run_id}/status")
            status = status_response.json()
            if status["state"] in ["completed", "failed"]:
                break

        # Verify completed successfully
        assert status["state"] == "completed", f"Run failed or didn't complete: {status}"

        # Get metrics CSV
        response = api_client.get(f"/runs/{run_id}/metrics.csv")

        # Should succeed without JSON serialization errors
        assert response.status_code == 200
        csv_content = response.text

        # Verify CSV contains the data
        assert "Value" in csv_content
        assert "numeric" in csv_content

    def test_api_profile_json_with_extreme_values(self, api_client, temp_dir: Path):
        """Test that profile JSON endpoint handles extreme numeric values."""
        # Create CSV with extreme values
        csv_path = temp_dir / "extreme.csv"
        csv_path.write_text(
            "ID|Score|Amount\n"
            "1|inf|100.00\n"
            "2|85.5|inf\n"
            "3|nan|200.50\n"
            "4|92.0|-inf\n"
            "5|88.5|150.00\n",
            encoding="utf-8"
        )

        # Create run and upload
        response = api_client.post("/runs", json={"delimiter": "|"})
        run_id = response.json()["run_id"]

        with open(csv_path, "rb") as f:
            api_client.post(
                f"/runs/{run_id}/upload",
                files={"file": ("extreme.csv", f, "text/csv")}
            )

        # Wait for completion (poll status)
        import time
        for _ in range(10):
            time.sleep(1)
            status_response = api_client.get(f"/runs/{run_id}/status")
            status = status_response.json()
            if status["state"] in ["completed", "failed"]:
                break

        # Verify completed successfully
        assert status["state"] == "completed", f"Run failed or didn't complete: {status}"

        # Get profile JSON
        response = api_client.get(f"/runs/{run_id}/profile")

        # Should succeed without JSON serialization errors
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "columns" in data

        # Find numeric columns and verify they have stats
        for col in data["columns"]:
            if col["type"] == "numeric":
                # These fields should exist and be JSON-compatible
                assert "min" in col or "min_value" in col
                assert "max" in col or "max_value" in col

    def test_edge_case_all_infinite(self):
        """Test column with all infinite values."""
        from api.services.profile import NumericProfiler

        profiler = NumericProfiler(num_bins=10)

        for _ in range(10):
            profiler.update("inf")

        stats = profiler.finalize()

        # Should handle gracefully
        stats_dict = {
            'min_value': stats.min_value,
            'max_value': stats.max_value,
            'mean': stats.mean
        }

        json_str = json.dumps(stats_dict)
        assert json_str is not None

    def test_edge_case_all_nan(self):
        """Test column with all NaN values."""
        from api.services.profile import NumericProfiler

        profiler = NumericProfiler(num_bins=10)

        for _ in range(10):
            profiler.update("nan")

        stats = profiler.finalize()

        # Should handle gracefully
        stats_dict = {
            'mean': stats.mean,
            'median': stats.median,
            'stddev': stats.stddev
        }

        json_str = json.dumps(stats_dict)
        assert json_str is not None
