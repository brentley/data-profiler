# Test Fixture Files

This directory contains golden test data files for validating the data profiler's parser and validation logic. Each file is designed to test specific edge cases and validation rules defined in the BuildSpec.

## Test Files

### 1. quoted_fields.csv
**Purpose:** Test RFC 4180 quoting rules and delimiter handling

**Edge Cases Covered:**
- Row 1: Simple unquoted fields (baseline)
- Row 2: Embedded quotes within unquoted field
- Row 3: Pipe delimiter (|) within quoted field
- Row 4: CRLF (line breaks) within quoted field
- Row 5: Doubled quotes (`""`) for escaping within quoted field
- Row 6: Mix of quoted and unquoted fields in same row
- Row 7: Multiple edge cases combined (pipe + newline in quoted field)
- Row 8: Field starting with quote character
- Row 9: Trailing spaces in quoted field
- Row 10: Comma within field (should not confuse with CSV format)

**Expected Behavior:**
- Parser should correctly handle all quoted fields
- Pipe delimiters within quotes should NOT split fields
- CRLF within quotes should be preserved as part of field value
- Doubled quotes should be unescaped to single quotes
- No false positives on CSV comma detection

---

### 2. money_violations.csv
**Purpose:** Test Money type validation rules

**Valid Money Format:** `[-]NNNNNN.NN` (optional negative, 2 decimal places exactly)

**Test Cases:**
- Row 1-3, 10, 14: Valid money formats (baseline)
- Row 4: Contains dollar sign ($) - INVALID
- Row 5: Contains comma separator - INVALID
- Row 6: Parentheses notation for negative - INVALID
- Row 7: Only 1 decimal place - INVALID
- Row 8: No decimal places - INVALID
- Row 9: More than 2 decimal places - INVALID
- Row 11-12: Missing decimal precision - INVALID
- Row 13: Missing leading zero - INVALID (possibly valid with trimming)
- Row 15: Leading/trailing spaces - EDGE CASE

**Expected Behavior:**
- Only rows 1-3, 10, 14 should be classified as valid Money type
- Invalid formats should trigger validation warnings
- Column should be classified as "mixed" type if violations exist
- Warning messages should specify exact violation reason

---

### 3. dates_mixed.csv
**Purpose:** Test date format detection, validation, and consistency warnings

**Valid Date Formats:** YYYYMMDD, MM/DD/YYYY

**Valid Date Range:** 1900-01-01 to 2026-12-31

**Test Cases:**
- DateYYYYMMDD column: Consistent YYYYMMDD format (all valid)
- DateSlash column: Consistent MM/DD/YYYY format (all valid)
- DateMixed column: Mixed formats in same column (should warn)
- InvalidDates column: Various invalid dates
  - Row 1: Year 2027 (out of range, > 2026)
  - Row 2: Year 1899 (out of range, < 1900)
  - Row 3: Year 2050 (out of range)
  - Row 4: Empty/NULL date
  - Row 5: Invalid format (too many digits)
  - Row 6: Invalid day (Feb 30)
  - Row 7: Invalid month (13)
  - Row 8: All zeros
  - Row 9: NULL value
  - Row 10: Text instead of date
  - Row 11: ISO format (YYYY-MM-DD) - not in spec
  - Row 12: Invalid day (June 31)

**Expected Behavior:**
- DateYYYYMMDD: Detected as Date type with consistent format
- DateSlash: Detected as Date type with consistent format
- DateMixed: Warn about mixed formats (YYYYMMDD vs MM/DD/YYYY)
- InvalidDates: Validation errors for each specific violation
- Out-of-range dates should trigger warnings
- Invalid dates (Feb 30, June 31, month 13) should be flagged

---

### 4. duplicate_records.csv
**Purpose:** Test duplicate detection and key candidate identification

**Duplicate Cases:**
- Rows 1 & 4: Same ID (1001) - ID column has duplicates
- Rows 2 & 8: Same ID (1002) - ID column has duplicates
- Rows 4 & 8: Same First_Name + Last_Name (John Smith) at different dates
- Rows 1 & 7: Same Email (alice@example.com) - Email has duplicates
- Rows 5 & 11: Exact duplicate rows (all fields match)
- Rows 2 & 5: Same Email (bob@example.com) with different IDs

**Expected Behavior:**
- ID column should NOT be identified as unique key (has duplicates)
- Email column should NOT be identified as unique key (has duplicates)
- Employee_ID column should be identified as potential key (appears unique)
- Compound key candidates: First_Name + Last_Name + Date
- Duplicate row detection should flag rows 5 & 11 as exact duplicates
- Report should list all single-column uniqueness violations
- Report should suggest compound key alternatives

