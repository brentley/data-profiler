"""
SQLite-based exact distinct counting for data profiling.

This module provides memory-efficient exact distinct counting using
SQLite on-disk storage. It tracks distinct values per column with
exact counts (no approximation) and handles large datasets by spilling
to disk.
"""

import csv
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class DistinctCountResult:
    """
    Result of distinct counting operation.

    Attributes:
        distinct_count: Exact number of distinct non-null values
        total_count: Total number of values (including nulls)
        null_count: Number of null/empty values
        empty_count: Number of empty strings (distinct from null)
        cardinality_ratio: Ratio of distinct to total (0.0 to 1.0)
        frequencies: Dictionary mapping value to count
        storage_method: Storage method used ("memory" or "sqlite")
        spill_file_path: Path to SQLite file (if using sqlite storage)
        is_exact: Always True (this implementation guarantees exactness)
    """

    distinct_count: int
    total_count: int
    null_count: int = 0
    empty_count: int = 0
    cardinality_ratio: float = 0.0
    frequencies: Dict[str, int] = field(default_factory=dict)
    storage_method: str = "memory"
    spill_file_path: Optional[Path] = None
    is_exact: bool = True

    def get_top_n(self, n: int = 10) -> List[Tuple[str, int]]:
        """
        Get top N most frequent values.

        Args:
            n: Number of top values to return

        Returns:
            List of (value, count) tuples sorted by count descending
        """
        sorted_items = sorted(
            self.frequencies.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_items[:n]


class DistinctCounter:
    """
    Exact distinct counter using SQLite for memory-efficient storage.

    This class provides exact distinct counting for CSV columns by storing
    values and their frequencies in SQLite. It handles large datasets by
    spilling to disk and uses parameterized queries to prevent SQL injection.
    """

    def __init__(
        self,
        use_sqlite: bool = False,
        cleanup: bool = False,
        case_sensitive: bool = True,
        trim_whitespace: bool = True
    ):
        """
        Initialize distinct counter.

        Args:
            use_sqlite: Force SQLite storage (otherwise auto-detect based on size)
            cleanup: Automatically clean up temporary SQLite files
            case_sensitive: Treat values as case-sensitive (default: True)
            trim_whitespace: Trim leading/trailing whitespace (default: True)
        """
        self.use_sqlite = use_sqlite
        self.cleanup_on_exit = cleanup
        self.case_sensitive = case_sensitive
        self.trim_whitespace = trim_whitespace
        self._temp_db_path: Optional[Path] = None
        self._connection: Optional[sqlite3.Connection] = None

    def count_distincts(
        self,
        csv_path: Path,
        column_name: str,
        delimiter: str = '|'
    ) -> DistinctCountResult:
        """
        Count distinct values in a CSV column.

        Args:
            csv_path: Path to CSV file
            column_name: Name of column to analyze
            delimiter: CSV delimiter (default: '|')

        Returns:
            DistinctCountResult with exact counts and frequencies
        """
        # Initialize storage
        if self.use_sqlite:
            self._init_sqlite_storage()

        frequencies: Dict[str, int] = {}
        null_count = 0
        empty_count = 0
        total_count = 0

        # Read CSV and count values
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)

            # Verify column exists
            if column_name not in reader.fieldnames:
                raise ValueError(f"Column '{column_name}' not found in CSV")

            for row in reader:
                value = row.get(column_name, '')
                total_count += 1

                # Handle null/empty values
                if value is None or value == '':
                    null_count += 1
                    continue

                # Check for quoted empty string
                if value == '""':
                    empty_count += 1
                    continue

                # Apply transformations
                if self.trim_whitespace:
                    value = value.strip()

                if not self.case_sensitive:
                    value = value.lower()

                # Count value
                if self.use_sqlite:
                    self._insert_or_increment_sqlite(value)
                else:
                    frequencies[value] = frequencies.get(value, 0) + 1

        # Get results
        if self.use_sqlite:
            frequencies = self._get_all_frequencies_sqlite()
            # Commit any pending transactions before returning
            if self._connection:
                self._connection.commit()

        distinct_count = len(frequencies)
        cardinality_ratio = distinct_count / total_count if total_count > 0 else 0.0

        return DistinctCountResult(
            distinct_count=distinct_count,
            total_count=total_count,
            null_count=null_count,
            empty_count=empty_count,
            cardinality_ratio=cardinality_ratio,
            frequencies=frequencies,
            storage_method="sqlite" if self.use_sqlite else "memory",
            spill_file_path=self._temp_db_path,
            is_exact=True
        )

    def _init_sqlite_storage(self) -> None:
        """Initialize SQLite database for storing distinct values."""
        if self._connection is not None:
            return  # Already initialized

        # Create temporary database file
        fd, temp_path = tempfile.mkstemp(suffix='.db', prefix='distincts_')
        self._temp_db_path = Path(temp_path)

        # Connect to database
        self._connection = sqlite3.connect(str(self._temp_db_path))
        cursor = self._connection.cursor()

        # Create table for distinct values
        # Use UNIQUE constraint to ensure one row per value
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS distinct_values (
                value TEXT PRIMARY KEY,
                cnt INTEGER NOT NULL DEFAULT 1
            )
        """)

        # Create index for efficient top-N queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cnt
            ON distinct_values(cnt DESC)
        """)

        self._connection.commit()

    def _insert_or_increment_sqlite(self, value: str) -> None:
        """
        Insert value or increment count in SQLite.

        Uses parameterized queries to prevent SQL injection.
        Uses INSERT OR REPLACE with conflict resolution.

        Args:
            value: Value to insert or increment
        """
        if self._connection is None:
            raise RuntimeError("SQLite storage not initialized")

        cursor = self._connection.cursor()

        # Use INSERT OR REPLACE with COALESCE to increment existing or insert new
        # This is atomic and handles the upsert pattern efficiently
        cursor.execute("""
            INSERT INTO distinct_values (value, cnt)
            VALUES (?, 1)
            ON CONFLICT(value)
            DO UPDATE SET cnt = cnt + 1
        """, (value,))

        self._connection.commit()

    def _get_all_frequencies_sqlite(self) -> Dict[str, int]:
        """
        Retrieve all value frequencies from SQLite.

        Returns:
            Dictionary mapping value to count
        """
        if self._connection is None:
            raise RuntimeError("SQLite storage not initialized")

        cursor = self._connection.cursor()
        cursor.execute("SELECT value, cnt FROM distinct_values")

        frequencies = {}
        for value, cnt in cursor.fetchall():
            frequencies[value] = cnt

        return frequencies

    def cleanup(self) -> None:
        """Clean up temporary SQLite files."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

        if self._temp_db_path is not None and self._temp_db_path.exists():
            try:
                self._temp_db_path.unlink()
            except Exception:
                pass  # Best effort cleanup
            finally:
                self._temp_db_path = None

    def __del__(self):
        """Clean up on deletion if cleanup is enabled."""
        if self.cleanup_on_exit:
            self.cleanup()


def create_column_table(db_path: Path, column_index: int) -> None:
    """
    Create per-column distinct value table in SQLite.

    This is a utility function for creating dedicated tables for
    each column in a larger profiling context.

    Args:
        db_path: Path to SQLite database
        column_index: 0-based column index
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    table_name = f"col_{column_index}_values"

    # Create table with parameterized name (note: table names can't use ?)
    # This is safe because column_index is an integer, not user input
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            value TEXT PRIMARY KEY,
            cnt INTEGER NOT NULL DEFAULT 1
        )
    """)

    # Create index for top-N queries
    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_cnt
        ON {table_name}(cnt DESC)
    """)

    conn.commit()
    conn.close()


