"""
Tests for CodeProfiler.

Tests profiling of dictionary-like columns with limited distinct values.
"""

import pytest
from services.profile import CodeProfiler, CodeStats


class TestCodeProfiler:
    """Test CodeProfiler for dictionary-like columns."""

    def test_basic_profiling(self):
        """Should profile basic code column."""
        profiler = CodeProfiler()

        profiler.update("ACTIVE")
        profiler.update("INACTIVE")
        profiler.update("ACTIVE")
        profiler.update("PENDING")
        profiler.update("ACTIVE")

        result = profiler.finalize()

        assert result.count == 5
        assert result.null_count == 0
        assert result.distinct_count == 3

    def test_frequency_distribution(self):
        """Should compute frequency distribution."""
        profiler = CodeProfiler()

        profiler.update("RED")
        profiler.update("BLUE")
        profiler.update("RED")
        profiler.update("GREEN")
        profiler.update("RED")

        result = profiler.finalize()

        assert result.value_distribution["RED"] == 3
        assert result.value_distribution["BLUE"] == 1
        assert result.value_distribution["GREEN"] == 1

    def test_top_values(self):
        """Should return top N most frequent values."""
        profiler = CodeProfiler(top_n=2)

        profiler.update("A")
        profiler.update("B")
        profiler.update("A")
        profiler.update("C")
        profiler.update("A")
        profiler.update("B")

        result = profiler.finalize()

        # top_n=2 so we get top 2 values
        assert len(result.top_values) == 2
        assert result.top_values[0] == ("A", 3)
        assert result.top_values[1] == ("B", 2)

    def test_cardinality_ratio(self):
        """Should compute cardinality ratio."""
        profiler = CodeProfiler()

        # 3 distinct values out of 10 total = 0.3
        profiler.update("X")
        profiler.update("Y")
        profiler.update("Z")
        profiler.update("X")
        profiler.update("Y")
        profiler.update("Z")
        profiler.update("X")
        profiler.update("Y")
        profiler.update("Z")
        profiler.update("X")

        result = profiler.finalize()

        assert result.distinct_count == 3
        assert result.count == 10
        assert result.cardinality_ratio == 0.3

    def test_null_handling(self):
        """Should handle null values."""
        profiler = CodeProfiler()

        profiler.update("ACTIVE")
        profiler.update("")
        profiler.update("INACTIVE")
        profiler.update(None)
        profiler.update("ACTIVE")

        result = profiler.finalize()

        assert result.count == 5
        assert result.null_count == 2
        assert result.distinct_count == 2

    def test_length_statistics(self):
        """Should compute length statistics."""
        profiler = CodeProfiler()

        profiler.update("A")
        profiler.update("BB")
        profiler.update("CCC")
        profiler.update("A")

        result = profiler.finalize()

        assert result.min_length == 1
        assert result.max_length == 3
        assert result.avg_length == 1.75  # (1+2+3+1)/4

    def test_empty_column(self):
        """Should handle empty column."""
        profiler = CodeProfiler()

        result = profiler.finalize()

        assert result.count == 0
        assert result.null_count == 0
        assert result.distinct_count == 0
        assert result.cardinality_ratio == 0.0

    def test_all_nulls(self):
        """Should handle all null values."""
        profiler = CodeProfiler()

        profiler.update("")
        profiler.update(None)
        profiler.update("")

        result = profiler.finalize()

        assert result.count == 3
        assert result.null_count == 3
        assert result.distinct_count == 0

    def test_single_value(self):
        """Should handle single distinct value."""
        profiler = CodeProfiler()

        profiler.update("SAME")
        profiler.update("SAME")
        profiler.update("SAME")

        result = profiler.finalize()

        assert result.distinct_count == 1
        assert result.cardinality_ratio == 1.0 / 3.0
        assert result.value_distribution["SAME"] == 3

    def test_all_unique_values(self):
        """Should handle all unique values."""
        profiler = CodeProfiler()

        profiler.update("A")
        profiler.update("B")
        profiler.update("C")
        profiler.update("D")

        result = profiler.finalize()

        assert result.distinct_count == 4
        assert result.cardinality_ratio == 1.0
        assert len(result.value_distribution) == 4

    def test_case_sensitivity(self):
        """Should treat different cases as different values."""
        profiler = CodeProfiler()

        profiler.update("active")
        profiler.update("ACTIVE")
        profiler.update("Active")
        profiler.update("active")

        result = profiler.finalize()

        assert result.distinct_count == 3
        assert result.value_distribution["active"] == 2
        assert result.value_distribution["ACTIVE"] == 1
        assert result.value_distribution["Active"] == 1

    def test_whitespace_trimming(self):
        """Should trim whitespace from values."""
        profiler = CodeProfiler()

        profiler.update("  ACTIVE  ")
        profiler.update("ACTIVE")
        profiler.update(" ACTIVE ")

        result = profiler.finalize()

        assert result.distinct_count == 1
        assert result.value_distribution["ACTIVE"] == 3

    def test_top_n_parameter(self):
        """Should respect top_n parameter."""
        profiler = CodeProfiler(top_n=3)

        for i in range(10):
            profiler.update(f"CODE_{i}")

        result = profiler.finalize()

        # top_n=3 so we get top 3 values
        assert len(result.top_values) == 3
        assert result.distinct_count == 10

    def test_top_n_with_ties(self):
        """Should handle ties in top N values."""
        profiler = CodeProfiler(top_n=2)

        profiler.update("A")
        profiler.update("B")
        profiler.update("C")
        profiler.update("A")
        profiler.update("B")
        profiler.update("C")

        result = profiler.finalize()

        # top_n=2 so we get top 2 values (Counter.most_common handles ties arbitrarily)
        assert len(result.top_values) == 2
        for value, count in result.top_values:
            assert count == 2

    def test_numeric_codes(self):
        """Should handle numeric codes as strings."""
        profiler = CodeProfiler()

        profiler.update("001")
        profiler.update("002")
        profiler.update("001")
        profiler.update("003")

        result = profiler.finalize()

        assert result.distinct_count == 3
        assert result.value_distribution["001"] == 2
        assert result.value_distribution["002"] == 1
        assert result.value_distribution["003"] == 1

    def test_special_characters(self):
        """Should handle special characters in codes."""
        profiler = CodeProfiler()

        profiler.update("STATUS-1")
        profiler.update("STATUS_2")
        profiler.update("STATUS-1")
        profiler.update("STATUS.3")

        result = profiler.finalize()

        assert result.distinct_count == 3
        assert result.value_distribution["STATUS-1"] == 2

    def test_large_dictionary(self):
        """Should handle larger dictionaries efficiently."""
        profiler = CodeProfiler(top_n=10)

        # Simulate a state code dictionary (50 states, each appearing multiple times)
        states = ["CA", "TX", "NY", "FL", "PA"]
        for state in states:
            for _ in range(20):
                profiler.update(state)

        result = profiler.finalize()

        assert result.distinct_count == 5
        assert result.count == 100
        assert result.cardinality_ratio == 0.05
        assert len(result.top_values) == 5

    def test_empty_string_after_trim(self):
        """Should handle empty strings after trimming as nulls."""
        profiler = CodeProfiler()

        profiler.update("   ")
        profiler.update("\t")
        profiler.update("ACTIVE")

        result = profiler.finalize()

        assert result.null_count == 2
        assert result.distinct_count == 1
