"""
Test suite for candidate key suggestion.

RED PHASE: These tests define expected candidate key behavior.

Requirements from spec:
- Auto-suggest candidate keys (single/compound) from high-cardinality, low-null columns
- Score = (distinct_ratio * (1 - null_ratio_sum)) with tie-breakers
- Suggest top K candidates (e.g., 5)
- User confirms/rejects suggestions before duplicate check
"""
import pytest
from pathlib import Path


class TestCandidateKeys:
    """Test candidate key suggestion functionality."""

    def test_suggest_single_column_key(self, temp_dir: Path):
        """Test suggestion of single column as candidate key."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "single_key.csv"
        csv_path.write_text(
            "ID|Name|Age\n"
            "1|Alice|30\n"
            "2|Bob|25\n"
            "3|Charlie|35\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|")

        # ID should be suggested (100% distinct, 0% null)
        id_suggestions = [s for s in suggestions if len(s.columns) == 1 and "ID" in s.columns]
        assert len(id_suggestions) > 0
        assert id_suggestions[0].score > 0.9

    def test_suggest_compound_key(self, temp_dir: Path):
        """Test suggestion of compound key."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "compound_key.csv"
        csv_path.write_text(
            "FirstName|LastName|Age\n"
            "Alice|Smith|30\n"
            "Bob|Jones|25\n"
            "Alice|Jones|35\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|", include_compound=True)

        # FirstName+LastName should be suggested
        compound_suggestions = [
            s for s in suggestions
            if len(s.columns) == 2 and "FirstName" in s.columns and "LastName" in s.columns
        ]
        assert len(compound_suggestions) > 0

    def test_score_calculation(self, temp_dir: Path):
        """Test that key score is calculated correctly."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "scoring.csv"
        csv_path.write_text(
            "HighCard|LowCard|WithNulls\n"
            "1|A|X\n"
            "2|A|Y\n"
            "3|B|\n"
            "4|A|Z\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|")

        # HighCard: distinct_ratio=1.0, null_ratio=0.0 → score=1.0
        high_card_sugg = next(s for s in suggestions if s.columns == ["HighCard"])
        assert high_card_sugg.score == 1.0

        # WithNulls: distinct_ratio=0.75, null_ratio=0.25 → score=0.75*0.75=0.5625
        with_nulls_sugg = next(s for s in suggestions if s.columns == ["WithNulls"])
        assert abs(with_nulls_sugg.score - 0.5625) < 0.01

    def test_high_cardinality_threshold(self, temp_dir: Path):
        """Test that only high-cardinality columns are suggested."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "cardinality.csv"
        lines = ["ID|Status\n"]
        for i in range(100):
            status = "ACTIVE" if i % 2 == 0 else "INACTIVE"
            lines.append(f"{i}|{status}\n")
        csv_path.write_text("".join(lines), encoding="utf-8")

        finder = CandidateKeyFinder(min_cardinality_ratio=0.5)
        suggestions = finder.suggest_keys(csv_path, delimiter="|")

        # ID should be suggested (100% distinct)
        id_suggestions = [s for s in suggestions if "ID" in s.columns]
        assert len(id_suggestions) > 0

        # Status should NOT be suggested (only 2% distinct)
        status_suggestions = [s for s in suggestions if s.columns == ["Status"]]
        assert len(status_suggestions) == 0

    def test_low_null_preference(self, temp_dir: Path):
        """Test that columns with fewer nulls are preferred."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "nulls.csv"
        csv_path.write_text(
            "NoNulls|SomeNulls|ManyNulls\n"
            "1|A|X\n"
            "2|B|\n"
            "3|C|Y\n"
            "4||\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|")

        # Suggestions should be sorted by score (higher is better)
        # NoNulls should score higher than SomeNulls
        no_nulls = next(s for s in suggestions if s.columns == ["NoNulls"])
        some_nulls = next(s for s in suggestions if s.columns == ["SomeNulls"])

        assert no_nulls.score > some_nulls.score

    def test_suggest_top_k_keys(self, temp_dir: Path):
        """Test that only top K candidates are returned."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "many_columns.csv"
        header = "|".join([f"Col{i}" for i in range(20)])
        lines = [header + "\n"]
        for i in range(100):
            row = "|".join([f"Val{i}_{j}" for j in range(20)])
            lines.append(row + "\n")
        csv_path.write_text("".join(lines), encoding="utf-8")

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|", top_k=5)

        # Should return at most 5 suggestions
        assert len(suggestions) <= 5

    def test_tie_breaker_logic(self, temp_dir: Path):
        """Test tie-breaker when multiple keys have same score."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "ties.csv"
        csv_path.write_text(
            "Key1|Key2|Key3\n"
            "A|X|1\n"
            "B|Y|2\n"
            "C|Z|3\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|")

        # All three have same score (1.0)
        # Tie-breaker could be column position or name
        assert all(s.score == 1.0 for s in suggestions[:3])

    def test_compound_key_scoring(self, temp_dir: Path):
        """Test that compound keys are scored appropriately."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "compound_scoring.csv"
        csv_path.write_text(
            "FirstName|LastName|Email\n"
            "Alice|Smith|alice@example.com\n"
            "Bob|Jones|bob@example.com\n"
            "Alice|Jones|alice.jones@example.com\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|", include_compound=True)

        # Email alone should score 1.0 (100% unique)
        email_sugg = next(s for s in suggestions if s.columns == ["Email"])
        assert email_sugg.score == 1.0

        # FirstName+LastName should also score 1.0 (unique combination)
        compound_sugg = next(
            s for s in suggestions
            if len(s.columns) == 2 and "FirstName" in s.columns and "LastName" in s.columns
        )
        assert compound_sugg.score == 1.0

    def test_exclude_columns_with_high_null_ratio(self, temp_dir: Path):
        """Test that columns with too many nulls are excluded."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "high_nulls.csv"
        lines = ["ID|OptionalField\n"]
        for i in range(100):
            optional = f"Val{i}" if i < 10 else ""
            lines.append(f"{i}|{optional}\n")
        csv_path.write_text("".join(lines), encoding="utf-8")

        finder = CandidateKeyFinder(max_null_ratio=0.5)
        suggestions = finder.suggest_keys(csv_path, delimiter="|")

        # OptionalField has 90% nulls, should not be suggested
        optional_suggestions = [s for s in suggestions if "OptionalField" in s.columns]
        assert len(optional_suggestions) == 0

    def test_compound_key_null_handling(self, temp_dir: Path):
        """Test that compound keys consider null ratios from all columns."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "compound_nulls.csv"
        csv_path.write_text(
            "Col1|Col2\n"
            "A|X\n"
            "B|\n"
            "C|Y\n"
            "|Z\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|", include_compound=True)

        # Col1+Col2 compound key should account for nulls in both columns
        compound = next(
            s for s in suggestions
            if len(s.columns) == 2 and "Col1" in s.columns and "Col2" in s.columns
        )
        # null_ratio_sum = 0.25 + 0.25 = 0.5
        # distinct_ratio = 1.0 (all combos unique excluding nulls)
        # score = 1.0 * (1 - 0.5) = 0.5
        assert abs(compound.score - 0.5) < 0.1

    def test_candidate_key_metadata(self, temp_dir: Path):
        """Test that suggestions include useful metadata."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "metadata.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Alice\n"
            "2|Bob\n"
            "3|Charlie\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|")

        suggestion = suggestions[0]
        assert hasattr(suggestion, "columns")
        assert hasattr(suggestion, "score")
        assert hasattr(suggestion, "distinct_ratio")
        assert hasattr(suggestion, "null_ratio_sum")
        assert hasattr(suggestion, "estimated_duplicate_count")

    def test_incremental_compound_key_search(self, temp_dir: Path):
        """Test that compound keys are built incrementally."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "incremental.csv"
        csv_path.write_text(
            "A|B|C\n"
            "1|X|P\n"
            "1|Y|Q\n"
            "2|X|R\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(
            csv_path,
            delimiter="|",
            include_compound=True,
            max_compound_size=3
        )

        # Should suggest A+B, A+C, B+C, and possibly A+B+C
        two_col_compounds = [s for s in suggestions if len(s.columns) == 2]
        assert len(two_col_compounds) > 0

    def test_no_suggestions_when_no_good_keys(self, temp_dir: Path):
        """Test that no suggestions are made when no good keys exist."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "no_keys.csv"
        lines = ["Col1|Col2\n"]
        for i in range(100):
            lines.append(f"A|B\n")  # All values same
        csv_path.write_text("".join(lines), encoding="utf-8")

        finder = CandidateKeyFinder(min_cardinality_ratio=0.5)
        suggestions = finder.suggest_keys(csv_path, delimiter="|")

        # Should return empty or very low-scored suggestions
        assert len(suggestions) == 0 or all(s.score < 0.1 for s in suggestions)

    def test_suggestion_explanation(self, temp_dir: Path):
        """Test that suggestions include human-readable explanations."""
        from api.services.keys import CandidateKeyFinder

        csv_path = temp_dir / "explain.csv"
        csv_path.write_text(
            "ID|Name\n"
            "1|Alice\n"
            "2|Bob\n"
            "3|Charlie\n",
            encoding="utf-8"
        )

        finder = CandidateKeyFinder()
        suggestions = finder.suggest_keys(csv_path, delimiter="|")

        suggestion = suggestions[0]
        assert hasattr(suggestion, "explanation")
        assert "distinct" in suggestion.explanation.lower() or "unique" in suggestion.explanation.lower()
