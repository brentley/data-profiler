"""
Docstring Templates for Data Profiler

This module provides copy-paste templates for documenting Python code
in the data profiler project. Follow these templates when creating new
modules, classes, and functions.

Usage:
    1. Copy relevant template below
    2. Customize with actual function/class details
    3. Update parameter/return descriptions
    4. Add specific examples
    5. Include error codes and See Also references
"""

# ============================================================================
# MODULE-LEVEL DOCSTRING TEMPLATE
# ============================================================================

"""Module: ingest.py

File ingestion pipeline for data profiler.

This module handles the end-to-end file ingestion workflow:
- Stream reading with UTF-8 validation
- CSV parsing with configurable delimiters and quoting
- Column-by-column profiling
- Progress tracking for large files
- Error aggregation and reporting

Classes:
    FileIngester: Main orchestrator for file processing
    RowBuffer: Buffered row processing

Functions:
    read_file_stream: Generator for reading file with validation
    parse_csv_row: Parse single CSV row with quoting support

Example:
    >>> ingester = FileIngester("data.csv", delimiter="|")
    >>> for row in ingester.process():
    ...     print(f"Processed row: {len(row)} columns")
    >>> profile = ingester.finalize()

Performance Considerations:
    - Streaming processing: constant O(1) memory per row
    - Buffering: 10K rows at a time for batch statistics
    - SQLite spill: distinct counting uses on-disk indices

Error Handling:
    - UTF-8 validation: First invalid byte triggers E_UTF8_INVALID
    - Header validation: Missing header triggers E_HEADER_MISSING
    - Row validation: Jagged rows trigger E_JAGGED_ROW

See Also:
    - TYPE_INFERENCE.md: Column type detection
    - ERROR_CODES.md: Error code reference
    - api/services/profile.py: Profiling implementation
"""


# ============================================================================
# CLASS DOCSTRING TEMPLATE - Standard Class
# ============================================================================

class FileIngester:
    """
    Main orchestrator for file ingestion and profiling.

    Handles streaming processing of CSV/TXT files with configurable
    delimiters and quoting rules. Validates input, detects column types,
    computes statistics, and identifies candidate keys.

    This class manages the complete workflow from file upload to profile
    completion, including error handling and progress tracking.

    Attributes:
        file_path (str): Path to input file (may be gzipped)
        delimiter (str): Column delimiter ('|' or ',')
        quoted (bool): Whether CSV-style quoting is expected
        expect_crlf (bool): Whether CRLF line endings expected
        run_id (str): Unique identifier for this profiling run
        profilers (List[ColumnProfiler]): Per-column profilers
        error_aggregator (ErrorAggregator): Collects errors/warnings

    Example:
        Process a pipe-delimited file with profiling:

        >>> ingester = FileIngester(
        ...     file_path="transactions.csv",
        ...     delimiter="|",
        ...     run_id="550e8400-e29b-41d4-a716-446655440000"
        ... )
        >>> for event in ingester.process():
        ...     if event.type == "progress":
        ...         print(f"{event.progress_pct}% complete")
        ...
        >>> profile = ingester.get_profile()
        >>> print(f"Columns: {len(profile.columns)}")

    Raises:
        FileNotFoundError: If input file does not exist
        ValueError: If delimiter is not '|' or ','
        IOError: If file cannot be read

    Error Codes:
        - E_UTF8_INVALID: Invalid UTF-8 encoding detected
        - E_HEADER_MISSING: First row cannot be parsed as header
        - E_JAGGED_ROW: Row has inconsistent column count
        - W_SPILL_DIRECTORY_FULL: Not enough disk space

    Performance:
        - Memory: O(number of columns + top-10 buffer per column)
        - Disk: SQLite indices use 0.1-1x input file size
        - Time: ~3 seconds per GiB (single-threaded)

    Note:
        Null values are automatically detected and tracked separately.
        Data is not normalized; violations are counted and reported.

    See Also:
        - api/services/profile.py: Column profiling logic
        - api/services/distincts.py: Distinct counting
        - ERROR_CODES.md: Complete error reference
    """

    def __init__(
        self,
        file_path: str,
        delimiter: str = "|",
        quoted: bool = True,
        expect_crlf: bool = True,
        run_id: str = None,
    ):
        """
        Initialize file ingester.

        Args:
            file_path: Path to CSV/TXT file (may be .gz compressed)
            delimiter: Column delimiter ('|' or ','), default '|'
            quoted: Whether to expect CSV-style quoting, default True
            expect_crlf: Whether to expect CRLF endings, default True
            run_id: Unique run ID for tracking, generated if not provided

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If delimiter not in ['|', ',']
            TypeError: If parameters have wrong types

        Examples:
            Create ingester for standard pipe-delimited file:

            >>> ingester = FileIngester("data.csv")

            Create ingester with specific configuration:

            >>> ingester = FileIngester(
            ...     "data.csv.gz",
            ...     delimiter=",",
            ...     quoted=True,
            ...     expect_crlf=False,
            ...     run_id="custom-run-id"
            ... )
        """


