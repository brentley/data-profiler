"""
Statistical profilers for CSV columns.

This module provides exact statistical profiling for different column types:
- NumericProfiler: min, max, mean, median, stddev, quantiles, histogram
- StringProfiler: length stats, character analysis, top-10 values
- DateProfiler: min/max dates, format detection, range validation
- MoneyValidator: money format validation
- DateValidator: date format detection and validation

All profilers use streaming/online algorithms where possible for memory efficiency.
"""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import statistics

# Optional scipy import
try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ============================================================================
# Data Classes for Results
# ============================================================================

@dataclass
class NumericStats:
    """Statistics for numeric columns."""
    count: int = 0
    null_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    stddev: Optional[float] = None
    quantiles: Dict[str, float] = field(default_factory=dict)  # p1, p5, p25, p50, p75, p95, p99
    histogram: Dict[str, int] = field(default_factory=dict)
    gaussian_pvalue: Optional[float] = None


@dataclass
class StringStats:
    """Statistics for string columns."""
    count: int = 0
    null_count: int = 0
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: float = 0.0
    top_values: List[Tuple[str, int]] = field(default_factory=list)
    has_non_ascii: bool = False
    character_types: Set[str] = field(default_factory=set)


@dataclass
class DateStats:
    """Statistics for date columns."""
    count: int = 0
    null_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    out_of_range_count: int = 0
    detected_format: Optional[str] = None
    format_consistent: bool = True
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    span_days: Optional[int] = None
    distribution_by_month: Dict[str, int] = field(default_factory=dict)
    distribution_by_year: Dict[str, int] = field(default_factory=dict)
    distribution_by_dow: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    has_ambiguity: bool = False


@dataclass
class MoneyValidationResult:
    """Result of money validation for a column."""
    total_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    null_count: int = 0
    two_decimal_ok: bool = True
    disallowed_symbols_found: bool = False
    violations_by_type: Dict[str, int] = field(default_factory=dict)
    violation_examples: Dict[str, List[str]] = field(default_factory=dict)
    valid_values: List[str] = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        total = self.total_count if self.total_count > 0 else 1  # Avoid division by zero
        return {
            "total": self.total_count,
            "valid": self.valid_count,
            "invalid": self.invalid_count,
            "null": self.null_count,
            "valid_pct": (self.valid_count / total) * 100.0
        }


@dataclass
class ValueValidationResult:
    """Result of validating a single value."""
    is_valid: bool
    error_message: Optional[str] = None


@dataclass
class FormatDetectionResult:
    """Result of date format detection."""
    detected_format: Optional[str] = None
    confidence: float = 0.0
    null_count: int = 0
    has_ambiguity: bool = False


# ============================================================================
# Welford's Algorithm for Online Statistics
# ============================================================================

