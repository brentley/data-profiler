# Error Codes Reference

Complete reference for all error and warning codes generated during profiling operations.

## Error Categories

### Catastrophic Errors (Processing Stops)

Catastrophic errors halt processing immediately. The run state becomes `failed` and no further analysis occurs.

#### UTF-8 Encoding Errors

**E_UTF8_INVALID**

- **Severity**: Catastrophic
- **Message**: `Invalid UTF-8 sequence at byte offset {offset}`
- **Description**: File contains invalid UTF-8 byte sequences
- **Action**: Re-encode file to UTF-8 (UTF-8 BOM is accepted but not required)
- **Example**: Binary data or mis-encoded file uploaded
- **User Guidance**: "This file appears to be corrupted or not properly UTF-8 encoded. Please verify the file encoding and try again."

**E_UTF8_INVALID_BOM**

- **Severity**: Non-catastrophic (v1)
- **Message**: `UTF-8 BOM detected; continuing with processing`
- **Description**: File starts with UTF-8 Byte Order Mark
- **Action**: BOM is stripped and processing continues
- **User Guidance**: None required; handled automatically

### Header Validation Errors

**E_HEADER_MISSING**

- **Severity**: Catastrophic
- **Message**: `First row appears to be data, not headers`
- **Description**: File has no header row or header is missing
- **Action**: Add header row as first line of file
- **Example**: CSV file starts directly with data
- **User Guidance**: "CSV files must have a header row as the first line. Add column names as the first row and try again."

**E_HEADER_EMPTY**

- **Severity**: Catastrophic
- **Message**: `Header row contains no columns`
- **Description**: Header exists but contains no valid column names
- **Action**: Add at least one column name to header
- **User Guidance**: "Header row is empty. Please add column names."

**E_HEADER_DUPLICATE**

- **Severity**: Non-catastrophic
- **Message**: `Duplicate column name: {column_name}`
- **Count**: Number of duplicate occurrences
- **Description**: Multiple columns share the same name
- **Action**: Column is included with duplicate detection noted; may affect key suggestions
- **User Guidance**: "Some column names are duplicated. This may affect key suggestions."

### Row Structure Errors

**E_JAGGED_ROW**

- **Severity**: Catastrophic
- **Message**: `Row {row_number} has {actual_count} columns, expected {expected_count}`
- **Description**: Row has inconsistent column count
- **Action**: Processing stops; row that causes inconsistency is identified
- **Location**: Specific row number and column count mismatch provided
- **User Guidance**: "File has inconsistent rows - some have more or fewer columns than the header. Check row {row_number} for extra/missing delimiters."

**E_ROW_EMPTY**

- **Severity**: Non-catastrophic
- **Message**: `Empty row detected at line {line_number}`
- **Count**: Number of empty rows
- **Description**: Row contains only whitespace or is completely empty
- **Action**: Row is skipped; not counted in row total
- **User Guidance**: None required; empty rows are filtered automatically

### Quoting and Delimiter Errors

**E_QUOTE_RULE_VIOLATION**

- **Severity**: Non-catastrophic
- **Message**: `Quoting rules violated in row {row_number}`
- **Count**: Number of violations
- **Description**: CSV quoting rules not followed (e.g., unescaped inner quotes)
- **Details**:
  - Inner double quotes not doubled (`"` instead of `""`)
  - Unbalanced quotes in field
  - Quote character mid-field without field being quoted
- **Action**: Field value is recorded as-is; error counted but processing continues
- **User Guidance**: "Some fields have quoting issues. Values are recorded as-is. Check fields with embedded quotes."

**E_UNQUOTED_DELIMITER**

- **Severity**: Non-catastrophic
- **Message**: `Unquoted embedded delimiter in row {row_number}`
- **Count**: Number of occurrences
- **Description**: Delimiter character appears in field value without the field being quoted
- **Example**: Field value contains `|` but field isn't quoted
- **Action**: Entire field is skipped/treated as NULL; error counted
- **User Guidance**: "Some fields appear to contain unquoted delimiters. These fields may be parsed incorrectly. Consider re-exporting with proper quoting."

