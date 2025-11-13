# Error Code Reference

Complete reference for all error and warning codes in the VQ8 Data Profiler.

## Error Classification

### Severity Levels

| Level | Impact | Action |
|-------|--------|--------|
| **Catastrophic** | Processing stops immediately | Fix data and re-upload |
| **Error** | Processing continues, issues logged | Review data quality |
| **Warning** | Processing continues, informational | Review if concerned |

## Error Code Format

Error codes follow this pattern:
- **Prefix**: `E_` (Error) or `W_` (Warning)
- **Category**: Area of concern (UTF8, PARSER, NUMERIC, etc.)
- **Description**: Specific issue

Example: `E_NUMERIC_FORMAT` = Error in numeric formatting

## Catastrophic Errors

These errors stop all processing immediately.

### E_UTF8_INVALID

**Category**: Encoding

**Message**: Invalid UTF-8 byte sequence detected

**Cause**: File contains non-UTF-8 characters or encoding is not UTF-8

**Example**:
```
File: data.csv
Byte offset: 42,891
Invalid sequence: 0xFF 0xFE
```

**Solution**:
1. Check file encoding:
   ```bash
   file -i data.csv
   ```

2. Convert to UTF-8:
   ```bash
   iconv -f ISO-8859-1 -t UTF-8 data.csv > data_utf8.csv
   ```

3. Remove BOM if present:
   ```bash
   sed '1s/^\xEF\xBB\xBF//' data.csv > data_clean.csv
   ```

**Prevention**:
- Always save files as UTF-8
- Use UTF-8 without BOM
- Validate encoding before upload

---

### E_HEADER_MISSING

**Category**: Structure

**Message**: Header row not found or file is empty

**Cause**: First row missing or file is empty

**Example**:
```
# Missing header
123,John,30
456,Jane,25

# Should be:
id,name,age
123,John,30
456,Jane,25
```

**Solution**:
1. Add header row with column names
2. Ensure file is not empty
3. Check for leading blank lines

**Prevention**:
- Always include header as first row
- Validate file has content before upload

---

### E_JAGGED_ROW

**Category**: Structure

**Message**: Inconsistent column count detected

**Cause**: Some rows have more or fewer columns than header

**Example**:
```
# Header: 3 columns
name,age,city

# Row 1: OK (3 columns)
John,30,NYC

# Row 2: ERROR (2 columns)
Jane,25

# Row 3: ERROR (4 columns)
Bob,40,LA,USA
```

**Details**:
```json
{
  "code": "E_JAGGED_ROW",
  "message": "Row 2 has 2 columns, expected 3",
  "row_number": 2,
  "expected_columns": 3,
  "actual_columns": 2
}
```

**Solution**:
1. Find problematic rows:
   ```bash
   awk -F'|' '{print NR, NF}' data.csv | grep -v "^[0-9]* 3$"
   ```

2. Fix column count:
   - Add missing columns (use empty string or NULL)
   - Remove extra columns
   - Check for unquoted embedded delimiters

3. Common causes:
   - Unquoted embedded delimiters
   - Missing trailing delimiter
   - Extra delimiters in data

**Prevention**:
- Quote fields containing delimiters
- Validate row length before creating CSV
- Use CSV validation tool

---

## Non-Catastrophic Errors

These errors are logged but processing continues.

### E_QUOTE_RULE

**Category**: Quoting

**Message**: Quote escaping violation detected

**Cause**: Inner quotes not properly doubled

**Example**:
```
# Incorrect
"He said "hello" to me"

# Correct
"He said ""hello"" to me"
```

**Impact**: Field may be incorrectly parsed, leading to data quality issues

**Solution**:
1. Double all inner quotes:
   ```python
   value = value.replace('"', '""')
   quoted_value = f'"{value}"'
   ```

2. Use proper CSV library:
   ```python
   import csv
   with open('file.csv', 'w', newline='') as f:
       writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
       writer.writerow(['He said "hello" to me'])
   ```

**Prevention**:
- Always use CSV library for writing
- Never manually construct quoted CSV
- Validate output with CSV parser

---

### E_UNQUOTED_DELIM

**Category**: Quoting

**Message**: Unquoted embedded delimiter detected

**Cause**: Field contains delimiter but is not quoted

**Example (pipe delimiter)**:
```
# Incorrect
John|New York, NY|USA

# Correct (if comma is delimiter)
John,"New York, NY",USA
```

**Impact**: Field split incorrectly, data in wrong columns

**Solution**:
1. Quote fields with embedded delimiters:
   ```python
   if delimiter in value:
       value = f'"{value}"'
   ```

2. Escape delimiters if not using quotes:
   ```python
   value = value.replace('|', '\\|')
   ```

