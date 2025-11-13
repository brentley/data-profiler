# User Guide

Welcome to the VQ8 Data Profiler user guide. This guide will walk you through using the profiler to analyze your CSV and TXT files.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Uploading Files](#uploading-files)
3. [Understanding the Dashboard](#understanding-the-dashboard)
4. [Column Profiles](#column-profiles)
5. [Candidate Keys](#candidate-keys)
6. [Error Codes](#error-codes)
7. [Downloading Reports](#downloading-reports)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Getting Started

### Accessing the Application

Once the application is running, open your web browser and navigate to:
- **Web UI**: http://localhost:5173

You should see the upload page with options to select a file and configure processing settings.

### Supported File Types

The profiler accepts the following file types:
- `.txt` - Plain text files with delimited data
- `.csv` - Comma-separated values files
- `.txt.gz` - Gzipped text files
- `.csv.gz` - Gzipped CSV files

### File Requirements

Your data file must meet these requirements:

1. **UTF-8 Encoding**: Files must be encoded in UTF-8
2. **Header Row**: First row must contain column names
3. **Consistent Columns**: All rows must have the same number of columns
4. **Delimiter**: Choose between pipe (`|`) or comma (`,`)
5. **Line Endings**: CRLF (`\r\n`) preferred, but LF (`\n`) also accepted

## Uploading Files

### Step 1: Select Your File

1. Click the **"Choose File"** or **"Browse"** button
2. Navigate to your file location
3. Select a `.txt`, `.csv`, `.txt.gz`, or `.csv.gz` file
4. The file name will appear once selected

### Step 2: Configure Settings

#### Delimiter Selection
Choose the delimiter used in your file:
- **Pipe (`|`)**: Common in many data systems (default)
- **Comma (`,`)**: Standard CSV format

**Tip**: If unsure, open your file in a text editor and look at the first few lines to identify the separator character.

#### Quote Handling
- **Quoted Fields**: Check this if your data uses double quotes (`"`) around field values
- Default: Enabled (recommended)

#### Line Ending Expectation
- **Expect CRLF**: Check if your file uses Windows-style line endings (`\r\n`)
- Default: Enabled

**Note**: The profiler accepts both CRLF and LF line endings regardless of this setting, but may issue warnings if they don't match your expectation.

### Step 3: Start Processing

1. Click **"Upload and Profile"** button
2. You'll be redirected to the status page
3. Watch the progress bar as your file is processed

### What Happens During Processing

The profiler performs these operations in order:

1. **Validation**: Checks UTF-8 encoding, header presence, and column consistency
2. **Parsing**: Reads the file row-by-row with proper quote handling
3. **Type Inference**: Determines the data type for each column
4. **Statistical Analysis**: Computes exact metrics for each column
5. **Pattern Detection**: Identifies candidate uniqueness keys
6. **Report Generation**: Creates JSON, CSV, and HTML outputs

## Understanding the Dashboard

Once processing completes, you'll see the results dashboard with several sections:

### File Summary Card

Located at the top of the dashboard:

- **File Name**: Original uploaded file name
- **Row Count**: Total number of data rows (excluding header)
- **Column Count**: Number of columns detected
- **Delimiter**: Detected delimiter (pipe or comma)
- **Line Endings**: Detected line ending style (CRLF or LF)
- **Processing Time**: Total time to complete profiling
- **Status Badge**: Overall result (PASS/WARN/FAIL)

### Error Roll-Up Section

Displays aggregated errors and warnings:

| Error Code | Message | Count | Severity |
|------------|---------|-------|----------|
| E_NUMERIC_FORMAT | Invalid numeric format | 42 | Non-Catastrophic |
| W_DATE_RANGE | Date out of expected range | 7 | Warning |

**Color Coding**:
- **Red**: Catastrophic errors (processing stopped)
- **Orange**: Non-catastrophic errors (processing continued)
- **Yellow**: Warnings (informational)

### Candidate Keys Section

Shows suggested uniqueness keys (see [Candidate Keys](#candidate-keys) section below).

### Column Cards Grid

Each column has its own card with detailed statistics (see [Column Profiles](#column-profiles) section below).

## Column Profiles

Each column card provides comprehensive information about that column's data.

### Universal Metrics

All columns display these metrics:

#### Column Name
The header name from your CSV file.

#### Inferred Type
One of these types:
- **Alpha**: General string data
- **Varchar**: Variable-length strings
- **Code**: Dictionary-like codes (low cardinality)
- **Numeric**: Numbers with optional decimal point
- **Money**: Exactly 2 decimal places
- **Date**: Consistent date format
- **Mixed**: Multiple types detected (indicates data quality issue)
- **Unknown**: Type could not be determined

**Type Badge Colors**:
- Blue: String types (Alpha, Varchar, Code)
- Green: Numeric types (Numeric, Money)
- Purple: Date types
- Red: Mixed or Unknown

#### Null Statistics
- **Null Count**: Number of null/empty values
- **Null Percentage**: Percentage of rows that are null
- **Gauge**: Visual representation of null percentage

#### Distinct Values
- **Distinct Count**: Number of unique values
- **Uniqueness %**: Percentage of unique values
- **Indicator**: High uniqueness may suggest a candidate key

#### Top 10 Values
A table showing the most frequent values:

| Value | Count | % of Total |
|-------|-------|------------|
| Active | 8,542 | 42.7% |
| Inactive | 5,123 | 25.6% |
| Pending | 3,892 | 19.5% |
| ... | ... | ... |

**Note**: Actual data values are shown here for analysis purposes.

### String-Type Metrics

For **Alpha**, **Varchar**, and **Code** columns:

#### Length Statistics
- **Min Length**: Shortest value length
- **Max Length**: Longest value length
- **Average Length**: Mean value length

Example:
```
Min: 2 characters
Max: 45 characters
Avg: 12.5 characters
```

#### Character Set Notes
- Presence of non-ASCII characters
- Special character detection
- Unicode warnings if applicable

### Numeric & Money Metrics

For **Numeric** and **Money** columns:

#### Basic Statistics
- **Min**: Smallest value
- **Max**: Largest value
- **Mean**: Average value
- **Median**: Middle value (50th percentile)
- **Std Dev**: Standard deviation (measure of spread)

Example:
```
Min: $0.00
Max: $1,245.67
Mean: $342.89
Median: $298.50
Std Dev: $187.23
```

#### Quantiles
Distribution percentiles:
- **p1**: 1st percentile
- **p5**: 5th percentile
- **p25**: 25th percentile (Q1)
- **p50**: Median (Q2)
- **p75**: 75th percentile (Q3)
- **p95**: 95th percentile
- **p99**: 99th percentile

**Interpretation**: These help identify outliers and understand data distribution.

#### Histogram
Visual representation of value distribution across bins.

#### Gaussian Test
- **Test Type**: D'Agostino or Pearson
- **P-Value**: Statistical measure of normality
- **Interpretation**: p-value > 0.05 suggests normal distribution

**Why It Matters**: Normal distributions are easier to model and analyze statistically.

#### Money-Specific Validations

For **Money** type columns:
- **Two Decimal Check**: All values have exactly 2 decimals
- **Disallowed Symbols**: No `$`, `,`, or `()` found
- **Violations Count**: Number of rows that failed validation

Example violations:
```
❌ $1,234.56  (contains $ and comma)
❌ 1234.5     (only 1 decimal place)
✅ 1234.56    (valid)
```

### Date Metrics

For **Date** columns:

#### Format Detection
- **Detected Format**: Consistent format found (e.g., `YYYYMMDD`, `MM/DD/YYYY`)
- **Format Confidence**: How consistently the format appears

Example formats:
- `YYYYMMDD`: 20250115
- `YYYY-MM-DD`: 2025-01-15
- `MM/DD/YYYY`: 01/15/2025
- `DD-MMM-YYYY`: 15-JAN-2025

#### Date Range
- **Min Date**: Earliest date found
- **Max Date**: Latest date found
- **Date Span**: Range in days/months/years

Example:
```
Min: 2020-01-01
Max: 2025-12-31
Span: 6 years
```

#### Out-of-Range Warnings
Flags dates that seem unusual:
- **Before 1900**: Historical data warning
- **After Current Year + 1**: Future date warning
- **Count**: Number of out-of-range dates

#### Distribution
Visual representation of dates by:
- Month
- Year
- Day of week (if applicable)

**Use Case**: Identify seasonal patterns or data collection gaps.

## Candidate Keys

Candidate keys are columns (or combinations of columns) that could uniquely identify each row.

### What Are Candidate Keys?

A good candidate key has:
1. **High Uniqueness**: Most values are distinct
2. **Low Null Rate**: Few missing values
3. **Consistency**: No format violations

### Single-Column Keys

Individual columns suggested as potential unique identifiers:

Example:
```
Column: customer_id
├─ Distinct Ratio: 99.8%
├─ Null Ratio: 0.1%
└─ Score: 0.997
```

### Compound Keys

Combinations of 2-3 columns that together might be unique:

Example:
```
Columns: [order_date, customer_id, product_id]
├─ Distinct Ratio: 100%
├─ Null Ratio Sum: 0.2%
└─ Score: 0.998
```

### Using Candidate Keys

#### Step 1: Review Suggestions
Look at the candidate keys section and review the scores:
- **Score > 0.99**: Excellent candidate
- **Score 0.95-0.99**: Good candidate
- **Score < 0.95**: May have duplicates

#### Step 2: Confirm Selection
1. Check the boxes next to the keys you want to validate
2. Click **"Confirm Selected Keys"** button
3. The system will perform exact duplicate detection

#### Step 3: Review Duplicate Report
After confirmation, you'll see:
- **Duplicate Count**: Number of duplicate rows found
- **Duplicate Percentage**: % of total rows
- **Duplicate Details**: If applicable, sample duplicate values

### Why Candidate Keys Matter

- **Data Quality**: Duplicates may indicate data quality issues
- **Database Design**: Helps identify natural primary keys
- **Data Integration**: Useful for matching records across systems
- **Validation**: Confirms uniqueness assumptions

## Error Codes

Understanding error codes helps diagnose data quality issues.

### Catastrophic Errors

These errors stop processing immediately:

#### E_UTF8_INVALID
**Message**: Invalid UTF-8 byte sequence detected

**Cause**: File contains non-UTF-8 characters

**Solution**:
- Re-save file with UTF-8 encoding
- Use `iconv` or similar tool to convert encoding
- Remove or replace non-UTF-8 characters

#### E_HEADER_MISSING
**Message**: Header row not found

**Cause**: First row doesn't contain column names, or file is empty

**Solution**:
- Add header row with column names
- Ensure file is not empty

#### E_JAGGED_ROW
**Message**: Inconsistent column count detected

**Cause**: Some rows have more or fewer columns than the header

**Solution**:
- Fix rows with missing or extra delimiters
- Check for unquoted embedded delimiters
- Ensure proper quote escaping

Example:
```
Header:  name,age,city          (3 columns)
Row 1:   John,30,New York       ✅ OK
Row 2:   Jane,25                ❌ Only 2 columns
Row 3:   Bob,40,LA,USA          ❌ 4 columns
```

### Non-Catastrophic Errors

These errors are logged but processing continues:

#### E_QUOTE_RULE
**Message**: Quote escaping violation

**Cause**: Inner quotes not properly doubled

**Solution**: Double all inner quotes

Example:
```
❌ "He said "hello" to me"
✅ "He said ""hello"" to me"
```

#### E_UNQUOTED_DELIM
**Message**: Unquoted embedded delimiter

**Cause**: Delimiter character appears in unquoted field

**Solution**: Wrap field in quotes

Example (comma delimiter):
```
❌ John,New York, NY,USA
✅ John,"New York, NY",USA
```

#### E_NUMERIC_FORMAT
**Message**: Invalid numeric format

**Cause**: Non-numeric characters in numeric field

**Solution**: Remove currency symbols, commas, parentheses

Example:
```
❌ $1,234.56
❌ (123.45)
✅ 1234.56
✅ -123.45
```

#### E_MONEY_FORMAT
**Message**: Invalid money format

**Cause**: Money field doesn't have exactly 2 decimals or contains symbols

**Solution**: Format as plain number with 2 decimals

Example:
```
❌ $99.9
❌ 99.999
❌ 99
✅ 99.90
✅ 99.99
```

#### E_DATE_MIXED_FORMAT
**Message**: Inconsistent date formats in column

**Cause**: Multiple date formats used in same column

**Solution**: Standardize to one format (preferably YYYYMMDD)

Example:
```
❌ Mixed formats in same column:
   2025-01-15
   01/15/2025
   15-Jan-2025

✅ Consistent format:
   2025-01-15
   2025-01-16
   2025-01-17
```

### Warnings

These are informational and may not require action:

#### W_DATE_RANGE
**Message**: Date outside expected range

**Cause**: Date before 1900 or after next year

**Example**:
```
⚠️ 1850-01-01  (historical data?)
⚠️ 2050-12-31  (future projection?)
```

#### W_LINE_ENDING
**Message**: Mixed line endings detected

**Cause**: File contains both CRLF and LF

**Solution**: Normalize line endings (optional)

## Downloading Reports

The profiler generates multiple report formats for different use cases.

### JSON Profile

**Endpoint**: `/runs/{run_id}/profile`

**Use Case**: Programmatic access, data integration

**Contents**:
- Complete profiling results
- All metrics and statistics
- Machine-readable format

**Example Usage**:
```bash
curl http://localhost:8000/runs/{run_id}/profile > profile.json
```

### CSV Metrics

**Endpoint**: `/runs/{run_id}/metrics.csv`

**Use Case**: Spreadsheet analysis, reporting

**Contents**:
- One row per column
- Key metrics in columns
- Easy to filter and sort

**Columns**:
- Column Name
- Type
- Row Count
- Null Count
- Null %
- Distinct Count
- Min
- Max
- Mean
- Median
- Std Dev

**Example Usage**:
- Open in Excel/Google Sheets
- Import into BI tools
- Merge with other reports

### HTML Report

**Endpoint**: `/runs/{run_id}/report.html`

**Use Case**: Sharing results, documentation

**Contents**:
- Interactive visualizations
- Sortable tables
- Embedded charts
- Printable format

**Features**:
- Self-contained (no external dependencies)
- Dark mode compatible
- Responsive design
- Printable

### Audit Log

**Location**: `/data/outputs/{run_id}/audit.log.json`

**Use Case**: Compliance, debugging, auditing

**Contents**:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-01-15T10:30:00Z",
  "input_file_hash": "sha256:abc123...",
  "byte_count": 1073741824,
  "row_count": 500000,
  "column_count": 50,
  "processing_time_seconds": 45.2,
  "errors": {
    "E_NUMERIC_FORMAT": 12,
    "W_DATE_RANGE": 3
  }
}
```

**Note**: Contains no actual data values (PHI/PII safe).

## Best Practices

### Before Uploading

1. **Verify Encoding**: Ensure file is UTF-8
   ```bash
   file -i yourfile.csv
   # Should show: charset=utf-8
   ```

2. **Check Delimiter**: Open file to confirm delimiter
   ```bash
   head -5 yourfile.csv
   ```

3. **Validate Structure**: Ensure consistent column count
   ```bash
   awk -F'|' '{print NF}' yourfile.csv | sort -u
   # Should show one number
   ```

4. **Test with Sample**: For large files, test with first 1000 rows
   ```bash
   head -1001 largefile.csv > sample.csv
   # Upload sample first
   ```

### During Processing

1. **Monitor Progress**: Watch the progress bar
2. **Check Logs**: If processing seems slow, check browser console
3. **Don't Refresh**: Avoid refreshing page during processing
4. **Be Patient**: Large files (3+ GiB) may take several minutes

### After Processing

1. **Review Errors First**: Check error roll-up before analyzing data
2. **Validate Types**: Ensure inferred types match expectations
3. **Check Candidate Keys**: Confirm uniqueness before database import
4. **Download All Formats**: Keep JSON for programmatic access, CSV for analysis
5. **Archive Audit Log**: Store audit.log.json for compliance

### Data Quality Tips

1. **Standardize Dates**: Use YYYYMMDD format when possible
2. **Remove Currency Symbols**: Clean numeric data before upload
3. **Consistent Nulls**: Use empty strings or NULL consistently
4. **Quote When Needed**: Always quote fields with embedded delimiters
5. **Validate Encoding**: Use UTF-8 without BOM

## Troubleshooting

### Upload Fails

**Symptom**: Error during file upload

**Possible Causes**:
1. File too large for available disk space
2. Invalid file format
3. Permissions issue

**Solutions**:
- Check available disk space: `df -h /data`
- Verify file extension: `.txt`, `.csv`, `.txt.gz`, `.csv.gz`
- Check Docker volume permissions

### Processing Hangs

**Symptom**: Progress bar stuck at same percentage

**Possible Causes**:
1. Very large file (expected for 3+ GiB files)
2. Memory exhaustion
3. Disk I/O bottleneck

**Solutions**:
- Wait longer (large files can take 5-10 minutes)
- Check container logs: `docker compose logs api -f`
- Increase Docker memory limit if needed
- Check disk I/O: `iostat -x 1`

### Unexpected Types

**Symptom**: Column shows wrong type (e.g., Money shown as Alpha)

**Possible Causes**:
1. Mixed formats in column
2. Currency symbols or commas present
3. Inconsistent decimal places

**Solutions**:
- Clean data before upload
- Check "Top 10 Values" for problematic entries
- Review error roll-up for format violations

### Missing Candidate Keys

**Symptom**: No candidate keys suggested

**Possible Causes**:
1. No columns with high uniqueness
2. High null rates in all columns
3. Data quality issues

**Solutions**:
- Review column distinct ratios
- Check for duplicate rows in source data
- Consider compound keys (manually check combinations)

### Slow Performance

**Symptom**: Processing slower than expected

**Possible Causes**:
1. Insufficient memory
2. Slow disk (HDD vs SSD)
3. Many columns (100+)

**Solutions**:
- Ensure 8+ GB RAM available
- Use SSD for `/data` volume
- Consider profiling fewer columns
- Optimize file format (pipe vs comma delimiter)

### Can't Download Reports

**Symptom**: Download buttons not working

**Possible Causes**:
1. Processing not complete
2. Browser blocking downloads
3. Disk space exhausted

**Solutions**:
- Wait for "Completed" status
- Check browser download settings
- Verify disk space: `df -h /data`
- Check browser console for errors

## Getting Help

If you encounter issues not covered in this guide:

1. **Check Logs**:
   ```bash
   docker compose logs api -f
   ```

2. **Review Error Codes**: See [Error Codes](#error-codes) section

3. **Check API Documentation**: Visit http://localhost:8000/docs

4. **Review Architecture**: See `ARCHITECTURE.md` for technical details

5. **Developer Guide**: See `DEVELOPER_GUIDE.md` for advanced topics

## Appendix: Example Workflows

### Workflow 1: Quick Quality Check

Goal: Quickly check if a file is suitable for database import

1. Upload file with default settings
2. Check error roll-up for catastrophic errors
3. Review inferred types match expected schema
4. Confirm candidate keys match expected primary keys
5. If PASS, proceed with import

### Workflow 2: Comprehensive Analysis

Goal: Deep dive into data quality issues

1. Upload file
2. Review all column profiles
3. Note any "Mixed" or "Unknown" types
4. Check top 10 values for unexpected entries
5. Review all error codes with counts
6. Export CSV metrics for reporting
7. Share HTML report with stakeholders

### Workflow 3: Duplicate Detection

Goal: Find and quantify duplicate rows

1. Upload file
2. Wait for processing to complete
3. Review candidate key suggestions
4. Select most promising key (highest score)
5. Click "Confirm Selected Keys"
6. Review duplicate count and percentage
7. Download JSON profile with duplicate details

### Workflow 4: Schema Validation

Goal: Verify file matches expected schema

1. Create expected schema document:
   - Column names
   - Expected types
   - Expected null rates
2. Upload file and profile
3. Compare inferred types to expected types
4. Check for missing or extra columns
5. Validate null percentages within acceptable range
6. Document any deviations

---

## Conclusion

The VQ8 Data Profiler provides comprehensive insights into your CSV and TXT files with exact metrics and intelligent analysis. By following this guide, you can effectively:

- Profile files of any size
- Understand your data quality
- Identify uniqueness keys
- Troubleshoot issues
- Generate reports for stakeholders

For technical details, see the other documentation files in the `/docs` folder.