# ============================================================================
# CLASS DOCSTRING TEMPLATE - Exception/Error Class
# ============================================================================

class ProfilingError(Exception):
    """
    Base exception for profiling errors.

    Represents errors that occur during file processing and profiling.
    Subclass for specific error types.

    Attributes:
        error_code (str): Machine-readable error code (E_* or W_*)
        message (str): Human-readable error message
        row_number (int, optional): Row where error occurred
        column_name (str, optional): Column affected by error
        sample_value (str, optional): Example value causing error

    Examples:
        Catch and handle profiling errors:

        >>> try:
        ...     profile = ingester.process()
        ... except ProfilingError as e:
        ...     print(f"Error {e.error_code}: {e.message}")
        ...     if e.row_number:
        ...         print(f"At row {e.row_number}")

    See Also:
        - ERROR_CODES.md: Full error code reference
        - api/services/errors.py: Error handling implementation
    """


# ============================================================================
# FUNCTION DOCSTRING TEMPLATE - Basic Function
# ============================================================================

def infer_column_type(sample_values: list[str], threshold: float = 0.9) -> str:
    """
    Infer the type of a column from sample values.

    Analyzes a sample of column values to determine the most likely type.
    Types are tested in priority order: numeric, money, date, code, alpha.

    The function matches each value against type patterns and selects the
    type with the highest confidence. If no type exceeds the threshold
    confidence level, returns 'unknown'.

    Args:
        sample_values: List of non-NULL sample values (typically first 10K)
        threshold: Confidence threshold for type selection, range [0.0, 1.0].
                  Default 0.9 means 90% of values must match the pattern.
                  Use 0.8 for data with known quality issues.

    Returns:
        str: One of 'numeric', 'money', 'date', 'code', 'alpha', 'unknown'

    Raises:
        ValueError: If threshold not in range [0.0, 1.0]
        TypeError: If sample_values contains non-string items

    Examples:
        Infer type for clean numeric column:

        >>> values = ["100", "200.50", "150"]
        >>> inferred_type = infer_column_type(values)
        >>> assert inferred_type == "numeric"

        Infer type with lower threshold for mixed data:

        >>> mixed_values = ["100", "200", "N/A"]
        >>> inferred_type = infer_column_type(mixed_values, threshold=0.8)
        >>> # Still detects "numeric" if 80%+ are numeric

        Infer type for money column:

        >>> money_values = ["100.00", "150.50", "200.25"]
        >>> inferred_type = infer_column_type(money_values)
        >>> assert inferred_type == "money"

    Note:
        - NULL values ("", "NULL", etc.) are excluded during detection
        - Type priority is: numeric > money > date > code > alpha
        - Use lower threshold for data quality assessments
        - If multiple types tie at same confidence, first in priority wins

    Error Codes:
        No errors; returns 'unknown' if type cannot be determined

    Performance:
        - Time: O(n*m) where n=sample size, m=pattern complexity
        - Memory: O(1) - only counts maintained
        - Typical: < 10ms for 10K sample values

    See Also:
        - TYPE_INFERENCE.md: Detailed type detection algorithm
        - api/services/types.py: Type validation implementation
        - tests/test_types.py: Type inference tests
    """


# ============================================================================
# FUNCTION DOCSTRING TEMPLATE - Complex Function with Error Handling
# ============================================================================

