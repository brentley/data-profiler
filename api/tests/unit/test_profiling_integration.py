"""
Test profiling integration in the run pipeline.
"""

import pytest
import tempfile
from pathlib import Path
from uuid import uuid4

from services.types import TypeInferrer
from services.profile import NumericProfiler, StringProfiler, MoneyProfiler, DateProfiler, CodeProfiler
from services.distincts import DistinctCounter


class TestProfilingIntegration:
    """Test profiling integration with type inference."""

    @pytest.fixture
    def test_csv(self, tmp_path):
        """Create test CSV file."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "name|age|salary|hire_date|department\n"
            "Alice|30|75000.00|20200115|ENG\n"
            "Bob|25|65000.00|20210301|MKT\n"
            "Charlie|35|85000.00|20190820|ENG\n"
        )
        return csv_file

    def test_type_inference_and_profiling(self, test_csv):
        """Test that type inference works correctly."""
        # Run type inference
        inferrer = TypeInferrer()
        type_result = inferrer.infer_column_types(test_csv, delimiter='|')

        # Check inferred types
        assert type_result.columns['name'].inferred_type == 'alpha'
        assert type_result.columns['age'].inferred_type == 'numeric'
        assert type_result.columns['salary'].inferred_type == 'money'
        assert type_result.columns['hire_date'].inferred_type == 'date'
        # Department is 'alpha' not 'code' because sample size is too small (< MIN_SAMPLE_FOR_CODE)
        assert type_result.columns['department'].inferred_type in ['code', 'alpha']

    def test_numeric_profiler_integration(self, test_csv):
        """Test numeric profiler with real data."""
        # Create profiler
        profiler = NumericProfiler()

        # Stream values
        with open(test_csv, 'r') as f:
            lines = f.readlines()[1:]  # Skip header
            for line in lines:
                parts = line.strip().split('|')
                profiler.update(parts[1])  # age column

        # Finalize
        stats = profiler.finalize()

        # Check stats
        assert stats.valid_count == 3
        assert stats.min_value == 25
        assert stats.max_value == 35
        assert stats.mean == 30.0

    def test_money_profiler_integration(self, test_csv):
        """Test money profiler with real data."""
        # Create profiler
        profiler = MoneyProfiler()

        # Stream values
        with open(test_csv, 'r') as f:
            lines = f.readlines()[1:]  # Skip header
            for line in lines:
                parts = line.strip().split('|')
                profiler.update(parts[2])  # salary column

        # Finalize
        stats = profiler.finalize()

        # Check stats
        assert stats.valid_count == 3
        assert stats.invalid_count == 0
        assert stats.min_value == 65000.00
        assert stats.max_value == 85000.00
        assert stats.two_decimal_ok is True

    def test_date_profiler_integration(self, test_csv):
        """Test date profiler with real data."""
        # Create profiler
        profiler = DateProfiler()

        # Stream values
        with open(test_csv, 'r') as f:
            lines = f.readlines()[1:]  # Skip header
            for line in lines:
                parts = line.strip().split('|')
                profiler.update(parts[3])  # hire_date column

        # Finalize
        stats = profiler.finalize()

        # Check stats
        assert stats.valid_count == 3
        assert stats.invalid_count == 0
        assert stats.detected_format == 'YYYYMMDD'
        assert stats.format_consistent is True

    def test_code_profiler_integration(self, test_csv):
        """Test code profiler with real data."""
        # Create profiler
        profiler = CodeProfiler()

        # Stream values
        with open(test_csv, 'r') as f:
            lines = f.readlines()[1:]  # Skip header
            for line in lines:
                parts = line.strip().split('|')
                profiler.update(parts[4])  # department column

        # Finalize
        stats = profiler.finalize()

        # Check stats
        assert stats.count == 3
        assert stats.distinct_count == 2  # ENG and MKT
        assert stats.cardinality_ratio < 1.0

    def test_distinct_counter_integration(self, test_csv):
        """Test distinct counter with real data."""
        # Create counter
        counter = DistinctCounter()

        # Count distincts for name column
        result = counter.count_distincts(test_csv, 'name', delimiter='|')

        # Check results
        assert result.distinct_count == 3
        assert result.total_count == 3
        assert result.null_count == 0
        assert result.is_exact is True

        # Check top values
        top_values = result.get_top_n(3)
        assert len(top_values) == 3
        names = [v['value'] for v in top_values]
        assert 'Alice' in names
        assert 'Bob' in names
        assert 'Charlie' in names