**Prevention**:
- Quote all fields (safest approach)
- Use delimiter that doesn't appear in data
- Validate before writing

---

### E_NUMERIC_FORMAT

**Category**: Data Type

**Message**: Invalid numeric format detected

**Cause**: Numeric column contains non-numeric characters

**Examples**:
```
❌ $1,234.56     (currency symbol and comma)
❌ (123.45)      (parentheses for negative)
❌ 1,234         (comma separator)
❌ 123.45.67     (multiple decimals)
✅ 1234.56       (valid)
✅ -123.45       (valid)
✅ 123           (valid)
```

**Validation Rule**:
```regex
^-?[0-9]+(\.[0-9]+)?$
```

**Impact**: Value excluded from numeric statistics (min, max, mean, etc.)

**Solution**:
1. Remove currency symbols:
   ```python
   value = value.replace('$', '').replace('€', '')
   ```

2. Remove thousand separators:
   ```python
   value = value.replace(',', '')
   ```

3. Convert parentheses to negative:
   ```python
   if value.startswith('(') and value.endswith(')'):
       value = '-' + value[1:-1]
   ```

**Prevention**:
- Store numbers without formatting
- Use separate column for currency code
- Format only for display, not storage

---

### E_MONEY_FORMAT

**Category**: Data Type

**Message**: Invalid money format detected

**Cause**: Money column doesn't have exactly 2 decimals or contains symbols

**Examples**:
```
❌ $99.99        (currency symbol)
❌ 99.9          (only 1 decimal)
❌ 99            (no decimals)
❌ 99.999        (3 decimals)
❌ 1,234.56      (comma separator)
✅ 99.99         (valid)
✅ 0.01          (valid)
✅ 1234.56       (valid)
```

**Validation Rule**:
```regex
^-?[0-9]+\.[0-9]{2}$
```

**Impact**: Value excluded from money statistics

**Solution**:
1. Format to 2 decimals:
   ```python
   value = f"{float(value):.2f}"
   ```

2. Remove formatting:
   ```python
   value = value.replace('$', '').replace(',', '')
   value = f"{float(value):.2f}"
   ```

**Prevention**:
- Always store with exactly 2 decimals
- Use DECIMAL(10,2) in databases
- Format during export to CSV

---

### E_DATE_MIXED_FORMAT

**Category**: Data Type

**Message**: Inconsistent date formats in column

**Cause**: Multiple date formats used in same column

**Examples**:
```
# Inconsistent (ERROR)
2025-01-15
01/15/2025
15-Jan-2025

# Consistent (OK)
2025-01-15
2025-01-16
2025-01-17
```

**Impact**: Column marked as "mixed" type, date statistics not computed

**Solution**:
1. Standardize to single format (prefer YYYYMMDD):
   ```python
   from datetime import datetime

   def standardize_date(value):
       # Try multiple formats
       for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%Y']:
           try:
               dt = datetime.strptime(value, fmt)
               return dt.strftime('%Y%m%d')
           except ValueError:
               continue
       return None
   ```

2. Use ISO 8601 format (YYYY-MM-DD)

**Prevention**:
- Choose one date format for entire dataset
- Document format in data dictionary
- Validate dates before export

---

## Warnings

These are informational and may not require action.

### W_DATE_RANGE

**Category**: Data Type

**Message**: Date outside expected range

**Cause**: Date before 1900 or after current year + 1

**Examples**:
```
⚠️ 1850-01-01    (before 1900)
⚠️ 2050-12-31    (far future)
✅ 2020-01-01    (valid)
✅ 2025-01-15    (valid)
```

**Impact**: None (informational only)

**When This is Normal**:
- Historical data (birth dates, etc.)
- Future projections
- Calculated expiration dates

**When This is an Error**:
- Typos (2205 instead of 2025)
- Date parsing errors
- Default sentinel values (1900-01-01)

**Solution** (if error):
1. Review flagged dates:
   ```sql
   SELECT date_column, COUNT(*)
   FROM table
   WHERE date_column < '1900-01-01' OR date_column > '2026-12-31'
   GROUP BY date_column
   ```

2. Fix typos or parsing errors

**Action**: Review flagged dates; fix if incorrect

---

### W_LINE_ENDING

**Category**: Structure

**Message**: Mixed line endings detected (CRLF and LF)

**Cause**: File created on different systems or concatenated files

**Examples**:
```
# CRLF (Windows): \r\n
# LF (Unix):      \n
# CR (Old Mac):   \r
```

**Impact**: None (parser handles both)

**Solution** (if you want consistency):
1. Convert to CRLF:
   ```bash
   unix2dos file.csv
   ```

2. Convert to LF:
   ```bash
   dos2unix file.csv
   ```

