# Code Documentation and Coding Standards

Standards and guidelines for documenting Python and TypeScript code in the data profiler project.

## Python Code Documentation

### Module-Level Docstrings

Every Python module must start with a docstring:

```python
"""
app.py - FastAPI application entry point.

Defines all API endpoints, middleware configuration, and service initialization.
This module is responsible for starting the Uvicorn server and handling all
HTTP requests to the data profiler API.

Global Variables:
    app: FastAPI application instance
    logger: Configured logger for application events

Example:
    To run the application:

        $ uvicorn app:app --reload --host 0.0.0.0 --port 8000

    The API will be available at http://localhost:8000/docs
"""
```

### Class Docstrings

Document class purpose, attributes, and usage:

```python
class ColumnProfiler:
    """
    Profile a single column from CSV data.

    This class handles type inference, statistical calculation, and
    validation for a single column across all rows. It uses a streaming
    algorithm to minimize memory usage on large datasets.

    Attributes:
        name (str): Column name from header
        ordinal (int): 0-based column position
        values (List[str]): Buffer of values being profiled (internal)
        inferred_type (ColumnType): Detected type after profiling
        statistics (dict): Computed statistics for the column

    Example:
        >>> profiler = ColumnProfiler("user_id", 0)
        >>> for row in csv_rows:
        ...     profiler.add_value(row[0])
        >>> result = profiler.finalize()
        >>> print(f"Type: {result.inferred_type}")
        Type: code
        >>> print(f"Distinct: {result.statistics['distinct_count']}")
        Distinct: 1000000

    Note:
        Null handling: Empty strings and whitespace-only values are
        treated as NULL and excluded from most statistics.

    Raises:
        TypeError: If add_value() receives non-string input
        ValueError: If finalize() called before any values added
    """

    def __init__(self, name: str, ordinal: int):
        """
        Initialize column profiler.

        Args:
            name: Column name from CSV header
            ordinal: 0-based column index

        Raises:
            ValueError: If ordinal is negative
        """
        self.name = name
        self.ordinal = ordinal
        self.values = []
        self.inferred_type = None
        self.statistics = {}
```

### Function Docstrings

Use Google-style docstrings:

```python
def infer_column_type(sample_values: List[str], threshold: float = 0.9) -> ColumnType:
    """
    Infer the type of a column from sample values.

    Analyzes a sample of column values and determines the most likely type.
    Type detection prioritizes in this order: numeric, money, date, code, alpha.

    Args:
        sample_values: List of sample values (typically first 10K non-NULL)
        threshold: Confidence threshold for type detection (0.0-1.0).
                  Default 0.9 means 90% of values must match the pattern.

    Returns:
        ColumnType enum value (NUMERIC, MONEY, DATE, CODE, ALPHA, UNKNOWN)

    Raises:
        ValueError: If threshold not in range [0.0, 1.0]
        TypeError: If sample_values contains non-string items

    Examples:
        Type inference for numeric column:

        >>> values = ["100", "200.50", "150"]
        >>> inferred_type = infer_column_type(values)
        >>> assert inferred_type == ColumnType.NUMERIC

        Type inference with lower threshold:

        >>> mixed_values = ["100", "200", "N/A"]
        >>> inferred_type = infer_column_type(mixed_values, threshold=0.8)
        >>> # Still detects NUMERIC if 80%+ are numeric

    Note:
        - NULL values (empty strings, "NULL", etc.) are ignored in detection
        - Types are prioritized, not scored equally
        - Use lower threshold for data with known quality issues

    See Also:
        - TYPE_INFERENCE.md: Detailed type detection algorithm
        - ColumnProfiler.finalize(): Full profiling workflow
    """
    # Implementation...
```

### Type Hints

Use comprehensive type hints:

```python
from typing import List, Dict, Optional, Tuple, Union, Callable
from enum import Enum

class ColumnType(Enum):
    """Enumeration of supported column types."""
    NUMERIC = "numeric"
    MONEY = "money"
    DATE = "date"
    ALPHA = "alpha"
    CODE = "code"
    UNKNOWN = "unknown"


def process_file(
    file_path: str,
    delimiter: str = "|",
    encoding: str = "utf-8"
) -> Tuple[int, List[str], Optional[Exception]]:
    """
    Process CSV file and return results.

    Args:
        file_path: Path to CSV file
        delimiter: Column delimiter
        encoding: File encoding (default UTF-8)

    Returns:
        Tuple of (rows_processed, headers, error)
        - rows_processed: Number of rows successfully processed
        - headers: List of column names from header row
        - error: Exception if processing failed, None otherwise
    """


def create_index_for_column(
    values: List[str],
    column_name: str
) -> Dict[str, int]:
    """
    Create an index of distinct values.

    Args:
        values: Column values
        column_name: Name for logging/debugging

    Returns:
        Dictionary mapping values to occurrence counts
    """
    # Implementation...
```

### Inline Comments

Add comments for complex logic:

