"""
Type inference engine for CSV columns.

This module provides type detection for all column types:
- Numeric: digits and optional single decimal point
- Money: exactly 2 decimals, no $, commas, or parentheses
- Date: prefer YYYYMMDD; otherwise one consistent format per column
- Alpha: strings with letters only
- Varchar: general strings
- Code: dictionary-like strings with limited distinct values
- Mixed: multiple types detected in same column
- Unknown: cannot determine type
"""

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import Counter


class ColumnType(Enum):
    """Column type enumeration."""
    ALPHA = "alpha"
    VARCHAR = "varchar"
    CODE = "code"
    NUMERIC = "numeric"
    MONEY = "money"
    DATE = "date"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class ColumnTypeInfo:
    """Information about a column's inferred type."""

    inferred_type: str  # One of: alpha, varchar, code, numeric, money, date, mixed, unknown
    detected_format: Optional[str] = None  # For dates: YYYYMMDD, YYYY-MM-DD, etc.
    null_count: int = 0
    error_count: int = 0  # Format violations (not normalized, just counted)
    warning_count: int = 0
    cardinality_ratio: float = 0.0  # distinct_count / total_count
    distinct_values: Set[str] = field(default_factory=set)
    sample_values: List[str] = field(default_factory=list)
    confidence: float = 0.0  # Confidence level (0-1)
    invalid_count: int = 0  # Alias for error_count
    out_of_range_count: int = 0  # For dates: year out of range warnings
    distinct_ratio: float = 0.0  # Alias for cardinality_ratio

    def __post_init__(self):
        """Set up aliases for backward compatibility."""
        # invalid_count is an alias for error_count
        if self.invalid_count == 0 and self.error_count > 0:
            self.invalid_count = self.error_count
        # distinct_ratio is an alias for cardinality_ratio
        if self.distinct_ratio == 0.0 and self.cardinality_ratio > 0.0:
            self.distinct_ratio = self.cardinality_ratio


@dataclass
class TypeInferenceResult:
    """Result of type inference for a CSV file."""

    columns: Dict[str, ColumnTypeInfo]
    inference_method: str = "full"  # "full" or "sample"