**E_UNQUOTED_NEWLINE**

- **Severity**: Non-catastrophic
- **Message**: `Unquoted embedded newline in row {row_number}`
- **Count**: Number of occurrences
- **Description**: Newline appears within field without field being quoted
- **Action**: Processing handles according to line ending rules; error counted
- **User Guidance**: "Some fields contain unquoted line breaks. Ensure these fields are quoted."

### Type Validation Errors

**E_NUMERIC_FORMAT**

- **Severity**: Non-catastrophic
- **Message**: `Non-numeric value in numeric column: {sample_value}`
- **Count**: Number of violations
- **Column**: Name of numeric column
- **Description**: Value doesn't match numeric pattern `^[0-9]+(\.[0-9]+)?$`
- **Invalid Patterns**:
  - Currency symbols: `$100`, `€50.00`
  - Thousands separators: `1,000`, `1.000` (when dot is separator)
  - Scientific notation: `1e5`, `1.23E+10`
  - Parentheses for negatives: `(100)`
  - Multiple decimals: `1.2.3`
- **Action**: Value excluded from numeric statistics; counted as invalid
- **User Guidance**: "Some numeric columns contain non-numeric values. These values are excluded from statistics."

**E_MONEY_FORMAT**

- **Severity**: Non-catastrophic
- **Message**: `Invalid money format: {sample_value}`
- **Count**: Number of violations
- **Column**: Name of money column
- **Description**: Value doesn't match money rules (exactly 2 decimals, no symbols)
- **Invalid Patterns**:
  - Wrong decimal count: `100`, `100.1`, `100.123`
  - Currency symbols: `$100.00`, `€100.00`
  - Thousands separators: `1,000.00`
  - Parentheses: `(100.00)`
  - Negative signs: `-100.00`
- **Valid Pattern**: `^\d+\.\d{2}$` (e.g., `100.00`, `0.01`, `9999.99`)
- **Action**: Value excluded from money statistics; counted as invalid
- **User Guidance**: "Some money columns have improper formatting. Use format: `XXX.XX` (e.g., `100.00`) without currency symbols."

**E_MIXED_TYPE**

- **Severity**: Non-catastrophic
- **Message**: `Mixed types detected in column: {column_name}`
- **Count**: Number of different types detected
- **Types Found**: List of detected types
- **Description**: Column contains values of multiple detected types
- **Example**: Column contains both numeric values (`100`) and text values (`N/A`)
- **Action**: Column typed as `mixed`; statistics not computed
- **User Guidance**: "This column contains mixed data types. Ensure all values in a column are the same type."

**E_TYPE_UNKNOWN**

- **Severity**: Non-catastrophic
- **Message**: `Unable to determine column type: {column_name}`
- **Count**: Number of columns affected
- **Description**: Type inference couldn't determine a consistent type
- **Possible Causes**:
  - All values are NULL
  - Values don't match any known pattern
  - Insufficient non-NULL sample
- **Action**: Column typed as `unknown`; no statistics generated
- **User Guidance**: "Unable to determine the type for this column. Ensure it contains consistent values."

### Date Validation Errors

**E_DATE_MIXED_FORMAT**

- **Severity**: Non-catastrophic
- **Message**: `Multiple date formats detected: {format1}, {format2}`
- **Count**: Number of inconsistent formats
- **Column**: Name of date column
- **Description**: Date column uses inconsistent formats
- **Example**: Column contains both `2024-01-15` and `01/15/2024`
- **Action**: Column marked with primary detected format; other formats counted as errors
- **User Guidance**: "Date column contains mixed formats. Standardize all dates to one format (prefer YYYYMMDD)."

**W_DATE_RANGE**

