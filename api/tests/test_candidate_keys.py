"""
Candidate key suggestion and duplicate detection tests.

Tests the candidate key system:
- Auto-suggest single column keys (high cardinality, low nulls)
- Auto-suggest compound keys (2-3 columns)
- Scoring: distinct_ratio * (1 - null_ratio_sum)
- User confirmation workflow
- Exact duplicate detection with hash-based approach
"""

import pytest
from services.keys import CandidateKeyAnalyzer, DuplicateDetector


class TestSingleColumnCandidates:
    """Test single column candidate key suggestions."""

    def test_perfect_unique_column(self):
        """Column with all unique values should score highest."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "col1": {
                "distinct_count": 1000,
                "total_count": 1000,
                "null_count": 0
            }
        }

        candidates = analyzer.suggest_candidates(column_stats)

        # Should suggest col1 with score 1.0
        assert len(candidates) > 0
        assert candidates[0]["columns"] == ["col1"]
        assert candidates[0]["score"] == 1.0

    def test_high_cardinality_no_nulls(self):
        """High cardinality with no nulls should score well."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "id_col": {
                "distinct_count": 950,
                "total_count": 1000,
                "null_count": 0
            }
        }

        candidates = analyzer.suggest_candidates(column_stats)

        # Should have high score: 0.95 * 1.0 = 0.95
        assert len(candidates) > 0
        top = candidates[0]
        assert top["columns"] == ["id_col"]
        assert top["score"] == pytest.approx(0.95, rel=0.01)

    def test_low_cardinality_excluded(self):
        """Low cardinality columns should not be suggested."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "status": {
                "distinct_count": 3,
                "total_count": 1000,
                "null_count": 0
            }
        }

        candidates = analyzer.suggest_candidates(column_stats)

        # Should not suggest status (distinct_ratio too low)
        assert not any(c["columns"] == ["status"] for c in candidates)

    def test_with_nulls_penalty(self):
        """Nulls should reduce score."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "col1": {
                "distinct_count": 1000,
                "total_count": 1000,
                "null_count": 100
            }
        }

        candidates = analyzer.suggest_candidates(column_stats)

        # Score should be penalized: 1.0 * (1 - 0.1) = 0.9
        assert len(candidates) > 0
        top = candidates[0]
        assert top["score"] == pytest.approx(0.9, rel=0.01)

    def test_multiple_candidate_ranking(self):
        """Should rank multiple candidates by score."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "id": {
                "distinct_count": 1000,
                "total_count": 1000,
                "null_count": 0
            },
            "email": {
                "distinct_count": 950,
                "total_count": 1000,
                "null_count": 50
            },
            "name": {
                "distinct_count": 800,
                "total_count": 1000,
                "null_count": 10
            }
        }

        candidates = analyzer.suggest_candidates(column_stats)

        # Should be ordered: id (1.0), name (0.8 * 0.99), email (0.95 * 0.95)
        assert candidates[0]["columns"] == ["id"]
        assert candidates[0]["score"] > candidates[1]["score"]


class TestCompoundKeyCandidates:
    """Test compound key candidate suggestions."""

    def test_two_column_compound(self):
        """Should suggest 2-column compound keys."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "first_name": {
                "distinct_count": 50,
                "total_count": 1000,
                "null_count": 0
            },
            "last_name": {
                "distinct_count": 100,
                "total_count": 1000,
                "null_count": 0
            }
        }

        # Provide pair statistics
        pair_stats = {
            ("first_name", "last_name"): {
                "distinct_count": 980,
                "total_count": 1000,
                "null_count": 0
            }
        }

        candidates = analyzer.suggest_candidates(column_stats, pair_stats)

        # Should suggest compound key
        compound = [c for c in candidates if len(c["columns"]) == 2]
        assert len(compound) > 0
        assert set(compound[0]["columns"]) == {"first_name", "last_name"}

    def test_three_column_compound(self):
        """Should suggest 3-column compound keys if needed."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "year": {"distinct_count": 10, "total_count": 1000, "null_count": 0},
            "month": {"distinct_count": 12, "total_count": 1000, "null_count": 0},
            "customer_id": {"distinct_count": 100, "total_count": 1000, "null_count": 0}
        }

        triple_stats = {
            ("year", "month", "customer_id"): {
                "distinct_count": 1000,
                "total_count": 1000,
                "null_count": 0
            }
        }

        candidates = analyzer.suggest_candidates(column_stats, triple_stats=triple_stats)

        # Should suggest 3-column compound
        compound = [c for c in candidates if len(c["columns"]) == 3]
        assert len(compound) > 0
        assert compound[0]["score"] == 1.0

    def test_compound_null_penalty(self):
        """Compound keys with nulls should be penalized."""
        analyzer = CandidateKeyAnalyzer()

        pair_stats = {
            ("col1", "col2"): {
                "distinct_count": 1000,
                "total_count": 1000,
                "null_count": 100  # Nulls in either column
            }
        }

        column_stats = {
            "col1": {"distinct_count": 500, "total_count": 1000, "null_count": 50},
            "col2": {"distinct_count": 500, "total_count": 1000, "null_count": 50}
        }

        candidates = analyzer.suggest_candidates(column_stats, pair_stats)

        # Score should account for nulls: 1.0 * (1 - (0.05 + 0.05))
        compound = [c for c in candidates if len(c["columns"]) == 2]
        if compound:
            assert compound[0]["score"] < 1.0

    def test_prefer_single_over_compound(self):
        """Should prefer single column if it's sufficient."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "id": {
                "distinct_count": 1000,
                "total_count": 1000,
                "null_count": 0
            },
            "name": {
                "distinct_count": 500,
                "total_count": 1000,
                "null_count": 0
            }
        }

        pair_stats = {
            ("id", "name"): {
                "distinct_count": 1000,
                "total_count": 1000,
                "null_count": 0
            }
        }

        candidates = analyzer.suggest_candidates(column_stats, pair_stats)

        # Single column "id" should rank higher than compound
        assert candidates[0]["columns"] == ["id"]

    def test_limit_suggestions(self):
        """Should limit to top K suggestions."""
        analyzer = CandidateKeyAnalyzer(max_suggestions=5)

        # Create many candidate columns
        column_stats = {
            f"col_{i}": {
                "distinct_count": 900 - i * 10,
                "total_count": 1000,
                "null_count": 0
            }
            for i in range(20)
        }

        candidates = analyzer.suggest_candidates(column_stats)

        # Should return only top 5
        assert len(candidates) <= 5