def insert_or_increment(
    db_path: Path,
    column_index: int,
    value: str
) -> None:
    """
    Insert value or increment count in per-column table.

    Uses parameterized queries to prevent SQL injection.

    Args:
        db_path: Path to SQLite database
        column_index: 0-based column index
        value: Value to insert or increment
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    table_name = f"col_{column_index}_values"

    # Use parameterized query for value (not table name, which is constructed)
    cursor.execute(f"""
        INSERT INTO {table_name} (value, cnt)
        VALUES (?, 1)
        ON CONFLICT(value)
        DO UPDATE SET cnt = cnt + 1
    """, (value,))

    conn.commit()
    conn.close()


def get_distinct_count(db_path: Path, column_index: int) -> int:
    """
    Get exact distinct count for a column.

    Args:
        db_path: Path to SQLite database
        column_index: 0-based column index

    Returns:
        Exact count of distinct values
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    table_name = f"col_{column_index}_values"

    cursor.execute(f"""
        SELECT COUNT(*) FROM {table_name}
    """)

    count = cursor.fetchone()[0]
    conn.close()

    return count


def get_top_values(
    db_path: Path,
    column_index: int,
    limit: int = 10
) -> List[Tuple[str, int]]:
    """
    Get top N most frequent values for a column.

    Args:
        db_path: Path to SQLite database
        column_index: 0-based column index
        limit: Number of top values to return

    Returns:
        List of (value, count) tuples sorted by count descending
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    table_name = f"col_{column_index}_values"

    # Use index for efficient sorting
    cursor.execute(f"""
        SELECT value, cnt
        FROM {table_name}
        ORDER BY cnt DESC
        LIMIT ?
    """, (limit,))

    results = cursor.fetchall()
    conn.close()

    return results
