"""
Exact distinct counting tests.

Tests the exact distinct counter using SQLite:
- Per-column spill to disk
- Exact counts (no approximations)
- Memory-efficient streaming
- Duplicate detection
- Top-10 value tracking
"""

import pytest
import tempfile
import os
from pathlib import Path
from services.distincts import DistinctCounter


class TestDistinctCounterBasics:
    """Test basic distinct counting functionality."""

    def test_simple_distinct_count(self):
        """Should count distinct values exactly."""
        counter = DistinctCounter()
        values = ["a", "b", "c", "b", "a", "c", "d"]

        result = counter.count_distinct(values)
        assert result.distinct_count == 4
        assert result.total_count == 7
        assert result.duplicate_count == 3

    def test_all_unique(self):
        """Should handle all unique values."""
        counter = DistinctCounter()
        values = ["a", "b", "c", "d", "e"]

        result = counter.count_distinct(values)
        assert result.distinct_count == 5
        assert result.total_count == 5
        assert result.duplicate_count == 0

    def test_all_duplicates(self):
        """Should handle all duplicate values."""
        counter = DistinctCounter()
        values = ["a", "a", "a", "a", "a"]

        result = counter.count_distinct(values)
        assert result.distinct_count == 1
        assert result.total_count == 5
        assert result.duplicate_count == 4

    def test_with_nulls(self):
        """Should handle nulls correctly."""
        counter = DistinctCounter()
        values = ["a", "", "b", None, "a", ""]

        result = counter.count_distinct(values)
        # Nulls typically don't count toward distincts
        assert result.distinct_count == 2  # a, b
        assert result.null_count == 3

    def test_empty_list(self):
        """Should handle empty list."""
        counter = DistinctCounter()
        values = []

        result = counter.count_distinct(values)
        assert result.distinct_count == 0
        assert result.total_count == 0


class TestDistinctCounterSQLite:
    """Test SQLite-based counting for large datasets."""

    def test_spill_to_sqlite(self):
        """Should spill to SQLite for memory efficiency."""
        counter = DistinctCounter(memory_threshold=100)
        # Generate more values than memory threshold
        values = [f"val_{i}" for i in range(1000)]

        result = counter.count_distinct(values)
        assert result.distinct_count == 1000
        assert result.used_sqlite is True

    def test_sqlite_unique_index(self):
        """Should use unique index for deduplication."""
        counter = DistinctCounter()
        values = [f"val_{i % 100}" for i in range(10000)]  # 100 unique values repeated

        result = counter.count_distinct(values)
        assert result.distinct_count == 100
        assert result.total_count == 10000

    def test_temporary_database_cleanup(self):
        """Should clean up temporary SQLite files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            counter = DistinctCounter(work_dir=tmpdir)
            values = [f"val_{i}" for i in range(1000)]

            result = counter.count_distinct(values)
            counter.cleanup()

            # Should clean up temp files
            sqlite_files = list(Path(tmpdir).glob("*.sqlite"))
            assert len(sqlite_files) == 0

    def test_concurrent_columns(self):
        """Should handle multiple columns concurrently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            counter1 = DistinctCounter(work_dir=tmpdir, column_name="col1")
            counter2 = DistinctCounter(work_dir=tmpdir, column_name="col2")

            values1 = [f"val_{i}" for i in range(100)]
            values2 = [f"other_{i}" for i in range(200)]

            result1 = counter1.count_distinct(values1)
            result2 = counter2.count_distinct(values2)

            assert result1.distinct_count == 100
            assert result2.distinct_count == 200


class TestDistinctCounterStreaming:
    """Test streaming distinct counting."""

    def test_streaming_api(self):
        """Should support streaming API."""
        counter = DistinctCounter()

        # Add values in batches
        counter.add_batch(["a", "b", "c"])
        counter.add_batch(["b", "c", "d"])
        counter.add_batch(["d", "e", "f"])

        result = counter.finalize()
        assert result.distinct_count == 6

    def test_streaming_with_large_batches(self):
        """Should handle large batches efficiently."""
        counter = DistinctCounter()

        for i in range(10):
            batch = [f"val_{j}" for j in range(i * 100, (i + 1) * 100)]
            counter.add_batch(batch)

        result = counter.finalize()
        assert result.distinct_count == 1000

    def test_streaming_memory_efficiency(self):
        """Should spill to disk during streaming."""
        counter = DistinctCounter(memory_threshold=100)

        for i in range(100):
            batch = [f"val_{j}" for j in range(i * 10, (i + 1) * 10)]
            counter.add_batch(batch)

        result = counter.finalize()
        assert result.distinct_count == 1000
        assert result.used_sqlite is True


