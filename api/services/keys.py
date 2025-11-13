"""
Candidate key suggestion and duplicate detection for data profiling.

This module provides algorithms to:
- Auto-suggest single and compound candidate keys based on cardinality and null ratios
- Detect exact duplicates using hash-based approaches
- Score candidates using: distinct_ratio * (1 - null_ratio_sum)
"""

import hashlib
import os
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DuplicateDetectionResult:
    """
    Result of duplicate detection operation.

    Attributes:
        has_duplicates: Whether duplicates were found
        duplicate_count: Number of distinct duplicate key values
        duplicate_rows: Total number of rows with duplicate keys
        null_key_count: Number of rows with null keys
        duplicate_examples: List of example duplicates
        hash_method: Hash method used ("concatenated" for compound keys)
    """

    has_duplicates: bool
    duplicate_count: int = 0
    duplicate_rows: int = 0
    null_key_count: int = 0
    duplicate_examples: List[Dict[str, Any]] = field(default_factory=list)
    hash_method: str = "concatenated"


class CandidateKeyAnalyzer:
    """
    Analyzes column statistics to suggest candidate keys.

    Uses scoring formula: distinct_ratio * (1 - null_ratio_sum)
    Suggests top K single-column and compound keys (2-3 columns).
    """

    def __init__(
        self,
        max_suggestions: int = 5,
        min_score: float = 0.5,
        min_distinct_ratio: float = 0.5
    ):
        """
        Initialize candidate key analyzer.

        Args:
            max_suggestions: Maximum number of suggestions to return
            min_score: Minimum score threshold for suggestions
            min_distinct_ratio: Minimum distinct ratio to consider
        """
        self.max_suggestions = max_suggestions
        self.min_score = min_score
        self.min_distinct_ratio = min_distinct_ratio

    def calculate_score(
        self,
        distinct_count: int,
        total_count: int,
        null_count: int
    ) -> float:
        """
        Calculate candidate key score.

        Formula: distinct_ratio * (1 - null_ratio)
        where:
        - distinct_ratio = distinct_count / total_count
        - null_ratio = null_count / total_count

        Args:
            distinct_count: Number of distinct values
            total_count: Total number of values
            null_count: Number of null values

        Returns:
            Score between 0.0 and 1.0
        """
        if total_count == 0:
            return 0.0

        distinct_ratio = distinct_count / total_count
        null_ratio = null_count / total_count
        score = distinct_ratio * (1 - null_ratio)

        return score

    def suggest_candidates(
        self,
        column_stats: Dict[str, Dict[str, int]],
        pair_stats: Optional[Dict[Tuple[str, ...], Dict[str, int]]] = None,
        triple_stats: Optional[Dict[Tuple[str, ...], Dict[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest candidate keys from column statistics.

        Args:
            column_stats: Dictionary mapping column name to stats
                         (must include: distinct_count, total_count, null_count)
            pair_stats: Optional dictionary of 2-column combination stats
            triple_stats: Optional dictionary of 3-column combination stats

        Returns:
            List of candidate suggestions sorted by score (descending)
            Each candidate has: columns (list), score (float), distinct_ratio, null_ratio_sum
        """
        candidates = []

        # Single column candidates
        for col_name, stats in column_stats.items():
            distinct_count = stats["distinct_count"]
            total_count = stats["total_count"]
            null_count = stats["null_count"]

            # Calculate ratios
            if total_count == 0:
                continue

            distinct_ratio = distinct_count / total_count

            # Skip low cardinality columns
            if distinct_ratio < self.min_distinct_ratio:
                continue

            score = self.calculate_score(distinct_count, total_count, null_count)

            # Skip if below minimum threshold
            if score < self.min_score:
                continue

            candidates.append({
                "columns": [col_name],
                "score": score,
                "distinct_ratio": distinct_ratio,
                "null_ratio_sum": null_count / total_count,
                "invalid_count": stats.get("invalid_count", 0)
            })

        # Two-column compound candidates
        if pair_stats:
            for cols, stats in pair_stats.items():
                distinct_count = stats["distinct_count"]
                total_count = stats["total_count"]
                null_count = stats["null_count"]

                if total_count == 0:
                    continue

                distinct_ratio = distinct_count / total_count

                # For compound keys, use sum of individual null ratios
                null_ratio_sum = 0.0
                for col in cols:
                    if col in column_stats:
                        col_null_ratio = column_stats[col]["null_count"] / column_stats[col]["total_count"]
                        null_ratio_sum += col_null_ratio

                score = distinct_ratio * (1 - null_ratio_sum)

                if score >= self.min_score:
                    candidates.append({
                        "columns": list(cols),
                        "score": score,
                        "distinct_ratio": distinct_ratio,
                        "null_ratio_sum": null_ratio_sum,
                        "invalid_count": sum(column_stats.get(c, {}).get("invalid_count", 0) for c in cols)
                    })

        # Three-column compound candidates
        if triple_stats:
            for cols, stats in triple_stats.items():
                distinct_count = stats["distinct_count"]
                total_count = stats["total_count"]
                null_count = stats["null_count"]

                if total_count == 0:
                    continue

                distinct_ratio = distinct_count / total_count

                # For compound keys, use sum of individual null ratios
                null_ratio_sum = 0.0
                for col in cols:
                    if col in column_stats:
                        col_null_ratio = column_stats[col]["null_count"] / column_stats[col]["total_count"]
                        null_ratio_sum += col_null_ratio

                score = distinct_ratio * (1 - null_ratio_sum)

                if score >= self.min_score:
                    candidates.append({
                        "columns": list(cols),
                        "score": score,
                        "distinct_ratio": distinct_ratio,
                        "null_ratio_sum": null_ratio_sum,
                        "invalid_count": sum(column_stats.get(c, {}).get("invalid_count", 0) for c in cols)
                    })

        # Sort by score (descending), then by invalid_count (ascending) as tie-breaker
        candidates.sort(
            key=lambda x: (-x["score"], x["invalid_count"])
        )

        # Remove invalid_count from final output (internal only)
        for candidate in candidates:
            candidate.pop("invalid_count", None)

        # Return top K suggestions
        return candidates[:self.max_suggestions]


class DuplicateDetector:
    """
    Detects exact duplicates using hash-based approach.

    Supports single and compound key columns.
    Uses SQLite for efficient duplicate detection on large datasets.
    """

    def __init__(
        self,
        use_sqlite: bool = False,
        cleanup: bool = True,
        max_examples: int = 10,
        commit_batch_size: int = 1000
    ):
        """
        Initialize duplicate detector.

        Args:
            use_sqlite: Use SQLite for storage (efficient for large datasets)
            cleanup: Automatically clean up temporary SQLite files
            max_examples: Maximum number of duplicate examples to return
            commit_batch_size: Number of rows between SQLite commits (default 1000)
        """
        self.use_sqlite = use_sqlite
        self.cleanup_on_exit = cleanup
        self.max_examples = max_examples
        self.commit_batch_size = commit_batch_size
        self._insert_count = 0
        self._temp_db_path: Optional[Path] = None
        self._connection: Optional[sqlite3.Connection] = None

    def find_duplicates(
        self,
        data: List[Dict[str, Any]],
        key_columns: List[str]
    ) -> DuplicateDetectionResult:
        """
        Find exact duplicates in data based on key columns.

        Args:
            data: List of dictionaries representing rows
            key_columns: List of column names to use as key

        Returns:
            DuplicateDetectionResult with duplicate statistics
        """
        if not data or not key_columns:
            return DuplicateDetectionResult(has_duplicates=False)

        # Initialize storage if needed
        if self.use_sqlite:
            self._init_sqlite_storage()

        # Track key occurrences
        key_counts: Dict[str, int] = {}
        null_key_count = 0
        duplicate_examples: List[Dict[str, Any]] = []

        for row in data:
            # Extract key values
            key_values = []
            has_null = False

            for col in key_columns:
                value = row.get(col)
                if value is None or value == "":
                    has_null = True
                    break
                key_values.append(str(value))

            # Skip rows with null keys
            if has_null:
                null_key_count += 1
                continue

            # Create hash/key
            if len(key_columns) == 1:
                key_hash = key_values[0]
            else:
                # Compound key: concatenate with separator
                key_hash = self._create_compound_hash(key_values)

            # Count occurrences
            if self.use_sqlite:
                self._insert_or_increment_sqlite(key_hash, row)
            else:
                if key_hash not in key_counts:
                    key_counts[key_hash] = 0
                key_counts[key_hash] += 1

        # Get results
        if self.use_sqlite:
            # Commit any remaining batched inserts before reading results
            self._connection.commit()
            key_counts = self._get_duplicate_counts_sqlite()
            duplicate_examples = self._get_duplicate_examples_sqlite()

        # Calculate statistics
        duplicate_count = sum(1 for count in key_counts.values() if count > 1)
        # duplicate_rows is the total count of rows involved in duplicates
        duplicate_rows = sum(count for count in key_counts.values() if count > 1)
        has_duplicates = duplicate_count > 0

        # Get examples (if not using SQLite)
        if not self.use_sqlite and has_duplicates:
            duplicate_keys = [k for k, v in key_counts.items() if v > 1]
            duplicate_examples = [
                {
                    "key_value": key,
                    "count": key_counts[key]
                }
                for key in duplicate_keys[:self.max_examples]
            ]

        # Cleanup if needed
        if self.cleanup_on_exit:
            self.cleanup()

        return DuplicateDetectionResult(
            has_duplicates=has_duplicates,
            duplicate_count=duplicate_count,
            duplicate_rows=duplicate_rows,
            null_key_count=null_key_count,
            duplicate_examples=duplicate_examples,
            hash_method="concatenated" if len(key_columns) > 1 else "single"
        )

    def _create_compound_hash(self, values: List[str]) -> str:
        """
        Create hash for compound key.

        Uses concatenation with null-safe separator.

        Args:
            values: List of string values

        Returns:
            Hash string
        """
        # Use null-safe separator (unlikely to appear in data)
        separator = "\x00"
        return separator.join(values)

    def _init_sqlite_storage(self) -> None:
        """Initialize SQLite database for duplicate detection."""
        if self._connection is not None:
            return

        # Create temporary database file
        fd, temp_path = tempfile.mkstemp(suffix='.db', prefix='duplicates_')
        os.close(fd)  # Close file descriptor to prevent resource leak
        self._temp_db_path = Path(temp_path)

        # Connect to database
        self._connection = sqlite3.connect(str(self._temp_db_path))
        cursor = self._connection.cursor()

        # Create table for key hashes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS key_hashes (
                hash TEXT PRIMARY KEY,
                cnt INTEGER NOT NULL DEFAULT 1,
                example_row TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cnt
            ON key_hashes(cnt DESC)
        """)

        self._connection.commit()

    def _insert_or_increment_sqlite(self, key_hash: str, row: Dict[str, Any]) -> None:
        """
        Insert key hash or increment count in SQLite.

        Args:
            key_hash: Hash of key columns
            row: Example row for this key
        """
        if self._connection is None:
            raise RuntimeError("SQLite storage not initialized")

        cursor = self._connection.cursor()

        # Store first occurrence as example
        import json
        example_row = json.dumps(row, default=str)

        cursor.execute("""
            INSERT INTO key_hashes (hash, cnt, example_row)
            VALUES (?, 1, ?)
            ON CONFLICT(hash)
            DO UPDATE SET cnt = cnt + 1
        """, (key_hash, example_row))

        # Batched commits for performance
        self._insert_count += 1
        if self._insert_count % self.commit_batch_size == 0:
            self._connection.commit()

    def _get_duplicate_counts_sqlite(self) -> Dict[str, int]:
        """
        Get key counts from SQLite.

        Returns:
            Dictionary mapping hash to count
        """
        if self._connection is None:
            raise RuntimeError("SQLite storage not initialized")

        cursor = self._connection.cursor()
        cursor.execute("SELECT hash, cnt FROM key_hashes")

        counts = {}
        for hash_val, cnt in cursor.fetchall():
            counts[hash_val] = cnt

        return counts

    def _get_duplicate_examples_sqlite(self) -> List[Dict[str, Any]]:
        """
        Get example duplicate rows from SQLite.

        Returns:
            List of duplicate examples
        """
        if self._connection is None:
            raise RuntimeError("SQLite storage not initialized")

        cursor = self._connection.cursor()
        cursor.execute("""
            SELECT hash, cnt, example_row
            FROM key_hashes
            WHERE cnt > 1
            ORDER BY cnt DESC
            LIMIT ?
        """, (self.max_examples,))

        examples = []
        for hash_val, cnt, _ in cursor.fetchall():
            examples.append({
                "key_value": hash_val,
                "count": cnt
            })

        return examples

    def cleanup(self) -> None:
        """Clean up temporary SQLite files."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

        if self._temp_db_path is not None and self._temp_db_path.exists():
            try:
                self._temp_db_path.unlink()
            except Exception:
                # Ignore errors if temp file already deleted
                pass
            finally:
                self._temp_db_path = None

    def __del__(self):
        """Clean up on deletion if cleanup is enabled."""
        if self.cleanup_on_exit:
            self.cleanup()