```python
def calculate_quantiles(values: List[float]) -> Dict[str, float]:
    """Calculate exact quantiles using sorted values."""
    sorted_values = sorted(values)
    n = len(sorted_values)

    # Use linear interpolation for quantile calculation
    # This is more accurate than simple indexing
    def quantile(p: float) -> float:
        """Calculate p-th percentile (0-100)."""
        position = (p / 100) * (n - 1)
        lower_idx = int(position)
        upper_idx = min(lower_idx + 1, n - 1)
        fraction = position - lower_idx

        # Linear interpolation between values
        return (
            sorted_values[lower_idx] * (1 - fraction) +
            sorted_values[upper_idx] * fraction
        )

    return {
        "p1": quantile(1),
        "p5": quantile(5),
        "p25": quantile(25),
        "p50": quantile(50),  # Median
        "p75": quantile(75),
        "p95": quantile(95),
        "p99": quantile(99),
    }
```

### Error Handling Documentation

Document exceptions clearly:

```python
def validate_utf8_bytes(data: bytes) -> Tuple[bool, Optional[int]]:
    """
    Validate that data is valid UTF-8.

    Args:
        data: Bytes to validate

    Returns:
        Tuple of (is_valid, error_offset)
        - is_valid: True if all bytes are valid UTF-8
        - error_offset: Byte offset of first invalid sequence, or None

    Raises:
        TypeError: If data is not bytes
        ValueError: If data is empty

    Examples:
        Valid UTF-8:

        >>> is_valid, offset = validate_utf8_bytes(b"Hello")
        >>> assert is_valid and offset is None

        Invalid UTF-8:

        >>> is_valid, offset = validate_utf8_bytes(b"\\x80\\x81")
        >>> assert not is_valid and offset == 0

    Error Codes:
        - UTF8_E_001: Invalid continuation byte at {offset}
        - UTF8_E_002: Incomplete sequence at {offset}
    """
    # Implementation...
```

## TypeScript Code Documentation

### Component Docstrings

Document React components with JSDoc:

```typescript
/**
 * Upload form component for selecting and submitting files.
 *
 * Allows users to select a CSV/TXT file, configure parsing options
 * (delimiter, quoting, line endings), and submit for profiling.
 *
 * @component
 * @example
 * ```tsx
 * <UploadForm onSubmit={(runId) => navigate(`/run/${runId}`)} />
 * ```
 *
 * @props {UploadFormProps} props - Component properties
 * @returns {JSX.Element} Form UI
 *
 * @fires onSubmit - Emitted when form is submitted with file
 * @fires onError - Emitted when validation fails
 *
 * @see {@link RunStatus} for status display after upload
 * @see {@link API.md} for endpoint details
 */
export function UploadForm({ onSubmit, onError }: UploadFormProps): JSX.Element {
  // Implementation...
}
```

### Function Docstrings

Document utility functions:

```typescript
/**
 * Format a timestamp as human-readable date with timezone.
 *
 * Converts server UTC timestamp to user's local timezone and
 * formats with month name and timezone abbreviation.
 *
 * @param timestamp - ISO 8601 timestamp string or number (milliseconds)
 * @param options - Formatting options
 * @returns Formatted date string (e.g., "Jan 15, 2:30 PM PST")
 *
 * @example
 * ```ts
 * const formatted = formatDateTime("2024-01-15T14:30:00Z");
 * // => "Jan 15, 2:30 PM PST" (in PST timezone)
 * ```
 *
 * @throws {InvalidDateError} If timestamp cannot be parsed
 *
 * @see [MDN: Date.toLocaleString](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/toLocaleString)
 */
function formatDateTime(
    timestamp: string | number,
    options?: FormatOptions
): string {
  // Implementation...
}
```

### Type Definitions

Document interfaces and types:

```typescript
/**
 * API response for column profiling results.
 *
 * Contains all statistics and metrics for a single column,
 * including type inference, distributions, and validation results.
 *
 * @property name - Column name from header row
 * @property inferred_type - Auto-detected type (see ColumnType)
 * @property null_pct - Percentage of NULL/empty values (0-100)
 * @property distinct_count - Number of unique values
 * @property statistics - Type-specific statistics object
 *
 * @example
 * ```ts
 * const column: ColumnProfile = {
 *   name: "amount",
 *   inferred_type: "money",
 *   null_pct: 0.5,
 *   distinct_count: 50000,
 *   statistics: { min: 0.01, max: 9999.99, mean: 245.67 }
 * };
 * ```
 *
 * @see {@link ColumnType} for valid type values
 * @see {@link API.md} for API response schema
 */
interface ColumnProfile {
  name: string;
  inferred_type: ColumnType;
  null_pct: number;
  distinct_count: number;
  statistics?: Record<string, unknown>;
}
```

## Documentation Comments vs Code Comments

### When to Use Comments

**Good comments - explain WHY:**

```python
# Use min-heap for top-10 to avoid sorting entire dataset
# This reduces memory from O(n) to O(10) and time from O(n log n) to O(n log 10)
top_values = heapq.nsmallest(10, values, key=lambda x: x[1])
```

**Poor comments - repeat the code:**

```python
# Loop through values
for value in values:
    # Append to list
    result.append(value)
```

### When to Use Docstrings