- **Severity**: Warning (non-catastrophic)
- **Message**: `Date out of expected range`
- **Count**: Number of out-of-range dates
- **Column**: Name of date column
- **Description**: Date value is outside reasonable range
- **Range Rules**:
  - Year >= 1900
  - Year <= current year + 1
  - Day in valid range for month/year
- **Example**: Date of `1850-01-01` or `2050-12-31` (if current year is 2024)
- **Action**: Date is processed; warning counted
- **User Guidance**: "Some dates are outside the typical range. Verify these dates are correct."

**E_DATE_INVALID**

- **Severity**: Non-catastrophic
- **Message**: `Invalid date: {sample_value}`
- **Count**: Number of invalid dates
- **Column**: Name of date column
- **Description**: Value doesn't parse as a date in detected format
- **Example**: `2024-02-30` (invalid day), `2024-13-01` (invalid month)
- **Action**: Value treated as NULL; error counted
- **User Guidance**: "Some date values are invalid. Check for typos or invalid day/month combinations."

### Line Ending Issues

**W_LINE_ENDING_INCONSISTENT**

- **Severity**: Warning (non-catastrophic)
- **Message**: `Inconsistent line endings detected`
- **Count**: Number of inconsistent line endings found
- **Description**: File mixes different line ending styles (CRLF, LF, CR)
- **Action**: Normalized internally; original style noted in profile
- **User Guidance**: None required; handled automatically

**W_LINE_ENDING_UNEXPECTED**

- **Severity**: Warning (non-catastrophic)
- **Message**: `Expected {expected_ending} but found {actual_ending}`
- **Description**: File uses different line endings than specified/expected
- **Expected**: CRLF (Windows) or LF (Unix)
- **Action**: Normalized to internal standard; processing continues
- **User Guidance**: "File uses different line endings than expected but will be processed normally."

### Key and Uniqueness Errors

**E_KEY_INVALID**

- **Severity**: Non-catastrophic
- **Message**: `Column in key suggestion does not exist: {column_name}`
- **Description**: Suggested key references non-existent column
- **Action**: Key suggestion is removed
- **User Guidance**: "A suggested key includes a column that doesn't exist. This suggestion has been removed."

**W_KEY_LOW_CARDINALITY**

- **Severity**: Warning (non-catastrophic)
- **Message**: `Suggested key has low distinctness: {score}`
- **Score**: Distinct ratio * (1 - null ratio)
- **Description**: Key has duplicates or many NULL values
- **Action**: Key still suggested but marked with low score
- **User Guidance**: "This suggested key has low distinctness and may not uniquely identify rows."

**W_DUPLICATE_FOUND**

- **Severity**: Warning (non-catastrophic)
- **Message**: `{count} duplicate values found for key: {key_columns}`
- **Count**: Number of duplicate occurrences
- **Description**: Confirmed key has duplicate values
- **Action**: Duplicates are counted and reported; processing continues
- **User Guidance**: "This key has {count} duplicate values. Data quality issue detected."

### Processing and Resource Errors

**E_PROCESSING_FAILED**

- **Severity**: Catastrophic
- **Message**: `Processing failed: {error_detail}`
- **Description**: Unexpected error during processing
- **Details**: Specific error context
- **Action**: Run state becomes `failed`
- **User Guidance**: "Processing failed with an internal error. Check logs for details."

**W_SPILL_DIRECTORY_FULL**

- **Severity**: Warning (may become catastrophic)
- **Message**: `Spill directory approaching capacity: {used_pct}%`
- **Percentage**: Current usage of spill directory
- **Action**: Processing continues; further processing may fail if capacity reached
- **User Guidance**: "Disk space is running low. Processing may fail if spill space runs out."

**E_SPILL_DIRECTORY_FULL**

- **Severity**: Catastrophic
- **Message**: `Spill directory full: cannot continue processing`
- **Action**: Run state becomes `failed`
- **User Guidance**: "Disk space has run out. Free up disk space and try again."

**E_FILE_ENCODING_ISSUE**

