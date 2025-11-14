"""
Tests for services/distincts.py - distinct counting functionality.

Focuses on covering uncovered lines to push past 85% coverage threshold.
"""

import csv
import sqlite3
import tempfile
from pathlib import Path
import pytest

from services.distincts import (
    DistinctCounter,
    DistinctCountResult,
    create_column_table,
    insert_or_increment,
    get_distinct_count,
    get_top_values,
)


class TestDistinctCounterWithSQLite:
    """Test DistinctCounter with SQLite backend."""

    def test_count_distincts_with_sqlite(self, tmp_path):
        """Should count distincts using SQLite storage."""
        # Create test CSV
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(['id', 'category', 'value'])
            writer.writerow(['1', 'A', '100'])
            writer.writerow(['2', 'A', '200'])
            writer.writerow(['3', 'B', '100'])
            writer.writerow(['4', 'B', '300'])

        counter = DistinctCounter(use_sqlite=True, cleanup=True)
        result = counter.count_distincts(csv_file, 'category', delimiter='|')

        assert result.distinct_count == 2  # A, B
        assert result.total_count == 4
        assert result.storage_method == "sqlite"
        assert result.spill_file_path is not None
        assert result.is_exact is True

        # Cleanup should happen
        counter.cleanup()

    def test_sqlite_with_case_insensitive(self, tmp_path):
        """Should handle case-insensitive matching."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(['id', 'code'])
            writer.writerow(['1', 'ABC'])
            writer.writerow(['2', 'abc'])
            writer.writerow(['3', 'Abc'])

        counter = DistinctCounter(use_sqlite=True, case_sensitive=False, cleanup=True)
        result = counter.count_distincts(csv_file, 'code', delimiter='|')

        assert result.distinct_count == 1  # All normalized to same value
        counter.cleanup()

    def test_sqlite_with_whitespace_handling(self, tmp_path):
        """Should handle whitespace trimming."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(['id', 'code'])
            writer.writerow(['1', ' ABC '])
            writer.writerow(['2', 'ABC'])
            writer.writerow(['3', '  ABC  '])

        counter = DistinctCounter(use_sqlite=True, trim_whitespace=True, cleanup=True)
        result = counter.count_distincts(csv_file, 'code', delimiter='|')

        assert result.distinct_count == 1  # All trimmed to ABC
        counter.cleanup()

    def test_sqlite_with_empty_values(self, tmp_path):
        """Should handle null and empty values correctly."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(['id', 'value'])
            writer.writerow(['1', 'A'])
            writer.writerow(['2', ''])
            writer.writerow(['3', '""'])
            writer.writerow(['4', 'B'])

        counter = DistinctCounter(use_sqlite=True, cleanup=True)
        result = counter.count_distincts(csv_file, 'value', delimiter='|')

        assert result.distinct_count == 2  # A, B
        assert result.null_count == 1  # Empty string
        assert result.empty_count == 1  # Quoted empty string
        counter.cleanup()

    def test_invalid_column_name(self, tmp_path):
        """Should raise error for invalid column name."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(['id', 'name'])
            writer.writerow(['1', 'Alice'])

        counter = DistinctCounter(use_sqlite=True, cleanup=True)

        with pytest.raises(ValueError, match="Column 'invalid' not found"):
            counter.count_distincts(csv_file, 'invalid', delimiter='|')

        counter.cleanup()


class TestUtilityFunctions:
    """Test module-level utility functions."""

    def test_create_column_table(self, tmp_path):
        """Should create per-column table in SQLite."""
        db_file = tmp_path / "test.db"

        create_column_table(db_file, 0)

        # Verify table was created
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='col_0_values'")
        result = cursor.fetchone()
        assert result is not None
        conn.close()

    def test_insert_or_increment(self, tmp_path):
        """Should insert or increment values."""
        db_file = tmp_path / "test.db"

        # Create table first
        create_column_table(db_file, 0)

        # Insert new value
        insert_or_increment(db_file, 0, 'test_value')

        # Verify it was inserted
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT value, cnt FROM col_0_values WHERE value='test_value'")
        result = cursor.fetchone()
        assert result == ('test_value', 1)
        conn.close()

        # Increment existing value
        insert_or_increment(db_file, 0, 'test_value')

        # Verify it was incremented
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT value, cnt FROM col_0_values WHERE value='test_value'")
        result = cursor.fetchone()
        assert result == ('test_value', 2)
        conn.close()

    def test_get_distinct_count(self, tmp_path):
        """Should get exact distinct count."""
        db_file = tmp_path / "test.db"

        # Create table and insert values
        create_column_table(db_file, 0)
        insert_or_increment(db_file, 0, 'A')
        insert_or_increment(db_file, 0, 'B')
        insert_or_increment(db_file, 0, 'A')  # Duplicate

        count = get_distinct_count(db_file, 0)
        assert count == 2  # A and B

    def test_get_top_values(self, tmp_path):
        """Should get top N values."""
        db_file = tmp_path / "test.db"

        # Create table and insert values with different frequencies
        create_column_table(db_file, 0)
        for _ in range(5):
            insert_or_increment(db_file, 0, 'A')
        for _ in range(3):
            insert_or_increment(db_file, 0, 'B')
        insert_or_increment(db_file, 0, 'C')

        top_values = get_top_values(db_file, 0, limit=2)

        assert len(top_values) == 2
        assert top_values[0] == ('A', 5)  # Most frequent
        assert top_values[1] == ('B', 3)  # Second most


class TestDistinctCountResult:
    """Test DistinctCountResult methods."""

    def test_get_top_n(self):
        """Should return top N values."""
        result = DistinctCountResult(
            distinct_count=3,
            total_count=10,
            frequencies={'A': 5, 'B': 3, 'C': 2}
        )

        top_2 = result.get_top_n(2)

        assert len(top_2) == 2
        assert top_2[0] == {'value': 'A', 'count': 5}
        assert top_2[1] == {'value': 'B', 'count': 3}

    def test_get_top_n_more_than_available(self):
        """Should return all values if N > distinct count."""
        result = DistinctCountResult(
            distinct_count=2,
            total_count=5,
            frequencies={'A': 3, 'B': 2}
        )

        top_10 = result.get_top_n(10)

        assert len(top_10) == 2  # Only 2 available