- Every module, class, function, and method
- Explain what the code does (WHAT, not how)
- Include examples for complex logic
- Document exceptions and edge cases
- Link to related documentation

## Error Code Documentation

Document error codes in docstrings:

```python
def validate_numeric_field(value: str) -> bool:
    """
    Validate that value is numeric format.

    Args:
        value: String value to validate

    Returns:
        True if valid numeric format, False otherwise

    Error Codes:
        - E_NUMERIC_FORMAT: Value doesn't match ^[0-9]+(\\.[0-9]+)?$
        - E_NUMERIC_OVERFLOW: Value too large to represent

    Examples:
        >>> validate_numeric_field("100")
        True
        >>> validate_numeric_field("$100")
        False  # E_NUMERIC_FORMAT
    """
    # Implementation...
```

## API Documentation

### Endpoint Documentation

```python
@router.get("/runs/{run_id}/profile")
async def get_profile(run_id: str) -> Profile:
    """
    Get complete profiling results for a run.

    Retrieves the full profile JSON including file metadata, column
    statistics, error roll-ups, and candidate key suggestions.

    Path Parameters:
        run_id (str): UUID of the profiling run

    Response:
        Profile: Complete profile object (see API.md for schema)

    Status Codes:
        200 OK - Profile retrieved successfully
        202 Accepted - Profile still being computed (retry after 1 second)
        404 Not Found - Run not found (check run_id)
        500 Server Error - Profile generation failed (see error message)

    Examples:
        Successful request:

            GET /runs/550e8400-e29b-41d4-a716-446655440000/profile
            HTTP/1.1 200 OK
            Content-Type: application/json

            {
              "run_id": "550e8400-e29b-41d4-a716-446655440000",
              "file": { ... },
              "columns": [ ... ]
            }

        Still processing:

            GET /runs/550e8400-e29b-41d4-a716-446655440000/profile
            HTTP/1.1 202 Accepted

            Retry-After: 1

    See Also:
        - POST /runs: Create a run
        - POST /runs/{run_id}/upload: Upload file
        - GET /runs/{run_id}/status: Check progress
        - /docs: Full API documentation
    """
    # Implementation...
```

### Request/Response Models

Document Pydantic models:

```python
class ColumnProfile(BaseModel):
    """
    Profiling results for a single column.

    Attributes:
        name (str): Column name from CSV header
        inferred_type (ColumnType): Detected type
        null_pct (float): Percentage of NULL values (0-100)
        distinct_count (int): Number of unique values
        length (LengthStats, optional): String length stats
        numeric_stats (NumericStats, optional): Stats if numeric type
        top_values (List[ValueFreq]): Top 10 most common values

    Examples:
        Numeric column profile:

        >>> profile = {
        ...     "name": "amount",
        ...     "inferred_type": "numeric",
        ...     "null_pct": 0.0,
        ...     "distinct_count": 50000,
        ...     "numeric_stats": {
        ...         "min": 0.01,
        ...         "max": 9999.99,
        ...         "mean": 245.67
        ...     }
        ... }

    Validation:
        - null_pct must be 0-100
        - distinct_count must be >= 0
        - distinct_count must be <= total rows

    See Also:
        - TYPE_INFERENCE.md: How types are detected
        - API.md: Full schema definition
    """
    name: str
    inferred_type: ColumnType
    null_pct: float
    distinct_count: int
    length: Optional[LengthStats] = None
    numeric_stats: Optional[NumericStats] = None
    top_values: List[ValueFreq] = []

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "name": "transaction_id",
                "inferred_type": "code",
                "null_pct": 0.0,
                "distinct_count": 1000000,
                "top_values": [
                    {"value": "TXN00001", "count": 1},
                    {"value": "TXN00002", "count": 1}
                ]
            }
        }
```

## Documentation Standards Checklist

### Before Committing

- [ ] All modules have docstrings
- [ ] All classes have docstrings
- [ ] All public functions have docstrings
- [ ] All type hints are present
- [ ] Complex logic has inline comments
- [ ] Error codes are documented
- [ ] Examples are provided for complex functionality
- [ ] Related documentation links are included
- [ ] API endpoints are documented in code
- [ ] No generic comments like "TODO" or "FIXME" without context

### Documentation Coverage

Aim for:
- 100% of modules documented
- 100% of classes documented
- 100% of public functions documented
- 90% of complex functions have examples

### Automated Documentation Generation

Generate API docs from docstrings:

```bash
cd api

# Generate OpenAPI schema
python -c "from app import app; import json; print(json.dumps(app.openapi()))"

# Generate Markdown from docstrings
pip install pydoc-markdown
pydoc-markdown api/ > API_GENERATED.md
```

## Tools and Integration

### Pre-commit Hooks

Validate documentation:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/PyCQA/pydocstyle
    rev: 6.3.0
    hooks:
      - id: pydocstyle
        args: ["api/"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
```

### IDE Configuration

VSCode settings for documentation:

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

## See Also

- README.md: Project overview
- API.md: API endpoint documentation
- DEVELOPMENT.md: Development setup and testing
- TYPE_INFERENCE.md: Type validation documentation
- ERROR_CODES.md: Error code reference
