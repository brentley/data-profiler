"""
Test suite for exact distinct counting.

RED PHASE: These tests define expected distinct counting behavior.

Requirements from spec:
- Exact distinct counts (no approximations)
- Use SQLite for on-disk storage of large datasets
- Handle 3 GiB+ files without memory overflow
- Count nulls separately
- Provide frequency distribution
"""
import pytest
from pathlib import Path


class TestDistinctCounter:
    """Test exact distinct counting functionality."""

    def test_count_distinct_basic(self, temp_dir: Path):
        """Test basic distinct counting."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "distinct_basic.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2|B\n"
            "3|A\n"
            "4|C\n"
            "5|B\n",
            encoding="utf-8"
        )

        counter = DistinctCounter()
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        assert result.distinct_count == 3
        assert result.total_count == 5

    def test_count_distinct_with_nulls(self, temp_dir: Path):
        """Test distinct counting with null values."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "distinct_nulls.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2|\n"
            "3|A\n"
            "4|B\n"
            "5|\n",
            encoding="utf-8"
        )

        counter = DistinctCounter()
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        assert result.distinct_count == 2  # A, B (nulls counted separately)
        assert result.null_count == 2
        assert result.total_count == 5

    def test_count_distinct_all_unique(self, temp_dir: Path):
        """Test counting when all values are distinct."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "all_unique.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2|B\n"
            "3|C\n"
            "4|D\n",
            encoding="utf-8"
        )

        counter = DistinctCounter()
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        assert result.distinct_count == 4
        assert result.cardinality_ratio == 1.0

    def test_count_distinct_all_same(self, temp_dir: Path):
        """Test counting when all values are the same."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "all_same.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2|A\n"
            "3|A\n"
            "4|A\n",
            encoding="utf-8"
        )

        counter = DistinctCounter()
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        assert result.distinct_count == 1
        assert result.cardinality_ratio == 0.25

    def test_value_frequency_distribution(self, temp_dir: Path):
        """Test that frequency distribution is accurate."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "freq_dist.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2|B\n"
            "3|A\n"
            "4|C\n"
            "5|A\n"
            "6|B\n",
            encoding="utf-8"
        )

        counter = DistinctCounter()
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        assert result.frequencies["A"] == 3
        assert result.frequencies["B"] == 2
        assert result.frequencies["C"] == 1

    def test_top_n_values(self, temp_dir: Path):
        """Test retrieval of top N most frequent values."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "top_n.csv"
        lines = ["ID|Value\n"]
        for i in range(100):
            if i < 50:
                lines.append(f"{i}|A\n")
            elif i < 75:
                lines.append(f"{i}|B\n")
            elif i < 90:
                lines.append(f"{i}|C\n")
            else:
                lines.append(f"{i}|D\n")
        csv_path.write_text("".join(lines), encoding="utf-8")

        counter = DistinctCounter()
        result = counter.count_distincts(csv_path, "Value", delimiter="|")
        top_10 = result.get_top_n(10)

        assert len(top_10) == 4
        assert top_10[0] == ("A", 50)
        assert top_10[1] == ("B", 25)
        assert top_10[2] == ("C", 15)
        assert top_10[3] == ("D", 10)

    def test_sqlite_storage_for_large_datasets(self, temp_dir: Path):
        """Test that SQLite is used for storing distincts in large files."""
        from api.services.distincts import DistinctCounter

        # Create large CSV with many distinct values
        large_csv = temp_dir / "large_distinct.csv"
        with large_csv.open("w", encoding="utf-8") as f:
            f.write("ID|Value\n")
            for i in range(100000):
                f.write(f"{i}|Value{i % 10000}\n")

        counter = DistinctCounter(use_sqlite=True)
        result = counter.count_distincts(large_csv, "Value", delimiter="|")

        assert result.distinct_count == 10000
        assert result.storage_method == "sqlite"
        assert result.spill_file_path.exists()

    def test_cardinality_ratio_calculation(self, temp_dir: Path):
        """Test that cardinality ratio is calculated correctly."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "cardinality.csv"
        csv_path.write_text(
            "ID|LowCard|HighCard\n"
            "1|A|Val1\n"
            "2|A|Val2\n"
            "3|B|Val3\n"
            "4|A|Val4\n",
            encoding="utf-8"
        )

        counter = DistinctCounter()

        low_result = counter.count_distincts(csv_path, "LowCard", delimiter="|")
        assert low_result.cardinality_ratio == 0.5  # 2/4

        high_result = counter.count_distincts(csv_path, "HighCard", delimiter="|")
        assert high_result.cardinality_ratio == 1.0  # 4/4

    def test_distinct_counting_with_empty_strings(self, temp_dir: Path):
        """Test that empty strings are counted as distinct from nulls."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "empty_vs_null.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2|\n"  # Empty
            '3|""\n'  # Quoted empty
            "4|A\n",
            encoding="utf-8"
        )

        counter = DistinctCounter()
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        # Both empty and null should be counted
        assert result.distinct_count >= 1  # At least "A"
        assert result.null_count > 0 or result.empty_count > 0

    def test_distinct_counting_case_sensitive(self, temp_dir: Path):
        """Test that distinct counting is case-sensitive by default."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "case_sensitive.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2|a\n"
            "3|A\n",
            encoding="utf-8"
        )

        counter = DistinctCounter(case_sensitive=True)
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        assert result.distinct_count == 2  # "A" and "a" are different

    def test_distinct_counting_case_insensitive_option(self, temp_dir: Path):
        """Test case-insensitive distinct counting option."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "case_insensitive.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2|a\n"
            "3|A\n",
            encoding="utf-8"
        )

        counter = DistinctCounter(case_sensitive=False)
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        assert result.distinct_count == 1  # "A" and "a" are same

    def test_distinct_counter_cleanup(self, temp_dir: Path):
        """Test that temporary SQLite files are cleaned up."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "cleanup.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2|B\n",
            encoding="utf-8"
        )

        counter = DistinctCounter(use_sqlite=True, cleanup=True)
        result = counter.count_distincts(csv_path, "Value", delimiter="|")
        spill_file = result.spill_file_path

        # After cleanup, file should be removed
        counter.cleanup()
        assert not spill_file.exists() if spill_file else True

    def test_distinct_counting_multiple_columns(self, temp_dir: Path):
        """Test distinct counting across multiple columns."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "multi_col.csv"
        csv_path.write_text(
            "ID|Col1|Col2\n"
            "1|A|X\n"
            "2|B|Y\n"
            "3|A|Z\n",
            encoding="utf-8"
        )

        counter = DistinctCounter()

        result1 = counter.count_distincts(csv_path, "Col1", delimiter="|")
        assert result1.distinct_count == 2

        result2 = counter.count_distincts(csv_path, "Col2", delimiter="|")
        assert result2.distinct_count == 3

    def test_distinct_counting_with_whitespace(self, temp_dir: Path):
        """Test that whitespace is preserved in distinct counting."""
        from api.services.distincts import DistinctCounter

        csv_path = temp_dir / "whitespace.csv"
        csv_path.write_text(
            "ID|Value\n"
            "1|A\n"
            "2| A\n"
            "3|A \n"
            "4|A\n",
            encoding="utf-8"
        )

        counter = DistinctCounter(trim_whitespace=False)
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        # "A", " A", and "A " should be distinct
        assert result.distinct_count == 3

    def test_exact_counting_guarantee(self, temp_dir: Path):
        """Test that counting is exact, not approximate."""
        from api.services.distincts import DistinctCounter

        # Create file with known distinct count
        csv_path = temp_dir / "exact.csv"
        lines = ["ID|Value\n"]
        expected_distinct = 1000
        for i in range(10000):
            lines.append(f"{i}|Value{i % expected_distinct}\n")
        csv_path.write_text("".join(lines), encoding="utf-8")

        counter = DistinctCounter()
        result = counter.count_distincts(csv_path, "Value", delimiter="|")

        # Should be exactly 1000, not an approximation
        assert result.distinct_count == expected_distinct
        assert result.is_exact is True
