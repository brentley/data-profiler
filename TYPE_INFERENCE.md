# Type Inference and Validation Rules

Detailed specification for column type detection, validation rules, and edge cases.

## Type System Overview

Each column is assigned exactly one type during profiling:

1. **alpha** - General text strings
2. **varchar** - Text with variable length
3. **code** - Code-like identifiers (alphanumeric, often fixed format)
4. **numeric** - Numbers with optional decimals
5. **money** - Currency values (exactly 2 decimals)
6. **date** - Date values in consistent format
7. **mixed** - Multiple types detected (error condition)
8. **unknown** - Cannot determine type (error condition)

## Type Detection Algorithm

### Phase 1: Sample Analysis (First 10,000 Non-NULL Values)

For each column, analyze first 10,000 non-NULL values:

```
1. Collect sample values
2. Test each value against type patterns (in order)
3. Count matches per type
4. Calculate confidence score for each type
5. Select primary type if confidence > 90%
```

### Phase 2: Full Pass Validation

Validate all values against detected type:

```
1. Iterate through remaining values
2. Check each value against primary type pattern
3. Count violations
4. If violations > 5% of values:
     - Flag as MIXED type (if multiple types detected)
     - Flag violations as errors
5. Generate per-type statistics
```

### Phase 3: Type-Specific Validation

Apply type-specific rules:

```
1. Numeric: Calculate statistics, check for outliers
2. Money: Validate decimal places, check for symbols
3. Date: Detect format, check range, count inconsistencies
4. String types: Collect length stats, top values, character sets
```

## Type Detection Patterns

### Numeric Type

**Pattern**: `^[0-9]+(\.[0-9]+)?$`

**Valid Examples**:
- `100`
- `100.50`
- `0`
- `0.0`
- `999999.99`

**Invalid Examples**:
- `100.50.25` (multiple decimals)
- `1,000.00` (thousands separator)
- `$100.00` (currency symbol)
- `1.23e5` (scientific notation)
- `(100)` (negative indicator)
- `+100` (sign)

**Detection Rules**:
1. Check pattern match
2. Parse as float (check for overflow)
3. Ensure exactly one decimal point if present