def calculate_statistics(
    values: list[float],
    compute_quantiles: bool = True,
    gaussian_test: str = "dagostino"
) -> dict:
    """
    Calculate comprehensive statistics for numeric values.

    Uses Welford's algorithm for numerically stable online mean and
    variance calculation, suitable for very large datasets without
    loading all values into memory.

    Computed metrics:
    - Center: minimum, maximum, mean, median
    - Spread: standard deviation, variance, range
    - Distribution: quantiles (p1, p5, p25, p50, p75, p95, p99)
    - Normality: Gaussian test p-value and test statistic

    Args:
        values: List of numeric values to analyze
        compute_quantiles: Whether to compute quantile percentiles.
                          Set False to skip for performance. Default True.
        gaussian_test: Which test to use for normality ('dagostino', 'shapiro').
                      Default 'dagostino' for better large-sample performance.

    Returns:
        Dictionary with keys:
        - min (float): Minimum value
        - max (float): Maximum value
        - mean (float): Arithmetic mean
        - median (float): 50th percentile
        - stddev (float): Standard deviation
        - variance (float): Variance
        - count (int): Number of values
        - quantiles (dict): Percentiles (if compute_quantiles=True)
        - gaussian_pvalue (float): P-value for normality test
        - gaussian_statistic (float): Test statistic

    Raises:
        ValueError: If values list is empty
        TypeError: If values contain non-numeric items
        RuntimeError: If Gaussian test computation fails

    Examples:
        Calculate statistics for numeric column:

        >>> values = [100.0, 150.5, 200.0, 250.75, 300.0]
        >>> stats = calculate_statistics(values)
        >>> print(f"Mean: {stats['mean']:.2f}")
        Mean: 200.25
        >>> print(f"Median: {stats['median']:.2f}")
        Median: 200.00
        >>> print(f"Std Dev: {stats['stddev']:.2f}")
        Std Dev: 79.06

        Calculate without quantiles (faster):

        >>> stats = calculate_statistics(values, compute_quantiles=False)
        >>> assert 'quantiles' not in stats

        Use Shapiro test instead of D'Agostino:

        >>> stats = calculate_statistics(values, gaussian_test='shapiro')

    Performance:
        - Time with quantiles: O(n log n) due to sorting
        - Time without quantiles: O(n) using Welford's algorithm
        - Memory: O(1) if compute_quantiles=False, O(n) if True
        - For 1M values: ~100ms with quantiles, ~20ms without

    Note:
        - NaN values are automatically filtered out
        - Infinite values raise ValueError
        - For very large datasets, disable quantiles for speed
        - Gaussian test may be unreliable for small samples (n < 20)

    Error Codes:
        - STATS_E_001: Empty values list provided
        - STATS_E_002: Non-numeric value in list
        - STATS_E_003: Gaussian test failed

    See Also:
        - DATA_MODEL.md: Numeric statistics schema
        - tests/test_stats.py: Statistics calculation tests
        - https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
    """


# ============================================================================
# FUNCTION DOCSTRING TEMPLATE - API Endpoint Handler
# ============================================================================

def get_profile(run_id: str) -> dict:
    """
    Retrieve complete profiling results for a run.

    Fetches full profile data including file metadata, per-column statistics,
    error roll-ups, and candidate key suggestions. Profile is generated from
    database records created during profiling.

    The response includes all information needed for the frontend dashboard
    and is suitable for JSON export.

    Args:
        run_id: UUID of the profiling run

    Returns:
        Dictionary representing Profile object with keys:
        - run_id (str): Run identifier
        - file (dict): File metadata (rows, columns, delimiter, etc.)
        - columns (list): Array of ColumnProfile objects
        - errors (list): Error objects with codes and counts
        - warnings (list): Warning objects
        - candidate_keys (list): Suggested uniqueness keys

    Raises:
        ValueError: If run_id format is invalid
        RunNotFoundError: If run does not exist in database
        ProfilingError: If profile generation fails

    HTTP Status Codes:
        200 OK: Profile retrieved successfully
        202 Accepted: Profile still being computed (retry later)
        404 Not Found: Run ID does not exist
        500 Internal Server Error: Profile generation failed

    Examples:
        Get profile for completed run:

        >>> profile = get_profile("550e8400-e29b-41d4-a716-446655440000")
        >>> print(f"Rows: {profile['file']['rows']}")
        Rows: 1000000
        >>> print(f"Columns: {len(profile['columns'])}")
        Columns: 15

        Handle in-progress run:

        >>> try:
        ...     profile = get_profile(run_id)
        ... except HTTPException as e:
        ...     if e.status_code == 202:
        ...         print("Still processing, retry in 1 second")

    Note:
        - Profile is rebuilt from database on each request (not cached)
        - For large profiles (10M+ distinct values), response may be slow
        - Consider using /metrics.csv for summary data on large profiles

    Error Codes:
        - E_RUN_NOT_FOUND: Run ID does not exist
        - E_PROFILE_GENERATION_FAILED: Profile computation error

    Performance:
        - Time: O(1) for metadata, O(n) for n columns
        - Typical: 100-500ms for 100-column profile
        - Large profiles (250+ columns): 1-5 seconds

    See Also:
        - API.md: Full endpoint documentation
        - GET /runs/{run_id}/metrics.csv: Alternative for summary data
        - GET /runs/{run_id}/status: Check processing status
    """