class TypeInferrer:
    """
    Type inference engine for CSV columns.

    Detects column types based on content analysis with strict validation rules.
    Does NOT normalize data - only detects and counts violations.
    """

    # Regex patterns for type detection
    NUMERIC_PATTERN = re.compile(r'^[0-9]+(\.[0-9]+)?$')
    MONEY_PATTERN = re.compile(r'^[0-9]+\.[0-9]{2}$')  # Exactly 2 decimals
    ALPHA_PATTERN = re.compile(r'^[a-zA-Z]+$')

    # Date format patterns (in order of preference)
    DATE_PATTERNS = [
        (r'^\d{8}$', 'YYYYMMDD', '%Y%m%d'),
        (r'^\d{4}-\d{2}-\d{2}$', 'YYYY-MM-DD', '%Y-%m-%d'),
        (r'^\d{4}/\d{2}/\d{2}$', 'YYYY/MM/DD', '%Y/%m/%d'),
        (r'^\d{2}/\d{2}/\d{4}$', 'MM/DD/YYYY', '%m/%d/%Y'),
        (r'^\d{2}-\d{2}-\d{4}$', 'MM-DD-YYYY', '%m-%d-%Y'),
    ]

    # Thresholds
    TYPE_CONFIDENCE_THRESHOLD = 0.66  # 66% of values must match for type (2/3 majority)
    CODE_CARDINALITY_THRESHOLD = 0.50  # <=50% distinct values = code type
    MAX_CODE_DISTINCT = 50  # Maximum distinct values for code type
    MIN_SAMPLE_FOR_CODE = 6  # Minimum sample size to classify as code

    def __init__(self, sample_size: Optional[int] = None, type_hint: Optional[ColumnType] = None):
        """
        Initialize type inferrer.

        Args:
            sample_size: If set, only sample this many rows for inference
            type_hint: Optional type hint to guide inference
        """
        self.sample_size = sample_size
        self.type_hint = type_hint

    def infer_type(self, values: List[str]) -> ColumnTypeInfo:
        """
        Infer type from a list of values.

        This is a convenience method for testing and direct value analysis.

        Args:
            values: List of string values to analyze

        Returns:
            ColumnTypeInfo with inferred type and statistics
        """
        # Create a ColumnTypeInfo object to collect statistics
        col_info = ColumnTypeInfo(inferred_type="unknown")

        # Process values
        for value in values:
            if value is None:
                value = ""
            value = str(value).strip()

            # Track null values
            if not value:
                col_info.null_count += 1
                continue

            # Track distinct values
            col_info.distinct_values.add(value)

            # Store sample values (limited to 100)
            if len(col_info.sample_values) < 100:
                col_info.sample_values.append(value)

        # Calculate cardinality ratio
        total_values = len(col_info.sample_values)
        total_count = total_values + col_info.null_count

        if total_count > 0:
            col_info.cardinality_ratio = len(col_info.distinct_values) / total_count
            col_info.distinct_ratio = col_info.cardinality_ratio

        # Detect type
        if total_values > 0:
            col_info.inferred_type = self._detect_type(col_info)

            # Calculate confidence based on type matches
            confidence = self._calculate_confidence(col_info)
            col_info.confidence = confidence

            # Set invalid_count as alias for error_count
            col_info.invalid_count = col_info.error_count

            # For date columns, check for out-of-range years
            if col_info.inferred_type == "date":
                col_info.out_of_range_count = self._count_date_range_warnings(col_info.sample_values)
        else:
            col_info.inferred_type = "unknown"
            col_info.confidence = 0.0

        return col_info

    def infer_column_types(
        self,
        csv_path: Path,
        delimiter: str = '|'
    ) -> TypeInferenceResult:
        """
        Infer types for all columns in a CSV file.

        Args:
            csv_path: Path to CSV file
            delimiter: CSV delimiter

        Returns:
            TypeInferenceResult with inferred types for each column
        """
        columns: Dict[str, ColumnTypeInfo] = {}

        # First pass: collect sample values for each column
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            headers = reader.fieldnames

            if not headers:
                return TypeInferenceResult(columns={})

            # Initialize column info
            for header in headers:
                columns[header] = ColumnTypeInfo(inferred_type="unknown")

            # Collect values
            row_count = 0
            for row in reader:
                row_count += 1

                for header in headers:
                    value = row.get(header, '').strip()
                    col_info = columns[header]

                    # Track null values
                    if not value:
                        col_info.null_count += 1
                        continue

                    # Track distinct values
                    col_info.distinct_values.add(value)

                    # Store sample values (limited)
                    if len(col_info.sample_values) < 100:
                        col_info.sample_values.append(value)

                # Stop if we hit sample size
                if self.sample_size and row_count >= self.sample_size:
                    break

        # Second pass: infer types based on collected samples
        for header, col_info in columns.items():
            total_values = len(col_info.sample_values)

            if total_values == 0:
                col_info.inferred_type = "unknown"
                continue

            # Calculate cardinality ratio
            col_info.cardinality_ratio = (
                len(col_info.distinct_values) / (total_values + col_info.null_count)
                if (total_values + col_info.null_count) > 0
                else 0.0
            )

            # Detect type
            col_info.inferred_type = self._detect_type(col_info)

        inference_method = "sample" if self.sample_size else "full"
        return TypeInferenceResult(columns=columns, inference_method=inference_method)

    def _detect_type(self, col_info: ColumnTypeInfo) -> str:
        """
        Detect the type of a column based on its sample values.

        Args:
            col_info: Column information with sample values

        Returns:
            Type name: alpha, varchar, code, numeric, money, date, mixed, unknown
        """
        if not col_info.sample_values:
            return "unknown"

        # Count matches for each type
        type_matches = {
            'numeric': 0,
            'money': 0,
            'date': 0,
            'alpha': 0,
        }

        date_formats: Counter = Counter()
        total = len(col_info.sample_values)

        for value in col_info.sample_values:
            # Check date FIRST (before numeric) since dates like 20221109 match numeric pattern
            date_format = self._detect_date_format(value)
            if date_format:
                type_matches['date'] += 1
                date_formats[date_format] += 1
                continue  # Don't check other types if it's a date

            # Check money (most specific numeric)
            if self._is_money(value):
                type_matches['money'] += 1
                continue

            # Check for money-like with violations
            if self._is_money_like_with_violations(value):
                type_matches['money'] += 1
                continue

            # Check numeric (less specific than money)
            if self._is_numeric(value):
                type_matches['numeric'] += 1
                continue

            # Check for numeric-like with violations (commas, $, parentheses)
            if self._is_numeric_like_with_violations(value):
                type_matches['numeric'] += 1
                continue

            # Check alpha
            if self._is_alpha(value):
                type_matches['alpha'] += 1
                continue

        # Determine primary type based on confidence threshold
        max_matches = max(type_matches.values())
        confidence = max_matches / total if total > 0 else 0.0

        # If confidence is below threshold, it's mixed
        if confidence < self.TYPE_CONFIDENCE_THRESHOLD:
            # Check if we have multiple types above a lower threshold
            types_above_threshold = [
                t for t, count in type_matches.items()
                if count / total >= 0.20  # 20% threshold for mixed detection
            ]
            if len(types_above_threshold) > 1:
                return "mixed"

        # Identify the dominant type (in order of specificity)
        if type_matches['date'] / total >= self.TYPE_CONFIDENCE_THRESHOLD:
            # Check date format consistency
            if len(date_formats) > 1:
                # Mixed date formats - warning
                col_info.warning_count = sum(
                    count for fmt, count in date_formats.items()
                    if fmt != date_formats.most_common(1)[0][0]
                )
                col_info.detected_format = date_formats.most_common(1)[0][0]
            else:
                # Single consistent format
                col_info.detected_format = date_formats.most_common(1)[0][0] if date_formats else None
            return "date"

        # For money vs numeric: decide based on patterns and violations
        elif type_matches['money'] > 0 or type_matches['numeric'] > 0:
            combined_numeric = type_matches['money'] + type_matches['numeric']

            # If combined numeric/money confidence is high enough
            if combined_numeric / total >= self.TYPE_CONFIDENCE_THRESHOLD:
                # Decide between money and numeric
                money_ratio = type_matches['money'] / total if total > 0 else 0

                # If money values meet threshold, it's a money column
                if money_ratio >= self.TYPE_CONFIDENCE_THRESHOLD:
                    col_info.error_count = self._count_money_violations(col_info.sample_values)
                    return "money"

                # If money values are present but below threshold
                elif type_matches['money'] > 0:
                    # Check if there are EXPLICIT money-like violations ($, commas, etc.)
                    has_explicit_violations = self._has_explicit_money_violations(col_info.sample_values)

                    # Check if there are values with WRONG decimal counts (not 0, not 2)
                    has_wrong_decimal_counts = self._has_wrong_decimal_counts(col_info.sample_values)

                    # Count potential money violations
                    money_violations = self._count_money_violations(col_info.sample_values)

                    # Strong evidence of money intent:
                    # 1. Explicit violations ($, commas, etc.)
                    # 2. Values with wrong decimal counts (suggests attempting money format)
                    if has_explicit_violations or has_wrong_decimal_counts:
                        col_info.error_count = money_violations
                        return "mixed" if type_matches['numeric'] > 0 else "money"
                    else:
                        # No strong evidence of money intent - it's just numeric
                        # (the 2-decimal values are coincidental)
                        col_info.error_count = self._count_numeric_violations(col_info.sample_values)
                        return "numeric"
                else:
                    # No money pattern, just numeric
                    col_info.error_count = self._count_numeric_violations(col_info.sample_values)
                    return "numeric"

        elif type_matches['alpha'] / total >= self.TYPE_CONFIDENCE_THRESHOLD:
            # Check if it's a code type (low cardinality AND reasonable sample size)
            if self._is_code_type(col_info):
                return "code"
            return "alpha"

        else:
            # Not numeric, date, or alpha - check if code or varchar
            if self._is_code_type(col_info):
                return "code"
            elif max_matches > 0 or len(col_info.sample_values) > 0:
                # Has some type matches but not enough confidence, OR has values but no type matched
                # Either way, it's string data that doesn't fit specific patterns = varchar
                return "varchar"
            else:
                # Truly no data to classify
                return "unknown"

    def _is_numeric(self, value: str) -> bool:
        """
        Check if value matches numeric pattern.

        Numeric: digits and optional single decimal point, no commas, $, or parentheses.

        Args:
            value: Value to check

        Returns:
            True if numeric pattern matches
        """
        return bool(self.NUMERIC_PATTERN.match(value))

    def _is_money(self, value: str) -> bool:
        """
        Check if value matches money pattern.

        Money: exactly 2 decimal places, no $, commas, or parentheses.

        Args:
            value: Value to check

        Returns:
            True if money pattern matches
        """
        return bool(self.MONEY_PATTERN.match(value))

    def _is_alpha(self, value: str) -> bool:
        """
        Check if value is alphabetic only.

        Args:
            value: Value to check

        Returns:
            True if alpha pattern matches
        """
        return bool(self.ALPHA_PATTERN.match(value))

    def _is_numeric_like_with_violations(self, value: str) -> bool:
        """
        Check if value looks numeric but has format violations.

        This includes values like: $123, 1,234, (99.99)

        Args:
            value: Value to check

        Returns:
            True if it looks numeric with violations
        """
        # Remove common numeric violations and see if what remains is numeric
        cleaned = value.replace('$', '').replace(',', '').replace('(', '').replace(')', '').strip()

        # If cleaned version is numeric, then original had violations
        if cleaned and self._is_numeric(cleaned):
            return True

        return False

    def _is_money_like_with_violations(self, value: str) -> bool:
        """
        Check if value looks like money but has format violations.

        This includes values like: $100.00, 1,234.50, (99.99)
        Does NOT include: plain integers, or values with 1/3/4+ decimals (those are numeric)

        Args:
            value: Value to check

        Returns:
            True if it looks like money with violations
        """
        # If it has no violation symbols, it's not "money-like with violations"
        # Values with wrong decimal counts are just numeric, not money violations
        # Money violations require $ , or () symbols
        if '$' not in value and ',' not in value and '(' not in value and ')' not in value:
            return False

        # Has violation symbols - check if it looks money-like after cleaning
        cleaned = value.replace('$', '').replace(',', '').replace('(', '').replace(')', '').strip()

        # If cleaned version looks like money or numeric with decimals, then it's money-like
        if cleaned and (self._is_money(cleaned) or (self._is_numeric(cleaned) and '.' in cleaned)):
            return True

        return False

    def _detect_date_format(self, value: str) -> Optional[str]:
        """
        Detect date format of a value.

        Tries patterns in order of preference (YYYYMMDD first).

        Args:
            value: Value to check

        Returns:
            Format name if date detected, None otherwise
        """
        for pattern, format_name, strptime_format in self.DATE_PATTERNS:
            if re.match(pattern, value):
                # Validate it's actually a valid date
                try:
                    datetime.strptime(value, strptime_format)
                    return format_name
                except ValueError:
                    # Not a valid date
                    continue
        return None

    def _is_code_type(self, col_info: ColumnTypeInfo) -> bool:
        """
        Check if column should be classified as code type.

        Code type: dictionary-like with limited distinct values relative to total rows.
        Requires a reasonable sample size to avoid false positives on small datasets.

        Args:
            col_info: Column information

        Returns:
            True if column should be code type
        """
        distinct_count = len(col_info.distinct_values)
        total_count = len(col_info.sample_values) + col_info.null_count

        # Need at least MIN_SAMPLE_FOR_CODE total values to classify as code
        # (to avoid false positives on very small samples)
        if total_count < self.MIN_SAMPLE_FOR_CODE:
            return False

        # Check if cardinality is low enough (<= threshold)
        if col_info.cardinality_ratio <= self.CODE_CARDINALITY_THRESHOLD:
            return True

        # Also check absolute distinct count (but only if sample is large enough)
        if distinct_count <= self.MAX_CODE_DISTINCT and total_count >= 50:
            return True

        return False

    def _count_numeric_violations(self, values: List[str]) -> int:
        """
        Count numeric format violations (commas, $, parentheses).

        Args:
            values: List of values to check

        Returns:
            Number of violations
        """
        violations = 0
        for value in values:
            # Check for violations
            if '$' in value or ',' in value or '(' in value or ')' in value:
                violations += 1
        return violations

    def _has_explicit_money_violations(self, values: List[str]) -> bool:
        """
        Check if there are EXPLICIT money violations ($, commas, parentheses).

        This indicates clear money intent, as opposed to just having wrong decimal counts.

        Args:
            values: List of values to check

        Returns:
            True if explicit violations found
        """
        for value in values:
            if '$' in value or ',' in value or '(' in value or ')' in value:
                return True
        return False

    def _has_wrong_decimal_counts(self, values: List[str]) -> bool:
        """
        Check if there are values with wrong decimal counts (not 0, not 2).

        This suggests an attempt at money formatting with errors.
        Values like 250.5 (1 decimal) or 99.999 (3 decimals) indicate money intent.

        Args:
            values: List of values to check

        Returns:
            True if values with wrong decimal counts found
        """
        for value in values:
            if not value.strip():
                continue
            if self._is_numeric(value) and '.' in value:
                parts = value.split('.')
                if len(parts) == 2 and len(parts[1]) not in [0, 2]:
                    # Has decimals but not 0 or 2 - wrong count
                    return True
        return False

    def _count_money_violations(self, values: List[str]) -> int:
        """
        Count money format violations (not exactly 2 decimals, $, commas, parentheses).

        Args:
            values: List of values to check

        Returns:
            Number of violations
        """
        violations = 0
        for value in values:
            # Skip empty values
            if not value.strip():
                continue

            # Check for disallowed symbols
            if '$' in value or ',' in value or '(' in value or ')' in value:
                violations += 1
                continue

            # Check if it's numeric but not exactly 2 decimals
            if self._is_numeric(value) and not self._is_money(value):
                violations += 1
                continue

            # Check if it's not numeric at all (non-numeric string in a numeric column)
            if not self._is_numeric(value):
                violations += 1

        return violations

    def _calculate_confidence(self, col_info: ColumnTypeInfo) -> float:
        """
        Calculate confidence level for inferred type.

        Args:
            col_info: Column information with inferred type

        Returns:
            Confidence level (0-1)
        """
        if not col_info.sample_values:
            return 0.0

        total = len(col_info.sample_values)
        matches = 0

        inferred_type = col_info.inferred_type

        # Count how many values match the inferred type
        for value in col_info.sample_values:
            if inferred_type == "numeric":
                if self._is_numeric(value) or self._is_numeric_like_with_violations(value):
                    matches += 1
            elif inferred_type == "money":
                if self._is_money(value) or self._is_money_like_with_violations(value):
                    matches += 1
            elif inferred_type == "date":
                if self._detect_date_format(value):
                    matches += 1
            elif inferred_type == "alpha":
                if self._is_alpha(value):
                    matches += 1
            elif inferred_type in ["varchar", "code"]:
                # String types - always match if not another type
                if not (self._is_numeric(value) or self._is_money(value) or
                       self._detect_date_format(value)):
                    matches += 1
            elif inferred_type == "mixed":
                # Mixed type has lower confidence by definition
                matches = int(total * 0.6)  # 60% confidence for mixed
            elif inferred_type == "unknown":
                return 0.0

        return matches / total if total > 0 else 0.0

    def _count_date_range_warnings(self, values: List[str]) -> int:
        """
        Count dates with years outside reasonable range.

        Args:
            values: List of date values

        Returns:
            Number of dates with out-of-range years
        """
        from datetime import datetime

        warnings = 0
        current_year = datetime.now().year
        min_year = 1900
        max_year = current_year + 1

        for value in values:
            date_format = self._detect_date_format(value)
            if not date_format:
                continue

            # Extract year based on format
            try:
                if date_format == "YYYYMMDD":
                    year = int(value[:4])
                elif date_format in ["YYYY-MM-DD", "YYYY/MM/DD"]:
                    year = int(value[:4])
                elif date_format in ["MM/DD/YYYY", "MM-DD-YYYY"]:
                    year = int(value[-4:])
                else:
                    continue

                if year < min_year or year > max_year:
                    warnings += 1
            except (ValueError, IndexError):
                continue

        return warnings


# ============================================================================
# Validators for Money and Date (from profile module)
# Import these here for test compatibility
# ============================================================================

# Re-export from profile module to maintain backward compatibility with tests
def _lazy_import_validators():
    """Lazy import to avoid circular dependencies."""
    try:
        from services.profile import MoneyValidator, DateValidator
        return MoneyValidator, DateValidator
    except ImportError:
        # If profile module not available, return None
        return None, None


# Make validators available when imported
MoneyValidator, DateValidator = _lazy_import_validators()