- **Severity**: Catastrophic
- **Message**: `File encoding issue: expected UTF-8`
- **Description**: File is not UTF-8 encoded
- **Action**: Processing stops
- **User Guidance**: "File is not UTF-8 encoded. Convert the file to UTF-8 and try again."

### Configuration and Setup Errors

**E_INVALID_DELIMITER**

- **Severity**: Non-catastrophic (caught at run creation)
- **Message**: `Invalid delimiter: {delimiter}`
- **Valid Values**: `|` (pipe) or `,` (comma)
- **Action**: Request rejected with 400 status
- **User Guidance**: "Only pipe (|) and comma (,) delimiters are supported."

**E_INVALID_CONFIG**

- **Severity**: Non-catastrophic
- **Message**: `Invalid configuration: {config_detail}`
- **Description**: Invalid configuration parameters
- **Action**: Run creation fails with 400 status
- **User Guidance**: "Invalid configuration. Check parameters and try again."

---

## Error Statistics

### Typical Distributions

**Well-Formatted Data** (80-90% of files):
- Few to no errors
- Mostly warnings about data quality (dates out of range, duplicates)

**Typical Data Quality Issues** (10-20% of files):
- E_NUMERIC_FORMAT: 5-10 occurrences (percentage of data)
- E_DATE_MIXED_FORMAT: 1-5% of date values
- W_DUPLICATE_FOUND: 0-10% of keys

**Problem Files** (0-10% of files):
- Catastrophic errors caught during parsing phase
- E_JAGGED_ROW if column count varies
- E_UTF8_INVALID if file corrupted

---

## Error Severity Levels

### Catastrophic (E_*)

Processing **stops immediately**. Run state becomes `failed`.

Files:
- `E_UTF8_INVALID`
- `E_HEADER_MISSING`
- `E_JAGGED_ROW`
- `E_PROCESSING_FAILED`
- `E_SPILL_DIRECTORY_FULL`
- `E_FILE_ENCODING_ISSUE`

### Non-Catastrophic (E_* or W_*)

Processing **continues**. Errors are counted and reported.

Examples:
- `E_NUMERIC_FORMAT` - Invalid values excluded from stats
- `E_MONEY_FORMAT` - Invalid values excluded from stats
- `E_DATE_MIXED_FORMAT` - Inconsistent dates counted
- `W_DATE_RANGE` - Out-of-range dates flagged
- `W_LINE_ENDING_INCONSISTENT` - Handled automatically

---

## Handling in Frontend

### Toast Notifications

- **Catastrophic Error**: Show error toast with instructions, no retry option
- **Non-Catastrophic Errors**: Continue processing, show summary on completion

### Error Roll-Up Table

Display errors grouped by code:

| Error Code | Count | Message |
|------------|-------|---------|
| E_NUMERIC_FORMAT | 125 | Non-numeric values in numeric column |
| W_DATE_RANGE | 8 | Dates outside expected range |

### Linking to Affected Rows

Future versions may support:
- Error detail view with sample affected values
- Row-level error navigation
- Download error report

---

## Resolution Workflow

### For Each Error Category

1. **Read Error Message** - Understand what's wrong
2. **Check Error Count** - Assess severity
3. **Review Samples** - See example values
4. **Fix Source Data** - Correct file format
5. **Re-upload** - Run profiling again

### Common Fixes

| Error | Fix |
|-------|-----|
| E_UTF8_INVALID | Re-encode file to UTF-8 |
| E_HEADER_MISSING | Add header row |
| E_JAGGED_ROW | Check for extra/missing delimiters |
| E_NUMERIC_FORMAT | Remove currency symbols, separators |
| E_MONEY_FORMAT | Ensure exactly 2 decimal places |
| E_DATE_MIXED_FORMAT | Standardize date format |
| W_DUPLICATE_FOUND | Investigate data integrity |

---

## Logging

Each error is logged with:
- Error code
- Error message
- Row number (if applicable)
- Column name (if applicable)
- Timestamp
- Run ID

PII is redacted in logs; only error codes and counts appear.