3. Using Python:
   ```python
   with open('file.csv', 'r') as f:
       content = f.read()

   # Normalize to CRLF
   content = content.replace('\r\n', '\n').replace('\n', '\r\n')

   with open('file_normalized.csv', 'w') as f:
       f.write(content)
   ```

**Prevention**:
- Use consistent platform for file creation
- Configure git line ending handling
- Use text editor with line ending control

---

## Error Code Summary Table

| Code | Severity | Category | Stop Processing? |
|------|----------|----------|------------------|
| E_UTF8_INVALID | Catastrophic | Encoding | Yes |
| E_HEADER_MISSING | Catastrophic | Structure | Yes |
| E_JAGGED_ROW | Catastrophic | Structure | Yes |
| E_QUOTE_RULE | Error | Quoting | No |
| E_UNQUOTED_DELIM | Error | Quoting | No |
| E_NUMERIC_FORMAT | Error | Data Type | No |
| E_MONEY_FORMAT | Error | Data Type | No |
| E_DATE_MIXED_FORMAT | Error | Data Type | No |
| W_DATE_RANGE | Warning | Data Type | No |
| W_LINE_ENDING | Warning | Structure | No |

## Error Aggregation

Errors are aggregated by code in the final report:

```json
{
  "errors": [
    {
      "code": "E_NUMERIC_FORMAT",
      "message": "Invalid numeric format (contains symbols)",
      "count": 42,
      "percentage": 0.084
    },
    {
      "code": "E_MONEY_FORMAT",
      "message": "Invalid money format (not exactly 2 decimals)",
      "count": 18,
      "percentage": 0.036
    }
  ],
  "warnings": [
    {
      "code": "W_DATE_RANGE",
      "message": "Date outside expected range (1900-2026)",
      "count": 7,
      "percentage": 0.014
    }
  ]
}
```

## Troubleshooting by Symptom

### Processing Immediately Stops

**Likely Causes**:
- E_UTF8_INVALID
- E_HEADER_MISSING
- E_JAGGED_ROW

**Action**: Check first 10 rows of file, verify encoding

### High Error Count

**Likely Causes**:
- E_NUMERIC_FORMAT (currency symbols present)
- E_MONEY_FORMAT (inconsistent decimal places)
- E_DATE_MIXED_FORMAT (multiple date formats)

**Action**: Review top 10 values in problematic columns

### Column Shows "Mixed" Type

**Cause**: Multiple types detected in same column

**Action**: Review E_DATE_MIXED_FORMAT or other format errors

### Low Candidate Key Scores

**Cause**: High duplicate count or high null count

**Action**: Not an error; indicates data does not have good unique keys

## Best Practices

### Prevention Checklist

Before uploading files:

- [ ] Verify UTF-8 encoding
- [ ] Ensure header row is present
- [ ] Validate consistent column count
- [ ] Quote fields with embedded delimiters
- [ ] Remove currency symbols from numbers
- [ ] Standardize date formats
- [ ] Use exactly 2 decimals for money
- [ ] Normalize line endings (optional)

### Data Quality Checklist

After profiling:

- [ ] Review error roll-up (sort by count)
- [ ] Check top errors are acceptable
- [ ] Validate "mixed" type columns
- [ ] Review candidate keys
- [ ] Confirm expected types match inferred types
- [ ] Investigate unexpected null percentages

### Error Resolution Priority

1. **Fix Catastrophic** (stops processing)
2. **Fix High-Count Errors** (> 1% of rows)
3. **Fix Type Mismatches** (wrong type inferred)
4. **Review Warnings** (informational)
5. **Optimize** (improve data quality)

## Custom Error Handling

### Adding New Error Codes

For developers adding new validations:

1. **Define Code** (`services/errors.py`):
```python
class ErrorCode:
    E_PHONE_FORMAT = "E_PHONE_FORMAT"

ERROR_MESSAGES = {
    ErrorCode.E_PHONE_FORMAT: "Invalid phone number format"
}
```

2. **Raise Error**:
```python
from services.errors import ErrorAggregator, ErrorCode

aggregator = ErrorAggregator()

if not validate_phone(value):
    aggregator.record(
        ErrorCode.E_PHONE_FORMAT,
        ERROR_MESSAGES[ErrorCode.E_PHONE_FORMAT]
    )
```

3. **Document** (add to this file):
   - Error code and message
   - Cause and examples
   - Solution and prevention

## Support

For issues not covered in this reference:

- [User Guide](USER_GUIDE.md) - General troubleshooting
- [API Documentation](API.md) - Error response formats
- [Developer Guide](DEVELOPER_GUIDE.md) - Custom error handling
- [Architecture](ARCHITECTURE.md) - Error aggregation design