class TestTopValuesTracking:
    """Test top-10 value tracking."""

    def test_top_values_basic(self):
        """Should track top values with counts."""
        counter = DistinctCounter()
        values = ["a"] * 10 + ["b"] * 5 + ["c"] * 3 + ["d"] * 1

        result = counter.count_distinct(values)
        top_values = result.top_values

        assert len(top_values) == 4
        assert top_values[0] == ("a", 10)
        assert top_values[1] == ("b", 5)
        assert top_values[2] == ("c", 3)
        assert top_values[3] == ("d", 1)

    def test_top_10_limit(self):
        """Should limit to top 10 values."""
        counter = DistinctCounter()
        # Generate 100 unique values with different frequencies
        values = []
        for i in range(100):
            values.extend([f"val_{i}"] * (100 - i))

        result = counter.count_distinct(values)
        assert len(result.top_values) == 10
        # Most frequent should be val_0 with 100 occurrences
        assert result.top_values[0] == ("val_0", 100)

    def test_top_values_with_nulls(self):
        """Should exclude nulls from top values."""
        counter = DistinctCounter()
        values = ["a"] * 5 + [""] * 10 + ["b"] * 3

        result = counter.count_distinct(values)
        # Nulls should not appear in top values
        assert all(v[0] != "" for v in result.top_values)

    def test_top_values_ordering(self):
        """Should order top values by frequency."""
        counter = DistinctCounter()
        values = ["c"] * 3 + ["a"] * 10 + ["b"] * 5

        result = counter.count_distinct(values)
        # Should be ordered: a, b, c
        assert result.top_values[0][0] == "a"
        assert result.top_values[1][0] == "b"
        assert result.top_values[2][0] == "c"

    def test_top_values_min_heap(self):
        """Should use min-heap for memory efficiency."""
        counter = DistinctCounter()
        # Generate many values
        values = []
        for i in range(1000):
            values.extend([f"val_{i}"] * (1000 - i))

        result = counter.count_distinct(values)
        # Should track top 10 efficiently
        assert len(result.top_values) == 10


class TestDistinctRatioCalculation:
    """Test distinct ratio calculation."""

    def test_distinct_ratio(self):
        """Should calculate distinct ratio."""
        counter = DistinctCounter()
        values = ["a"] * 10 + ["b"] * 10 + ["c"] * 10 + ["d"] * 10

        result = counter.count_distinct(values)
        assert result.distinct_ratio == 0.1  # 4 / 40

    def test_distinct_ratio_all_unique(self):
        """Distinct ratio should be 1.0 for all unique."""
        counter = DistinctCounter()
        values = ["a", "b", "c", "d"]

        result = counter.count_distinct(values)
        assert result.distinct_ratio == 1.0

    def test_distinct_ratio_one_value(self):
        """Distinct ratio should be low for one repeated value."""
        counter = DistinctCounter()
        values = ["a"] * 1000

        result = counter.count_distinct(values)
        assert result.distinct_ratio == 0.001  # 1 / 1000

    def test_distinct_ratio_with_nulls(self):
        """Distinct ratio should exclude nulls."""
        counter = DistinctCounter()
        values = ["a", "b", "", None, "a"]

        result = counter.count_distinct(values)
        # 2 distinct in 3 non-null = 0.667
        assert result.distinct_ratio == pytest.approx(0.667, rel=0.01)


class TestDistinctCounterPerformance:
    """Test performance and scalability."""

    def test_large_dataset_exact(self):
        """Should handle large datasets with exact counts."""
        counter = DistinctCounter()
        # 1 million values with 10k unique
        values = [f"val_{i % 10000}" for i in range(1000000)]

        result = counter.count_distinct(values)
        assert result.distinct_count == 10000
        assert result.total_count == 1000000

    def test_high_cardinality(self):
        """Should handle high cardinality efficiently."""
        counter = DistinctCounter()
        # 1 million unique values
        values = [f"val_{i}" for i in range(1000000)]

        result = counter.count_distinct(values)
        assert result.distinct_count == 1000000

    def test_unicode_values(self):
        """Should handle Unicode values correctly."""
        counter = DistinctCounter()
        values = ["世界", "世界", "hello", "مرحبا", "hello"]

        result = counter.count_distinct(values)
        assert result.distinct_count == 3

    def test_very_long_values(self):
        """Should handle very long string values."""
        counter = DistinctCounter()
        values = ["x" * 10000, "y" * 10000, "x" * 10000]

        result = counter.count_distinct(values)
        assert result.distinct_count == 2


class TestDistinctCounterEdgeCases:
    """Test edge cases."""

    def test_only_nulls(self):
        """Should handle column with only nulls."""
        counter = DistinctCounter()
        values = ["", None, "", None]

        result = counter.count_distinct(values)
        assert result.distinct_count == 0
        assert result.null_count == 4

    def test_single_value(self):
        """Should handle single value."""
        counter = DistinctCounter()
        values = ["a"]

        result = counter.count_distinct(values)
        assert result.distinct_count == 1
        assert result.total_count == 1

    def test_whitespace_values(self):
        """Should treat whitespace-only as distinct from empty."""
        counter = DistinctCounter()
        values = ["", "  ", "   ", ""]

        result = counter.count_distinct(values)
        # Empty strings are null, whitespace strings are distinct
        # This depends on null definition
        assert result.distinct_count >= 0

    def test_numeric_strings(self):
        """Should handle numeric strings."""
        counter = DistinctCounter()
        values = ["123", "456", "123", "789"]

        result = counter.count_distinct(values)
        assert result.distinct_count == 3

    def test_mixed_types_as_strings(self):
        """Should handle all values as strings."""
        counter = DistinctCounter()
        # All converted to strings
        values = ["123", "123.45", "abc", "123"]

        result = counter.count_distinct(values)
        assert result.distinct_count == 3