---

### 5. mixed_types.csv
**Purpose:** Test type inference with inconsistent data

**Column Analysis:**
- NumericThenText: Starts numeric (rows 1-3), becomes text (row 4), back to numeric/text mix
  - Expected: Mixed type with warnings
- MostlyDates: All dates except row 6 (NOT_A_DATE) and row 11 (empty)
  - Expected: Date type with validation errors
- InconsistentFormat: Money format but row 7 has text (ABC123)
  - Expected: Mixed type, not classified as Money
- ShouldBeInt: Integers except row 5 (46.5) and row 9 (FIFTY)
  - Expected: Mixed type or Integer with validation errors
- ShouldBeMixed: Truly mixed (integer, text, money, boolean, date, NULL)
  - Expected: Mixed type with multiple format detections

**Expected Behavior:**
- Type inference should detect majority type but flag inconsistencies
- Columns with >10% type violations should be classified as "mixed"
- Each type violation should generate a warning with row number
- Report should show percentage of each type detected

---

### 6. compound_key.csv
**Purpose:** Test multi-column key detection

**Key Candidates:**
- Employee_ID: Unique single-column key (10 unique values in 10 rows)
- First_Name: NOT unique (John Smith appears 3 times)
- Last_Name: NOT unique (Smith appears 3 times)
- First_Name + Last_Name: NOT unique (John Smith appears 3 times)
- First_Name + Last_Name + Date: UNIQUE (all combinations unique)
- First_Name + Date: UNIQUE (all combinations unique)
- Last_Name + Date: UNIQUE (all combinations unique)

**Test Cases:**
- Row 1, 5, 8: John Smith on different dates and departments
- Rows demonstrate that name alone is insufficient as a key
- Date + Name combinations provide uniqueness

**Expected Behavior:**
- Employee_ID should be identified as primary key candidate
- First_Name + Last_Name should be flagged as non-unique
- First_Name + Last_Name + Date should be identified as compound key candidate
- Report should list all viable compound key combinations
- System should rank keys by simplicity (prefer fewer columns)

---

## Usage in Tests

These files should be used in integration tests to validate:

1. **Parser Functionality**
   - RFC 4180 compliance (quoted_fields.csv)
   - Delimiter detection and handling
   - CRLF handling within quoted fields

2. **Type Inference**
   - Money type detection (money_violations.csv)
   - Date type detection (dates_mixed.csv)
   - Mixed type classification (mixed_types.csv)

3. **Validation Rules**
   - Money format validation (money_violations.csv)
   - Date range validation (dates_mixed.csv)
   - Date format consistency warnings (dates_mixed.csv)

4. **Data Quality Analysis**
   - Duplicate detection (duplicate_records.csv)
   - Key candidate identification (duplicate_records.csv, compound_key.csv)
   - Compound key discovery (compound_key.csv)

## Test Execution

Example test structure:

```python
def test_quoted_fields_parsing():
    """Test parser handles quoted fields correctly"""
    profile = profile_file('tests/fixtures/quoted_fields.csv')
    assert len(profile['columns']) == 5
    assert profile['row_count'] == 10
    # Verify row 4 Description field contains CRLF
    # Verify row 3 Description contains pipe character

def test_money_violations():
    """Test money type validation"""
    profile = profile_file('tests/fixtures/money_violations.csv')
    amount_col = profile['columns']['Amount']
    assert amount_col['inferred_type'] == 'mixed'  # Has violations
    assert len(amount_col['validation_errors']) > 0
    # Verify specific error messages for rows 4-9, 11-13

def test_duplicate_detection():
    """Test duplicate row and key analysis"""
    profile = profile_file('tests/fixtures/duplicate_records.csv')
    assert 'Employee_ID' not in profile['duplicate_violations']
    assert 'ID' in profile['duplicate_violations']
    assert len(profile['exact_duplicates']) > 0
```

## Maintenance

When updating test files:
1. Maintain pipe (|) delimiter for all files
2. Keep files small (10-50 rows) for quick test execution
3. Document new edge cases in this README
4. Ensure files cover all validation rules in BuildSpec
5. Add corresponding test cases for new fixtures

## Related Documentation

- BuildSpec: `BuildSpec.md` (defines all validation rules)
- Parser Implementation: `src/parser.py`
- Validation Logic: `src/validators.py`
- Integration Tests: `tests/test_integration.py`