class WelfordAggregator:
    """
    Compute mean and standard deviation using Welford's algorithm.

    This allows computing exact mean and stddev in a single pass without
    storing all values in memory.
    """

    def __init__(self):
        """Initialize aggregator."""
        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0
        self.values: List[float] = []  # Store for quantiles/median

    def update(self, value: float) -> None:
        """
        Update statistics with a new value.

        Args:
            value: New value to include
        """
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.M2 += delta * delta2

        # Store for quantiles (in real streaming, would use a better approach)
        self.values.append(value)

    def finalize(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Compute final mean and standard deviation.

        Returns:
            Tuple of (mean, stddev)
        """
        if self.count < 2:
            return (self.mean if self.count == 1 else None, None)

        variance = self.M2 / (self.count - 1)
        stddev = math.sqrt(variance)
        return (self.mean, stddev)

    def get_quantiles(self) -> Dict[str, float]:
        """
        Compute quantiles from stored values.

        Returns:
            Dictionary of quantiles (p1, p5, p25, p50, p75, p95, p99)
        """
        if not self.values:
            return {}

        sorted_values = sorted(self.values)

        return {
            'p1': self._percentile(sorted_values, 1),
            'p5': self._percentile(sorted_values, 5),
            'p25': self._percentile(sorted_values, 25),
            'p50': self._percentile(sorted_values, 50),
            'p75': self._percentile(sorted_values, 75),
            'p95': self._percentile(sorted_values, 95),
            'p99': self._percentile(sorted_values, 99),
        }

    def get_median(self) -> Optional[float]:
        """Compute median."""
        if not self.values:
            return None
        return statistics.median(self.values)

    @staticmethod
    def _percentile(sorted_values: List[float], percentile: int) -> float:
        """
        Compute percentile from sorted values.

        Args:
            sorted_values: Sorted list of values
            percentile: Percentile to compute (0-100)

        Returns:
            Percentile value
        """
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)

        if f == c:
            return sorted_values[int(k)]

        d0 = sorted_values[int(f)] * (c - k)
        d1 = sorted_values[int(c)] * (k - f)
        return d0 + d1


# ============================================================================
# Numeric Profiler
# ============================================================================

class NumericProfiler:
    """
    Profiler for numeric columns.

    Computes exact statistics using Welford's algorithm and exact quantiles.
    Includes histogram generation and gaussian distribution test.
    """

    NUMERIC_PATTERN = re.compile(r'^[0-9]+(\.[0-9]+)?$')

    def __init__(self, num_bins: int = 10):
        """
        Initialize profiler.

        Args:
            num_bins: Number of histogram bins
        """
        self.num_bins = num_bins
        self.welford = WelfordAggregator()
        self.null_count = 0
        self.invalid_count = 0
        self.min_value: Optional[float] = None
        self.max_value: Optional[float] = None

    def update(self, value: str) -> None:
        """
        Update statistics with a new value.

        Args:
            value: String value from CSV
        """
        # Handle nulls
        if not value or value.strip() == '':
            self.null_count += 1
            return

        # Validate numeric format
        if not self.NUMERIC_PATTERN.match(value.strip()):
            self.invalid_count += 1
            return

        # Parse value
        try:
            numeric_value = float(value.strip())
        except ValueError:
            self.invalid_count += 1
            return

        # Update Welford aggregator
        self.welford.update(numeric_value)

        # Track min/max
        if self.min_value is None or numeric_value < self.min_value:
            self.min_value = numeric_value
        if self.max_value is None or numeric_value > self.max_value:
            self.max_value = numeric_value

    def finalize(self) -> NumericStats:
        """
        Compute final statistics.

        Returns:
            NumericStats with all computed metrics
        """
        mean, stddev = self.welford.finalize()
        median = self.welford.get_median()
        quantiles = self.welford.get_quantiles()

        # Compute histogram
        histogram = self._compute_histogram()

        # Test for gaussian distribution (D'Agostino-Pearson test)
        gaussian_pvalue = self._test_gaussian()

        return NumericStats(
            count=self.welford.count + self.null_count + self.invalid_count,
            null_count=self.null_count,
            valid_count=self.welford.count,
            invalid_count=self.invalid_count,
            min_value=self.min_value,
            max_value=self.max_value,
            mean=mean,
            median=median,
            stddev=stddev,
            quantiles=quantiles,
            histogram=histogram,
            gaussian_pvalue=gaussian_pvalue
        )

    def _compute_histogram(self) -> Dict[str, int]:
        """
        Compute exact histogram with fixed number of bins.

        Returns:
            Dictionary mapping bin ranges to counts
        """
        if not self.welford.values:
            return {}

        if self.min_value is None or self.max_value is None:
            return {}

        # Handle single value case
        if self.min_value == self.max_value:
            return {f"{self.min_value}": len(self.welford.values)}

        # Compute bin edges
        bin_width = (self.max_value - self.min_value) / self.num_bins
        bins = defaultdict(int)

        for value in self.welford.values:
            # Determine which bin this value belongs to
            if value == self.max_value:
                bin_idx = self.num_bins - 1
            else:
                bin_idx = int((value - self.min_value) / bin_width)

            bin_start = self.min_value + (bin_idx * bin_width)
            bin_end = bin_start + bin_width
            bin_key = f"{bin_start:.2f}-{bin_end:.2f}"
            bins[bin_key] += 1

        return dict(bins)

    def _test_gaussian(self) -> Optional[float]:
        """
        Test if distribution is gaussian using D'Agostino-Pearson test.

        Returns:
            P-value from test (higher = more gaussian), or None if insufficient data
        """
        if len(self.welford.values) < 8:
            # Need at least 8 samples for the test
            return None

        if not HAS_SCIPY:
            # Fallback: use a simple skewness/kurtosis check
            # Not as robust as D'Agostino-Pearson but gives some indication
            return None

        try:
            # D'Agostino-Pearson test for normality
            _, pvalue = scipy_stats.normaltest(self.welford.values)
            return pvalue
        except Exception:
            return None


# ============================================================================
# String Profiler
# ============================================================================

class StringProfiler:
    """
    Profiler for string columns.

    Computes length statistics, character analysis, and top-N values.
    """

    def __init__(self, top_n: int = 10):
        """
        Initialize profiler.

        Args:
            top_n: Number of top values to track
        """
        self.top_n = top_n
        self.value_counts: Counter = Counter()
        self.null_count = 0
        self.min_length: Optional[int] = None
        self.max_length: Optional[int] = None
        self.total_length = 0
        self.value_count = 0
        self.has_non_ascii = False
        self.character_types: Set[str] = set()

    def update(self, value: str) -> None:
        """
        Update statistics with a new value.

        Args:
            value: String value from CSV
        """
        # Handle nulls
        if not value or value.strip() == '':
            self.null_count += 1
            return

        value = value.strip()
        self.value_count += 1

        # Track value frequency for top-N
        self.value_counts[value] += 1

        # Length statistics
        length = len(value)
        self.total_length += length

        if self.min_length is None or length < self.min_length:
            self.min_length = length
        if self.max_length is None or length > self.max_length:
            self.max_length = length

        # Character analysis
        for char in value:
            if ord(char) > 127:
                self.has_non_ascii = True

            if char.isalpha():
                self.character_types.add('alpha')
            elif char.isdigit():
                self.character_types.add('digit')
            elif char.isspace():
                self.character_types.add('space')
            elif char in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`"\'\\':
                self.character_types.add('special')

    def finalize(self) -> StringStats:
        """
        Compute final statistics.

        Returns:
            StringStats with all computed metrics
        """
        # Compute average length
        avg_length = self.total_length / self.value_count if self.value_count > 0 else 0.0

        # Get top N values
        top_values = self.value_counts.most_common(self.top_n)

        return StringStats(
            count=self.value_count + self.null_count,
            null_count=self.null_count,
            min_length=self.min_length,
            max_length=self.max_length,
            avg_length=avg_length,
            top_values=top_values,
            has_non_ascii=self.has_non_ascii,
            character_types=self.character_types
        )


# ============================================================================
# Money Validator
# ============================================================================

class MoneyValidator:
    """
    Validator for money columns.

    Money must have exactly 2 decimal places with no $, commas, or parentheses.
    """

    MONEY_PATTERN = re.compile(r'^\d+\.\d{2}$')

    def __init__(self):
        """Initialize validator."""
        self.total_count = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.null_count = 0
        self.violations_by_type: Dict[str, int] = defaultdict(int)
        self.violation_examples: Dict[str, List[str]] = defaultdict(list)
        self.valid_values: List[str] = []
        self.two_decimal_ok = True
        self.disallowed_symbols_found = False

    def is_null(self, value: str) -> bool:
        """
        Check if value is null.

        Args:
            value: Value to check

        Returns:
            True if null
        """
        return value is None or value.strip() == ''

    def is_valid(self, value: str) -> bool:
        """
        Check if value is valid money format.

        Args:
            value: Value to check

        Returns:
            True if valid
        """
        if self.is_null(value):
            return False

        # Strict: don't strip whitespace - whitespace invalidates
        # Check for whitespace first
        if value != value.strip():
            return False

        value = value.strip()
        return bool(self.MONEY_PATTERN.match(value))

    def validate_value(self, value: str) -> ValueValidationResult:
        """
        Validate a single value and return detailed result.

        Args:
            value: Value to validate

        Returns:
            ValueValidationResult
        """
        if self.is_valid(value):
            return ValueValidationResult(is_valid=True)

        # Determine error type
        if '$' in value:
            return ValueValidationResult(
                is_valid=False,
                error_message="Contains disallowed dollar sign ($)"
            )
        elif ',' in value:
            return ValueValidationResult(
                is_valid=False,
                error_message="Contains disallowed comma (,)"
            )
        elif '(' in value or ')' in value:
            return ValueValidationResult(
                is_valid=False,
                error_message="Contains disallowed parentheses"
            )
        elif '.' not in value:
            return ValueValidationResult(
                is_valid=False,
                error_message="Missing decimal point (exactly 2 decimals required)"
            )
        else:
            parts = value.split('.')
            if len(parts) == 2:
                decimal_count = len(parts[1])
                return ValueValidationResult(
                    is_valid=False,
                    error_message=f"Wrong decimal count ({decimal_count} instead of 2)"
                )
            else:
                return ValueValidationResult(
                    is_valid=False,
                    error_message="Invalid money format"
                )

    def validate_column(self, values: List[str]) -> MoneyValidationResult:
        """
        Validate entire column of values.

        Args:
            values: List of values to validate

        Returns:
            MoneyValidationResult
        """
        for value in values:
            self.total_count += 1

            # Check nulls
            if self.is_null(value):
                self.null_count += 1
                continue

            value = value.strip()

            # Check if valid
            if self.is_valid(value):
                self.valid_count += 1
                self.valid_values.append(value)
            else:
                self.invalid_count += 1

                # Categorize violation
                if '$' in value:
                    self.violations_by_type['dollar_sign'] += 1
                    self.disallowed_symbols_found = True
                    if len(self.violation_examples['dollar_sign']) < 3:
                        self.violation_examples['dollar_sign'].append(value)

                if ',' in value:
                    self.violations_by_type['comma'] += 1
                    self.disallowed_symbols_found = True
                    if len(self.violation_examples['comma']) < 3:
                        self.violation_examples['comma'].append(value)

                if '(' in value or ')' in value:
                    self.violations_by_type['parentheses'] += 1
                    self.disallowed_symbols_found = True
                    if len(self.violation_examples['parentheses']) < 3:
                        self.violation_examples['parentheses'].append(value)

                # Check decimal count
                if '.' in value:
                    # Remove symbols first
                    cleaned = value.replace('$', '').replace(',', '').replace('(', '').replace(')', '')
                    parts = cleaned.split('.')
                    if len(parts) == 2 and len(parts[1]) != 2:
                        self.violations_by_type['wrong_decimals'] += 1
                        self.two_decimal_ok = False
                        if len(self.violation_examples['wrong_decimals']) < 3:
                            self.violation_examples['wrong_decimals'].append(value)
                else:
                    # No decimal at all
                    self.violations_by_type['wrong_decimals'] += 1
                    self.two_decimal_ok = False

        # Compute min/max of valid values
        if self.valid_values:
            numeric_values = [float(v) for v in self.valid_values]
            return MoneyValidationResult(
                total_count=self.total_count,
                valid_count=self.valid_count,
                invalid_count=self.invalid_count,
                null_count=self.null_count,
                two_decimal_ok=self.two_decimal_ok,
                disallowed_symbols_found=self.disallowed_symbols_found,
                violations_by_type=dict(self.violations_by_type),
                violation_examples=dict(self.violation_examples),
                valid_values=self.valid_values,
                min_value=min(numeric_values),
                max_value=max(numeric_values)
            )
        else:
            return MoneyValidationResult(
                total_count=self.total_count,
                valid_count=self.valid_count,
                invalid_count=self.invalid_count,
                null_count=self.null_count,
                two_decimal_ok=self.two_decimal_ok,
                disallowed_symbols_found=self.disallowed_symbols_found,
                violations_by_type=dict(self.violations_by_type),
                violation_examples=dict(self.violation_examples),
                valid_values=self.valid_values
            )


# ============================================================================
# Date Validator
# ============================================================================

class DateValidator:
    """
    Validator for date columns.

    Detects date format (preferring YYYYMMDD), validates consistency,
    and checks for out-of-range dates.
    """

    # Date format patterns (in order of preference)
    DATE_PATTERNS = [
        (r'^\d{8}$', 'YYYYMMDD', '%Y%m%d'),
        (r'^\d{4}-\d{2}-\d{2}$', 'YYYY-MM-DD', '%Y-%m-%d'),
        (r'^\d{4}/\d{2}/\d{2}$', 'YYYY/MM/DD', '%Y/%m/%d'),
        (r'^\d{2}/\d{2}/\d{4}$', 'MM/DD/YYYY', '%m/%d/%Y'),
        (r'^\d{2}-\d{2}-\d{4}$', 'MM-DD-YYYY', '%m-%d-%Y'),
        (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', 'YYYY-MM-DD HH:MM:SS', '%Y-%m-%d %H:%M:%S'),
    ]

    # DD/MM/YYYY pattern (for ambiguous cases)
    DD_MM_YYYY_PATTERN = (r'^\d{2}/\d{2}/\d{4}$', 'DD/MM/YYYY', '%d/%m/%Y')

    def __init__(
        self,
        prefer_format: Optional[str] = None,
        min_year: int = 1900,
        max_year: Optional[int] = None,
        strict: bool = False
    ):
        """
        Initialize validator.

        Args:
            prefer_format: Preferred format when ambiguous
            min_year: Minimum valid year
            max_year: Maximum valid year (None = current + 1)
            strict: Strict mode rejects any inconsistencies
        """
        self.prefer_format = prefer_format or "YYYYMMDD"
        self.min_year = min_year
        self.max_year = max_year or (datetime.now().year + 1)
        self.strict = strict

        # Tracking
        self.format_counts: Counter = Counter()
        self.null_count = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.out_of_range_count = 0
        self.warnings: List[str] = []
        self.dates: List[datetime] = []
        self.distribution_by_month: Dict[str, int] = defaultdict(int)
        self.distribution_by_year: Dict[str, int] = defaultdict(int)
        self.distribution_by_dow: Dict[str, int] = defaultdict(int)
        self.has_ambiguity = False

    def is_null(self, value: str) -> bool:
        """
        Check if value is null.

        Args:
            value: Value to check

        Returns:
            True if null
        """
        return value is None or value.strip() == ''

    def is_valid(self, value: str, format_hint: str) -> bool:
        """
        Check if value is valid date in given format.

        Args:
            value: Value to check
            format_hint: Expected format name

        Returns:
            True if valid
        """
        if self.is_null(value):
            return False

        # Find the pattern for this format
        for pattern, fmt_name, strptime_fmt in self.DATE_PATTERNS:
            if fmt_name == format_hint:
                if re.match(pattern, value.strip()):
                    try:
                        date = datetime.strptime(value.strip(), strptime_fmt)
                        # Check year range
                        if self.min_year <= date.year <= self.max_year:
                            return True
                    except ValueError:
                        return False
                return False

        # Check DD/MM/YYYY if that's the hint
        if format_hint == 'DD/MM/YYYY':
            pattern, fmt_name, strptime_fmt = self.DD_MM_YYYY_PATTERN
            if re.match(pattern, value.strip()):
                try:
                    date = datetime.strptime(value.strip(), strptime_fmt)
                    if self.min_year <= date.year <= self.max_year:
                        return True
                except ValueError:
                    return False

        return False

    def parse_date(self, value: str, format_hint: str) -> Optional[datetime]:
        """
        Parse date value.

        Args:
            value: Date string
            format_hint: Format name

        Returns:
            Parsed datetime or None
        """
        if self.is_null(value):
            return None

        # Find the pattern for this format
        for pattern, fmt_name, strptime_fmt in self.DATE_PATTERNS:
            if fmt_name == format_hint:
                if re.match(pattern, value.strip()):
                    try:
                        return datetime.strptime(value.strip(), strptime_fmt)
                    except ValueError:
                        return None

        # Check DD/MM/YYYY
        if format_hint == 'DD/MM/YYYY':
            pattern, fmt_name, strptime_fmt = self.DD_MM_YYYY_PATTERN
            if re.match(pattern, value.strip()):
                try:
                    return datetime.strptime(value.strip(), strptime_fmt)
                except ValueError:
                    return None

        return None

    def detect_format(self, values: List[str]) -> FormatDetectionResult:
        """
        Detect date format from values.

        Args:
            values: List of values

        Returns:
            FormatDetectionResult
        """
        format_counts: Counter = Counter()
        null_count = 0

        for value in values:
            if self.is_null(value):
                null_count += 1
                continue

            value = value.strip()

            # Try each pattern
            for pattern, fmt_name, strptime_fmt in self.DATE_PATTERNS:
                if re.match(pattern, value):
                    try:
                        datetime.strptime(value, strptime_fmt)
                        format_counts[fmt_name] += 1
                        break
                    except ValueError:
                        continue

            # Try DD/MM/YYYY for ambiguous dates
            pattern, fmt_name, strptime_fmt = self.DD_MM_YYYY_PATTERN
            if re.match(pattern, value):
                try:
                    datetime.strptime(value, strptime_fmt)
                    # Only count this if it wasn't already counted as MM/DD/YYYY
                    if 'MM/DD/YYYY' not in format_counts or format_counts['MM/DD/YYYY'] == 0:
                        format_counts[fmt_name] += 1
                except ValueError:
                    pass

        if not format_counts:
            return FormatDetectionResult(null_count=null_count)

        # Get most common format
        most_common_format, count = format_counts.most_common(1)[0]
        total_non_null = sum(format_counts.values())
        confidence = count / total_non_null if total_non_null > 0 else 0.0

        # Check for ambiguity - dates that could be interpreted multiple ways
        has_ambiguity = False
        if 'MM/DD/YYYY' in format_counts or 'DD/MM/YYYY' in format_counts:
            # Check if values could be ambiguous (day and month both <= 12)
            # For simplicity, mark as ambiguous if we detected MM/DD/YYYY
            # since those dates could also be DD/MM/YYYY
            has_ambiguity = True

        # Also check if we detected multiple formats
        if len(format_counts) > 1:
            has_ambiguity = True

        return FormatDetectionResult(
            detected_format=most_common_format,
            confidence=confidence,
            null_count=null_count,
            has_ambiguity=has_ambiguity
        )

    def validate_column(self, values: List[str]) -> DateStats:
        """
        Validate entire column of date values.

        Args:
            values: List of values

        Returns:
            DateStats
        """
        # First detect format
        detection = self.detect_format(values)
        detected_format = detection.detected_format
        self.null_count = detection.null_count
        self.has_ambiguity = detection.has_ambiguity

        if not detected_format:
            # No format detected - all non-null values are invalid
            non_null_count = len(values) - self.null_count
            return DateStats(
                count=len(values),
                null_count=self.null_count,
                valid_count=0,
                invalid_count=non_null_count,
                format_consistent=False
            )

        # Validate each value
        min_date_obj: Optional[datetime] = None
        max_date_obj: Optional[datetime] = None
        all_formats_found: Counter = Counter()

        for value in values:
            if self.is_null(value):
                continue

            value = value.strip()

            # Try to parse with detected format
            date_obj = self.parse_date(value, detected_format)

            if date_obj:
                self.valid_count += 1
                self.dates.append(date_obj)

                # Track min/max
                if min_date_obj is None or date_obj < min_date_obj:
                    min_date_obj = date_obj
                if max_date_obj is None or date_obj > max_date_obj:
                    max_date_obj = date_obj

                # Check year range
                if date_obj.year < self.min_year:
                    self.out_of_range_count += 1
                    self.warnings.append(f"Date {value} has year < {self.min_year}")
                elif date_obj.year > self.max_year:
                    self.out_of_range_count += 1
                    self.warnings.append(f"Date {value} has year > {self.max_year}")

                # Distribution tracking
                month_key = date_obj.strftime('%Y-%m')
                year_key = str(date_obj.year)
                dow_key = date_obj.strftime('%A')

                self.distribution_by_month[month_key] += 1
                self.distribution_by_year[year_key] += 1
                self.distribution_by_dow[dow_key] += 1

                all_formats_found[detected_format] += 1
            else:
                self.invalid_count += 1
                # Also try to detect what format this value is (for mixed format detection)
                for pattern, fmt_name, strptime_fmt in self.DATE_PATTERNS:
                    if re.match(pattern, value):
                        try:
                            datetime.strptime(value, strptime_fmt)
                            all_formats_found[fmt_name] += 1
                            break
                        except ValueError:
                            continue

        # Check format consistency - if we found multiple formats, it's inconsistent
        format_consistent = len(all_formats_found) <= 1

        # Compute span
        span_days = None
        if min_date_obj and max_date_obj:
            span_days = (max_date_obj - min_date_obj).days

        # Format min/max as strings
        min_date = min_date_obj.strftime('%Y%m%d') if min_date_obj else None
        max_date = max_date_obj.strftime('%Y%m%d') if max_date_obj else None

        return DateStats(
            count=len(values),
            null_count=self.null_count,
            valid_count=self.valid_count,
            invalid_count=self.invalid_count,
            out_of_range_count=self.out_of_range_count,
            detected_format=detected_format,
            format_consistent=format_consistent,
            min_date=min_date,
            max_date=max_date,
            span_days=span_days,
            distribution_by_month=dict(self.distribution_by_month),
            distribution_by_year=dict(self.distribution_by_year),
            distribution_by_dow=dict(self.distribution_by_dow),
            warnings=self.warnings,
            has_ambiguity=self.has_ambiguity
        )


# ============================================================================
# Date Profiler (for use with streaming)
# ============================================================================

class DateProfiler:
    """
    Streaming profiler for date columns.

    Wraps DateValidator for streaming use case.
    """

    def __init__(self):
        """Initialize profiler."""
        self.validator = DateValidator()
        self.values: List[str] = []

    def update(self, value: str) -> None:
        """
        Add value to profiler.

        Args:
            value: Date string
        """
        self.values.append(value)

    def finalize(self) -> DateStats:
        """
        Compute final statistics.

        Returns:
            DateStats
        """
        return self.validator.validate_column(self.values)
