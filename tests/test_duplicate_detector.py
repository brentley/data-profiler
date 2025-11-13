"""
Test suite for duplicate detection.

RED PHASE: These tests define expected duplicate detection behavior.

Requirements from spec:
- Detect duplicates based on single or compound keys
- User confirms candidate keys before duplicate check
- Use SQLite with hash-based approach for compound keys
- Report exact duplicate counts and row numbers
- Handle 3 GiB+ files efficiently
"""
import pytest
from pathlib import Path


class TestDuplicateDetector:
    """Test duplicate detection functionality."""

    def test_detect_duplicates_single_key(self, sample_csv_duplicates: Path):
        """Test duplicate detection with single column key."""
        from api.services.duplicates import DuplicateDetector

        detector = DuplicateDetector()
        result = detector.detect_duplicates(
            sample_csv_duplicates,
            keys=["ID"],
            delimiter="|"
        )

        assert result.duplicate_count == 2  # ID 1 and 2 appear twice
        assert len(result.duplicate_groups) == 2

    def test_detect_duplicates_compound_key(self, sample_csv_duplicates: Path):
        """Test duplicate detection with compound key."""
        from api.services.duplicates import DuplicateDetector

        detector = DuplicateDetector()
        result = detector.detect_duplicates(
            sample_csv_duplicates,
            keys=["ID", "Name"],
            delimiter="|"
        )

        # ID+Name combination duplicated
        assert result.duplicate_count >= 2
        assert len(result.duplicate_groups) >= 1

    def test_detect_duplicates_no_duplicates(self, temp_dir: Path):
        """Test duplicate detection when no duplicates exist."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "no_dupes.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Alice\n"
            "2|Bob\n"
            "3|Charlie\n",
            encoding="utf-8"
        )

        detector = DuplicateDetector()
        result = detector.detect_duplicates(csv_path, keys=["ID"], delimiter="|")

        assert result.duplicate_count == 0
        assert len(result.duplicate_groups) == 0

    def test_detect_duplicates_all_duplicates(self, temp_dir: Path):
        """Test detection when all rows are duplicates."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "all_dupes.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Alice\n"
            "1|Alice\n"
            "1|Alice\n",
            encoding="utf-8"
        )

        detector = DuplicateDetector()
        result = detector.detect_duplicates(csv_path, keys=["ID", "Name"], delimiter="|")

        assert result.duplicate_count == 2  # 2 duplicates (3 total - 1 original)
        assert len(result.duplicate_groups) == 1
        assert result.duplicate_groups[0].count == 3

    def test_duplicate_detection_reports_row_numbers(self, sample_csv_duplicates: Path):
        """Test that duplicate detection reports exact row numbers."""
        from api.services.duplicates import DuplicateDetector

        detector = DuplicateDetector()
        result = detector.detect_duplicates(
            sample_csv_duplicates,
            keys=["ID"],
            delimiter="|"
        )

        # Should report which rows are duplicates
        for group in result.duplicate_groups:
            assert len(group.row_numbers) >= 2
            assert all(isinstance(row_num, int) for row_num in group.row_numbers)

    def test_duplicate_detection_with_nulls(self, temp_dir: Path):
        """Test duplicate detection when key columns contain nulls."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "dupes_with_nulls.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Alice\n"
            "|Bob\n"
            "1|Alice\n"
            "|Charlie\n",
            encoding="utf-8"
        )

        detector = DuplicateDetector()
        result = detector.detect_duplicates(csv_path, keys=["ID"], delimiter="|")

        # Nulls should be handled appropriately
        assert result.duplicate_count >= 1  # ID=1 duplicated
        assert result.null_key_count >= 2   # Two rows with null ID

    def test_compound_key_hash_generation(self):
        """Test that compound keys are hashed correctly."""
        from api.services.duplicates import DuplicateDetector

        detector = DuplicateDetector()

        # Same values should produce same hash
        hash1 = detector.generate_compound_hash(["1", "Alice", "alice@example.com"])
        hash2 = detector.generate_compound_hash(["1", "Alice", "alice@example.com"])
        assert hash1 == hash2

        # Different values should produce different hash
        hash3 = detector.generate_compound_hash(["2", "Bob", "bob@example.com"])
        assert hash1 != hash3

    def test_compound_key_with_null_handling(self):
        """Test that nulls in compound keys are handled consistently."""
        from api.services.duplicates import DuplicateDetector

        detector = DuplicateDetector()

        # Nulls should be represented consistently in hash
        hash1 = detector.generate_compound_hash(["1", None, "test"])
        hash2 = detector.generate_compound_hash(["1", None, "test"])
        hash3 = detector.generate_compound_hash(["1", "", "test"])

        assert hash1 == hash2
        assert hash1 != hash3  # None and empty string should be different

    def test_duplicate_detection_sqlite_storage(self, temp_dir: Path):
        """Test that SQLite is used for large file duplicate detection."""
        from api.services.duplicates import DuplicateDetector

        # Create large file with duplicates
        large_csv = temp_dir / "large_dupes.csv"
        with large_csv.open("w", encoding="utf-8") as f:
            f.write("ID|Name\n")
            for i in range(10000):
                f.write(f"{i % 1000}|Name{i % 1000}\n")

        detector = DuplicateDetector(use_sqlite=True)
        result = detector.detect_duplicates(large_csv, keys=["ID"], delimiter="|")

        assert result.storage_method == "sqlite"
        assert result.duplicate_count > 0
        assert result.spill_file_path.exists()

    def test_duplicate_detection_performance_large_file(self, temp_dir: Path):
        """Test that duplicate detection completes in reasonable time."""
        import time
        from api.services.duplicates import DuplicateDetector

        large_csv = temp_dir / "perf_test.csv"
        with large_csv.open("w", encoding="utf-8") as f:
            f.write("ID|Name|Email\n")
            for i in range(50000):
                f.write(f"{i}|Name{i}|email{i}@example.com\n")

        detector = DuplicateDetector(use_sqlite=True)

        start_time = time.time()
        result = detector.detect_duplicates(
            large_csv,
            keys=["ID", "Email"],
            delimiter="|"
        )
        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (< 10 seconds for 50k rows)
        assert elapsed_time < 10.0
        assert result.duplicate_count == 0

    def test_duplicate_groups_sorted_by_frequency(self, temp_dir: Path):
        """Test that duplicate groups are sorted by frequency."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "freq_sort.csv"
        lines = ["ID|Name\n"]
        lines.extend(["1|Alice\n"] * 5)  # 5 occurrences
        lines.extend(["2|Bob\n"] * 3)    # 3 occurrences
        lines.extend(["3|Charlie\n"] * 4) # 4 occurrences
        csv_path.write_text("".join(lines), encoding="utf-8")

        detector = DuplicateDetector()
        result = detector.detect_duplicates(csv_path, keys=["ID"], delimiter="|")

        # Groups should be sorted by count (descending)
        assert result.duplicate_groups[0].count == 5
        assert result.duplicate_groups[1].count == 4
        assert result.duplicate_groups[2].count == 3

    def test_duplicate_detection_sample_rows(self, temp_dir: Path):
        """Test that duplicate groups include sample row values."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "sample_rows.csv"
        csv_path.write_text(
            "ID|Name|Email\n"
            "1|Alice|alice@example.com\n"
            "2|Bob|bob@example.com\n"
            "1|Alice|alice@example.com\n",
            encoding="utf-8"
        )

        detector = DuplicateDetector()
        result = detector.detect_duplicates(csv_path, keys=["ID"], delimiter="|")

        # Duplicate group should include sample values
        group = result.duplicate_groups[0]
        assert "Alice" in str(group.sample_row)

    def test_duplicate_detection_cleanup(self, temp_dir: Path):
        """Test that temporary files are cleaned up after detection."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "cleanup.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Alice\n"
            "1|Alice\n",
            encoding="utf-8"
        )

        detector = DuplicateDetector(use_sqlite=True, cleanup=True)
        result = detector.detect_duplicates(csv_path, keys=["ID"], delimiter="|")
        spill_file = result.spill_file_path

        detector.cleanup()
        assert not spill_file.exists() if spill_file else True

    def test_duplicate_detection_with_quoted_fields(self, temp_dir: Path):
        """Test duplicate detection with quoted fields containing delimiters."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "quoted_dupes.csv"
        csv_path.write_text(
            'ID|Description\n'
            '1|"Smith, John"\n'
            '2|"Doe, Jane"\n'
            '1|"Smith, John"\n',
            encoding="utf-8"
        )

        detector = DuplicateDetector()
        result = detector.detect_duplicates(csv_path, keys=["ID", "Description"], delimiter="|")

        assert result.duplicate_count == 1
        assert len(result.duplicate_groups) == 1

    def test_duplicate_detection_case_sensitivity(self, temp_dir: Path):
        """Test that duplicate detection is case-sensitive by default."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "case_dupes.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Alice\n"
            "1|alice\n"
            "1|ALICE\n",
            encoding="utf-8"
        )

        detector = DuplicateDetector(case_sensitive=True)
        result = detector.detect_duplicates(csv_path, keys=["ID", "Name"], delimiter="|")

        # All three should be considered different (case-sensitive)
        assert result.duplicate_count == 0

    def test_duplicate_detection_case_insensitive_option(self, temp_dir: Path):
        """Test case-insensitive duplicate detection option."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "case_insensitive_dupes.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Alice\n"
            "1|alice\n"
            "1|ALICE\n",
            encoding="utf-8"
        )

        detector = DuplicateDetector(case_sensitive=False)
        result = detector.detect_duplicates(csv_path, keys=["ID", "Name"], delimiter="|")

        # All three should be considered duplicates (case-insensitive)
        assert result.duplicate_count == 2
        assert len(result.duplicate_groups) == 1
        assert result.duplicate_groups[0].count == 3

    def test_duplicate_percentage_calculation(self, temp_dir: Path):
        """Test that duplicate percentage is calculated correctly."""
        from api.services.duplicates import DuplicateDetector

        csv_path = temp_dir / "dup_pct.csv"
        lines = ["ID|Name\n"]
        lines.extend(["1|Alice\n"] * 3)  # 3 rows
        lines.extend([f"{i}|Name{i}\n" for i in range(2, 10)])  # 8 unique rows
        csv_path.write_text("".join(lines), encoding="utf-8")

        detector = DuplicateDetector()
        result = detector.detect_duplicates(csv_path, keys=["ID"], delimiter="|")

        # 11 total rows: 1 original + 2 duplicates + 8 unique = 11
        # Duplicate percentage: 2/11 ≈ 18.2%
        assert abs(result.duplicate_percentage - 18.2) < 1.0