# ============================================================================
# PYDANTIC MODEL DOCSTRING TEMPLATE
# ============================================================================

class ColumnProfile:
    """
    Profiling results for a single column.

    Contains all statistics, metrics, and validation results for a column.
    One ColumnProfile object per column in the input file.

    Attributes:
        name (str): Column name from CSV header
        inferred_type (str): Detected type (alpha|varchar|code|numeric|money|date)
        null_pct (float): Percentage of NULL/empty values (0-100)
        distinct_count (int): Count of unique values (nulls excluded)
        duplicate_count (int): Number of duplicate occurrences (if keys confirmed)
        length (dict): String length statistics (min, max, avg)
        top_values (list): Top 10 most common values with occurrence counts
        numeric_stats (dict): Statistics if inferred_type is numeric or money
        date_stats (dict): Date statistics if inferred_type is date

    Validation:
        - null_pct: Must be in range [0, 100]
        - distinct_count: Must be >= 0 and <= total rows
        - length.min/max/avg: Must be >= 0
        - top_values: List of at most 10 {value, count} objects

    Examples:
        Numeric column profile:

        >>> column = ColumnProfile(
        ...     name="amount",
        ...     inferred_type="numeric",
        ...     null_pct=0.5,
        ...     distinct_count=50000,
        ...     numeric_stats={
        ...         "min": 0.01,
        ...         "max": 9999.99,
        ...         "mean": 245.67
        ...     }
        ... )

        String column profile:

        >>> column = ColumnProfile(
        ...     name="description",
        ...     inferred_type="varchar",
        ...     null_pct=2.0,
        ...     distinct_count=10000,
        ...     length={"min": 5, "max": 500, "avg": 150.5},
        ...     top_values=[
        ...         {"value": "Standard", "count": 5000},
        ...         {"value": "Premium", "count": 3000}
        ...     ]
        ... )

    Note:
        - Null values never appear in distinct_count
        - Null values never appear in top_values
        - For mixed-type columns, inferred_type is "mixed"
        - Type-specific stats (numeric_stats, date_stats) are None for other types

    See Also:
        - TYPE_INFERENCE.md: Type detection details
        - API.md: Complete ColumnProfile schema
        - tests/test_models.py: Model validation tests
    """


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

"""
HOW TO USE THESE TEMPLATES:

1. Copy the appropriate template for your code element (module, class, function)

2. Replace placeholder sections:
   - Replace "module.py" with actual module name
   - Replace "ClassName" with actual class name
   - Replace "function_name" with actual function name
   - Update parameter names and types
   - Update return type descriptions
   - Update Examples section with realistic examples
   - Add error codes relevant to your function
   - Add See Also references to related documentation

3. Follow these guidelines:
   - Keep first line concise (one-liner for functions)
   - Use imperative voice: "Validate" not "Validates"
   - Describe What, not How (Why code is needed)
   - Include real examples from actual usage
   - Reference error codes from ERROR_CODES.md
   - Link to related documentation in See Also
   - Document performance characteristics for complex functions

4. Validation:
   - Check docstring with: python -m pydoc module.function
   - Verify links in See Also are correct
   - Test examples actually work
   - Ensure error codes are defined in ERROR_CODES.md

5. Common mistakes to avoid:
   - Don't repeat what the type hints already say
   - Don't include implementation details in docstring
   - Don't forget the Examples section
   - Don't forget Error Codes and See Also
   - Don't make examples too trivial or too complex
"""