class TestDuplicateDetection:
    """Test exact duplicate detection."""

    def test_detect_duplicates_single_key(self):
        """Should detect duplicates on single key."""
        detector = DuplicateDetector()

        data = [
            {"id": "1", "name": "Alice"},
            {"id": "2", "name": "Bob"},
            {"id": "1", "name": "Alice2"},  # Duplicate id
            {"id": "3", "name": "Carol"}
        ]

        result = detector.find_duplicates(data, key_columns=["id"])

        assert result.has_duplicates is True
        assert result.duplicate_count == 1  # One duplicate value
        assert result.duplicate_rows == 2  # Two rows with id=1

    def test_no_duplicates(self):
        """Should detect when no duplicates exist."""
        detector = DuplicateDetector()

        data = [
            {"id": "1", "name": "Alice"},
            {"id": "2", "name": "Bob"},
            {"id": "3", "name": "Carol"}
        ]

        result = detector.find_duplicates(data, key_columns=["id"])

        assert result.has_duplicates is False
        assert result.duplicate_count == 0

    def test_detect_compound_key_duplicates(self):
        """Should detect duplicates on compound key."""
        detector = DuplicateDetector()

        data = [
            {"first": "John", "last": "Smith", "age": 30},
            {"first": "John", "last": "Smith", "age": 35},  # Duplicate
            {"first": "John", "last": "Doe", "age": 30},
            {"first": "Jane", "last": "Smith", "age": 30}
        ]

        result = detector.find_duplicates(data, key_columns=["first", "last"])

        assert result.has_duplicates is True
        assert result.duplicate_count == 1  # One duplicate key (John Smith)

    def test_hash_based_detection(self):
        """Should use hash-based approach for efficiency."""
        detector = DuplicateDetector(use_sqlite=True)

        # Large dataset
        data = [{"id": str(i % 1000), "value": f"val_{i}"} for i in range(10000)]

        result = detector.find_duplicates(data, key_columns=["id"])

        assert result.has_duplicates is True
        # 1000 unique ids repeated 10 times each
        assert result.duplicate_count == 1000
        assert result.duplicate_rows == 10000  # All 10 rows per key

    def test_null_handling_in_keys(self):
        """Should handle nulls in key columns."""
        detector = DuplicateDetector()

        data = [
            {"id": "1", "name": "Alice"},
            {"id": None, "name": "Bob"},
            {"id": None, "name": "Carol"},
            {"id": "2", "name": "Dave"}
        ]

        result = detector.find_duplicates(data, key_columns=["id"])

        # Nulls might be excluded or counted separately
        assert result.null_key_count == 2

    def test_duplicate_examples(self):
        """Should provide examples of duplicates."""
        detector = DuplicateDetector()

        data = [
            {"id": "1", "name": "Alice", "row": 1},
            {"id": "2", "name": "Bob", "row": 2},
            {"id": "1", "name": "Alice2", "row": 3},
            {"id": "1", "name": "Alice3", "row": 4}
        ]

        result = detector.find_duplicates(data, key_columns=["id"])

        # Should provide examples of duplicate rows
        assert len(result.duplicate_examples) > 0
        assert "1" in [ex["key_value"] for ex in result.duplicate_examples]