**Statistics Generated**:
- min, max, mean, median
- Standard deviation
- Quantiles: p1, p5, p25, p50, p75, p95, p99
- Histogram with automatic binning
- Gaussian test (D'Agostino-Pearson)

**Error Handling**:
- Non-matching values: `E_NUMERIC_FORMAT` error
- Excluded from statistics
- Not counted in distinct values

### Money Type

**Pattern**: `^\d+\.\d{2}$`

**Valid Examples**:
- `100.00`
- `0.01`
- `9999.99`
- `10000.00`

**Invalid Examples**:
- `100` (missing decimals)
- `100.5` (only 1 decimal)
- `100.123` (too many decimals)
- `$100.00` (currency symbol)
- `100,00` (comma as decimal separator)
- `-100.00` (negative sign)
- `(100.00)` (accounting negative)
- `1,000.00` (thousands separator)

**Detection Rules**:
1. Check exact pattern match
2. Ensure no currency symbols: `$`, `€`, `£`, etc.
3. Ensure no thousands separators: `,`
4. Ensure no parentheses: `(`, `)`
5. Ensure no signs: `+`, `-`

**Statistics Generated**:
- Same as numeric (min, max, mean, median, stddev, quantiles, histogram)
- Plus validation flags:
  - `two_decimal_ok`: All values have exactly 2 decimals
  - `disallowed_symbols_found`: Any $ or , detected
  - `violations_count`: Number of values not matching pattern

**Error Handling**:
- Non-matching values: `E_MONEY_FORMAT` error
- Non-matching values excluded from statistics
- Violations counted and reported

### Date Type

**Supported Formats** (detected in order of preference):

1. `YYYYMMDD` - Most preferred (compact, sortable)
2. `YYYY-MM-DD` - ISO 8601
3. `YYYY/MM/DD` - Alternative slash format
4. `MM/DD/YYYY` - US format
5. `DD/MM/YYYY` - EU format
6. `YYYY.MM.DD` - Dot format
7. `DDMMYYYY` - Compact format
8. Custom formats - One format per column enforced

**Format Detection Rules**:

```python
def detect_date_format(sample_values):
    """
    1. For each value in sample:
       - Try to parse with each known format
       - Record successful parses
    2. Find most common successful format
    3. Return that format (if > 80% of values parse)
    """
```

**Valid Examples** (for YYYYMMDD):
- `20240115`
- `20000101`
- `19990531`

**Invalid Examples**:
- `2024-1-15` (missing zero-padding)
- `2024-13-01` (invalid month)
- `2024-02-30` (invalid day)
- `1850-01-01` (year < 1900)
- `2050-12-31` (year > current + 1)

**Null Handling**:
- Empty string: Treated as NULL
- `null`, `NULL`, `Null`: Treated as NULL
- Space-only: Treated as NULL

**Detection Rules**:
1. Parse with detected format
2. Validate date is valid (correct month/day for year)
3. Check year in range [1900, current_year + 1]
4. If multiple formats detected: Flag as `E_DATE_MIXED_FORMAT`

**Statistics Generated**:
- Detected format (string)
- Min date (earliest value)
- Max date (latest value)
- Out-of-range count
- Distribution by year (count per year)
- Distribution by month (count per month)
- Format consistency check

**Error Handling**:
- Invalid date: `E_DATE_INVALID` error, treated as NULL
- Mixed formats: `E_DATE_MIXED_FORMAT` error, primary format used
- Out of range: `W_DATE_RANGE` warning, still counted

### String Types (Alpha, Varchar, Code)

**Alpha Type**:
- Any alphabetic characters (a-z, A-Z)
- May include spaces
- Pattern: `^[a-zA-Z\s]+$`

**Varchar Type**:
- Any characters (generic string)
- Fallback when specific pattern not detected

**Code Type**:
- Alphanumeric with possible fixed structure
- Pattern: `^[a-zA-Z0-9_\-]+$`
- Detection: Used for fields like IDs, codes, identifiers

**Detection Rules**:
1. If all values match `^[a-zA-Z]+$`: Type = `alpha`
2. If all values match `^[a-zA-Z0-9_\-]+$`: Type = `code`
3. Otherwise: Type = `varchar`

**Statistics Generated**:
- Length: min, max, average
- Top 10 values with counts
- Character set notes:
  - Contains ASCII only or non-ASCII
  - Character type mix (digits, letters, symbols)

**Special Cases**:

| Pattern | Type | Example |
|---------|------|---------|
| `^[a-zA-Z0-9]{8}$` | code | `ABC12345` |
| `^[A-Z]{2}[0-9]{4}$` | code | `AB1234` |
| `^[0-9]{3}-[0-9]{2}-[0-9]{4}$` | code | `123-45-6789` |

**NULL/Empty Handling**:
- Empty string: Counted as NULL
- Whitespace only: Counted as NULL
- Tracked in `null_pct`

## NULL Handling

### NULL Detection

Values treated as NULL:
- Empty string: `""`
- Whitespace only: `"   "`
- Explicit null markers (configurable):
  - `null`, `NULL`, `Null`
  - `none`, `NONE`, `None`
  - `N/A`, `n/a`
  - `NA`
  - `-` (single dash)

### NULL Metrics

For each column:
- `null_count`: Number of NULL values
- `nonnull_count`: Number of non-NULL values
- `null_pct`: `null_count / total_count * 100`
- `null_distinct_ratio`: `distinct_count / nonnull_count`

### NULL Impact

- **Numeric Stats**: NULLs excluded from min/max/mean/stddev
- **Distinct Count**: NULLs counted separately (not in distinct_count)
- **Top Values**: NULLs excluded from top-10 calculation
- **Date Range**: NULLs allowed and excluded from range checks
- **Keys**: NULLs affect key quality score

## Type Validation Examples

### Example 1: Well-Typed Numeric Column

Input values:
```
100
150.50
200
250.75
300
```

Process:
1. All values match numeric pattern
2. Type detected: `numeric`
3. Statistics: min=100, max=300, mean=200.25, stddev=79.1
4. Errors: None

### Example 2: Mixed Type Column (Error)

Input values:
```
100
150.50
N/A
200
300
```

Process:
1. Sample contains both numeric (100, 150.50, 200, 300) and NULL (N/A)
2. Non-NULL values are all numeric
3. NULL values represent ~20% of sample
4. Type detected: `numeric`
5. Metrics: null_count=1, null_pct=20, valid statistics from 4 values
6. Errors: None (NULLs are allowed)

### Example 3: Money Column with Violations

Input values:
```
100.00
150.50
$200.00
250,00
300.0
```

Process:
1. Expected pattern: `^\d+\.\d{2}$`
2. Valid matches: 100.00, 150.50
3. Invalid: $200.00 (symbol), 250,00 (comma separator), 300.0 (1 decimal)
4. Type detected: `money` (based on majority)
5. Statistics: Generated from valid values only
6. Errors: E_MONEY_FORMAT (3 violations)

### Example 4: Date Column with Mixed Formats

Input values:
```
2024-01-15
2024/01/15
01-15-2024
2024-01-15
2024-01-16
```

Process:
1. Detect formats:
   - 2024-01-15: YYYY-MM-DD (2 occurrences)
   - 2024/01/15: YYYY/MM/DD (1 occurrence)
   - 01-15-2024: MM-DD-YYYY (1 occurrence)
2. Primary format: YYYY-MM-DD (40% match rate, below 80% threshold)
3. Type detected: `date`
4. Error: E_DATE_MIXED_FORMAT
5. Stats: min=2024-01-15, max=2024-01-16, format=YYYY-MM-DD

## Edge Cases

### Very Short Columns (Few Distinct Values)

If column has < 5 distinct values:
1. Still apply type detection
2. Mark as potential enumeration/categorical
3. Type inference works normally

### All NULL Columns

If column is all NULL:
1. Type: `unknown`
2. Statistics: All NULL
3. Null %: 100%
4. Error: None (allowed)

### Empty Values vs Explicit Null

Empty string `""` vs null marker `null`:

```
Column | null_count | Explanation
--------|------------|------------
""      | 1          | Treated as NULL
null    | 1          | Treated as NULL
"null"  | 0          | Treated as string (quoted)
" "     | 1          | Whitespace = NULL
"NULL"  | 0          | Case-sensitive; treated as string if unquoted
```

### Special Numeric Cases

| Value | Type | Notes |
|-------|------|-------|
| `0` | numeric | Valid zero |
| `0.0` | numeric | Valid zero |
| `0.00` | numeric | Valid zero (but money format) |
| `.5` | Invalid | Must have leading digit |
| `5.` | Invalid | Must have decimal digits |
| `+5` | Invalid | No signs allowed |
| `-5` | Invalid | No signs allowed |

### Special Date Cases

| Value | Format | Valid | Notes |
|-------|--------|-------|-------|
| `2024-02-29` | YYYY-MM-DD | Yes | Leap year |
| `2023-02-29` | YYYY-MM-DD | No | Not leap year |
| `2024-01-01` | YYYY-MM-DD | Yes | New year |
| `2024-12-31` | YYYY-MM-DD | Yes | End of year |
| `1899-12-31` | YYYY-MM-DD | No | Before 1900 |

## Type Inference Algorithm (Python-Like Pseudocode)

```python
def infer_column_type(column_values: List[str], sample_size: int = 10000) -> Tuple[Type, float]:
    """
    Infer column type from sample.

    Returns: (detected_type, confidence_score)
    """

    # Phase 1: Sample analysis
    sample = [v for v in column_values[:sample_size] if v is not null]

    if len(sample) == 0:
        return "unknown", 0.0

    type_scores = {
        "numeric": 0,
        "money": 0,
        "date": 0,
        "alpha": 0,
        "code": 0,
        "varchar": 0
    }

    for value in sample:
        if matches_numeric_pattern(value):
            type_scores["numeric"] += 1
        if matches_money_pattern(value):
            type_scores["money"] += 1
        if matches_date_pattern(value):
            type_scores["date"] += 1
        if matches_alpha_pattern(value):
            type_scores["alpha"] += 1
        if matches_code_pattern(value):
            type_scores["code"] += 1
        type_scores["varchar"] += 1  # Fallback

    # Normalize scores
    total = len(sample)
    scores = {k: v/total for k, v in type_scores.items()}

    # Determine primary type by priority
    # Priority: numeric > money > date > code > alpha > varchar
    priorities = ["numeric", "money", "date", "code", "alpha", "varchar"]

    for type_name in priorities:
        if scores[type_name] > 0.9:
            confidence = scores[type_name]
            return type_name, confidence

    # If no type > 90%, use highest scoring
    best_type = max(scores, key=scores.get)
    confidence = scores[best_type]

    if confidence < 0.5:
        return "unknown", confidence

    return best_type, confidence


def validate_all_values(column_values: List[str], detected_type: str) -> Tuple[int, List[Error]]:
    """
    Validate all values against detected type.

    Returns: (error_count, error_list)
    """
    errors = []
    error_count = 0

    for idx, value in enumerate(column_values):
        if is_null(value):
            continue

        if not validates_as_type(value, detected_type):
            error_count += 1
            errors.append({
                "row": idx + 2,  # +1 for header, +1 for 1-based indexing
                "value": value,
                "expected_type": detected_type,
                "error_code": get_error_code(detected_type)
            })

    # If error_count > 5% of values, type might be MIXED
    error_pct = error_count / len([v for v in column_values if not is_null(v)])
    if error_pct > 0.05 and error_count > 0:
        return error_count, errors

    return error_count, errors
```

## Type System Limitations

### Known Limitations in v1

1. **Single Type Per Column** - No support for nullable typed unions
2. **No Custom Types** - Cannot define application-specific types
3. **Basic Date Formats** - Limited to common formats; custom formats via schema hint (v2)
4. **No Enum Detection** - Categorical/enumeration not auto-detected
5. **No Geographic Types** - No special handling for lat/long, addresses, etc.

### Future Enhancements (v2+)

1. Support schema hints for pre-declared types
2. Automatic enum/categorical detection
3. More date formats and timezone handling
4. IP address and URL types
5. JSON and array types
6. Custom regex type validation

## Testing Type Inference

### Test Cases for Numeric Type

```python
# Valid
assert infer_type("100") == "numeric"
assert infer_type("0") == "numeric"
assert infer_type("0.0") == "numeric"
assert infer_type("999999.99") == "numeric"

# Invalid
assert infer_type("100.50.25") != "numeric"  # Multiple decimals
assert infer_type("$100.00") != "numeric"    # Currency
assert infer_type("1,000") != "numeric"      # Separator
```

### Test Cases for Money Type

```python
# Valid
assert infer_type("100.00") == "money"
assert infer_type("0.01") == "money"

# Invalid
assert infer_type("100") != "money"          # Missing decimals
assert infer_type("100.5") != "money"        # Wrong decimals
assert infer_type("$100.00") != "money"      # Symbol
```

### Test Cases for Date Type

```python
# Valid
assert infer_type("2024-01-15") == "date"
assert infer_type("20240115") == "date"

# Invalid
assert infer_type("2024-13-01") != "date"    # Invalid month
assert infer_type("2024-02-30") != "date"    # Invalid day
assert infer_type("1850-01-01") != "date"    # Before 1900
```

## Documentation

See `API.md` for how type information is included in API responses.

See `ERROR_CODES.md` for type-related error codes.

See `DEVELOPMENT.md` for implementing custom type validators.
