# Test Fixtures

This directory contains golden test files covering various data profiling scenarios.

## Files

### Basic Cases
- `basic.csv` - Simple valid pipe-delimited CSV
- `comma_delimited.csv` - Comma-delimited CSV
- `with_header.csv` - CSV with proper header
- `no_header.csv` - CSV missing header (should fail)

### Quoting and Delimiters
- `quoted_fields.csv` - Fields with embedded delimiters in quotes
- `doubled_quotes.csv` - Quoted fields with doubled quotes
- `embedded_crlf.csv` - Quoted fields with embedded line breaks
- `quote_violations.csv` - Various quoting rule violations

### Line Endings
- `crlf_endings.csv` - Consistent CRLF line endings
- `lf_endings.csv` - Consistent LF line endings
- `mixed_endings.csv` - Mixed CRLF and LF (warning)
- `cr_only_endings.csv` - Old Mac CR-only endings

### Numeric and Money
- `valid_numeric.csv` - Valid numeric values
- `numeric_violations.csv` - Numbers with $, commas, etc.
- `valid_money.csv` - Valid money format (2 decimals)
- `money_violations.csv` - Money with $, commas, parentheses, wrong decimals

### Dates
- `dates_yyyymmdd.csv` - YYYYMMDD format (preferred)
- `dates_iso8601.csv` - ISO-8601 format (YYYY-MM-DD)
- `dates_us_format.csv` - US format (MM/DD/YYYY)
- `dates_mixed.csv` - Mixed date formats (error)
- `dates_out_of_range.csv` - Dates with year < 1900 or > current+1

### Type Inference
- `all_strings.csv` - String data
- `mixed_types.csv` - Mixed types in same column
- `code_values.csv` - Low cardinality dictionary-like values
- `with_nulls.csv` - Various null/empty patterns

### Duplicates and Keys
- `unique_records.csv` - All unique records
- `duplicate_records.csv` - Some duplicate records
- `high_cardinality.csv` - High cardinality column (good key candidate)
- `low_cardinality.csv` - Low cardinality column (poor key candidate)
- `compound_key.csv` - Requires compound key for uniqueness

### Error Cases
- `invalid_utf8.csv` - Invalid UTF-8 byte sequences
- `jagged_rows.csv` - Inconsistent column counts
- `large_file.csv.gz` - Large gzipped file for performance testing

### Edge Cases
- `empty.csv` - Empty file
- `single_row.csv` - Single data row
- `all_nulls.csv` - Column with all null values
- `unicode_chars.csv` - Various Unicode characters
- `very_long_fields.csv` - Fields exceeding typical lengths