class TestCandidateKeyWorkflow:
    """Test the full candidate key workflow."""

    def test_suggest_confirm_detect_workflow(self):
        """Test complete workflow: suggest -> confirm -> detect."""
        # Step 1: Analyze and suggest
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "id": {"distinct_count": 1000, "total_count": 1000, "null_count": 0},
            "email": {"distinct_count": 950, "total_count": 1000, "null_count": 50}
        }

        candidates = analyzer.suggest_candidates(column_stats)
        assert len(candidates) > 0

        # Step 2: User confirms top candidate
        confirmed_key = candidates[0]["columns"]

        # Step 3: Run duplicate detection
        detector = DuplicateDetector()
        data = [{"id": str(i), "email": f"user{i}@example.com"} for i in range(1000)]

        result = detector.find_duplicates(data, key_columns=confirmed_key)
        assert result.has_duplicates is False

    def test_reject_and_try_next(self):
        """Should allow trying next candidate if first is rejected."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "id": {"distinct_count": 990, "total_count": 1000, "null_count": 0},
            "email": {"distinct_count": 995, "total_count": 1000, "null_count": 0}
        }

        candidates = analyzer.suggest_candidates(column_stats)

        # User rejects first, tries second
        first_choice = candidates[0]["columns"]
        second_choice = candidates[1]["columns"]

        assert first_choice != second_choice

    def test_no_suitable_single_suggest_compound(self):
        """If no single column suitable, suggest compound."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "year": {"distinct_count": 5, "total_count": 1000, "null_count": 0},
            "month": {"distinct_count": 12, "total_count": 1000, "null_count": 0},
            "day": {"distinct_count": 31, "total_count": 1000, "null_count": 0}
        }

        pair_stats = {
            ("year", "month", "day"): {
                "distinct_count": 1000,
                "total_count": 1000,
                "null_count": 0
            }
        }

        candidates = analyzer.suggest_candidates(column_stats, triple_stats=pair_stats)

        # Should primarily suggest compound keys
        assert any(len(c["columns"]) > 1 for c in candidates)


class TestDuplicateDetectorPerformance:
    """Test duplicate detection performance and scalability."""

    def test_large_dataset_exact(self):
        """Should handle large datasets with exact detection."""
        detector = DuplicateDetector(use_sqlite=True)

        # 1 million rows
        data = [{"id": str(i % 10000)} for i in range(1000000)]

        result = detector.find_duplicates(data, key_columns=["id"])

        assert result.has_duplicates is True
        assert result.duplicate_count == 10000  # 10k unique values
        assert result.duplicate_rows == 1000000  # All 100 rows per key

    def test_compound_key_hashing(self):
        """Should hash compound keys efficiently."""
        detector = DuplicateDetector()

        data = [
            {"a": str(i % 100), "b": str(i % 50), "c": str(i % 25)}
            for i in range(10000)
        ]

        result = detector.find_duplicates(data, key_columns=["a", "b", "c"])

        # Hash should use all columns with proper separator
        assert result.hash_method == "concatenated"

    def test_unicode_in_keys(self):
        """Should handle Unicode in key columns."""
        detector = DuplicateDetector()

        data = [
            {"name": "世界", "id": "1"},
            {"name": "世界", "id": "2"},
            {"name": "hello", "id": "3"}
        ]

        result = detector.find_duplicates(data, key_columns=["name"])

        assert result.has_duplicates is True


class TestCandidateKeyScoring:
    """Test the scoring algorithm details."""

    def test_score_calculation(self):
        """Test score calculation formula."""
        analyzer = CandidateKeyAnalyzer()

        # distinct_ratio * (1 - null_ratio_sum)
        score = analyzer.calculate_score(
            distinct_count=800,
            total_count=1000,
            null_count=100
        )

        # distinct_ratio = 800/1000 = 0.8
        # null_ratio = 100/1000 = 0.1
        # score = 0.8 * (1 - 0.1) = 0.72
        assert score == pytest.approx(0.72, rel=0.01)

    def test_tie_breaker_lower_invalid(self):
        """Should use invalid count as tie breaker."""
        analyzer = CandidateKeyAnalyzer()

        column_stats = {
            "col1": {
                "distinct_count": 900,
                "total_count": 1000,
                "null_count": 0,
                "invalid_count": 10
            },
            "col2": {
                "distinct_count": 900,
                "total_count": 1000,
                "null_count": 0,
                "invalid_count": 5
            }
        }

        candidates = analyzer.suggest_candidates(column_stats)

        # Same score, but col2 has fewer invalids
        scores = {tuple(c["columns"]): c["score"] for c in candidates}
        # Should prefer col2 due to fewer invalids
        assert candidates[0]["columns"] == ["col2"]

    def test_minimum_threshold(self):
        """Should not suggest keys below minimum threshold."""
        analyzer = CandidateKeyAnalyzer(min_score=0.8)

        column_stats = {
            "col1": {
                "distinct_count": 500,
                "total_count": 1000,
                "null_count": 0
            }
        }

        candidates = analyzer.suggest_candidates(column_stats)

        # Score 0.5 is below threshold
        assert len(candidates) == 0
