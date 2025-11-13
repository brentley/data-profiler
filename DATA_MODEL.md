# Data Model and Schema

Complete specification of the database schema, data structures, and SQLite indices used for profiling operations.

## Overview

The data profiler uses SQLite for:
1. Persistent storage of run metadata (one database per deployment)
2. Per-run temporary indices for exact distinct counting
3. Duplicate detection across confirmed keys

## Database Schema

### Main Database (`/data/work/profiler.db`)

Central database storing all run metadata and results.

#### Table: runs

Stores run metadata and configuration.

```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,  -- ISO 8601 timestamp
    updated_at TEXT NOT NULL,  -- ISO 8601 timestamp
    state TEXT NOT NULL,       -- queued | processing | completed | failed
    progress_pct FLOAT NOT NULL DEFAULT 0.0,
    delimiter TEXT NOT NULL,   -- '|' or ','
    quoted BOOLEAN NOT NULL DEFAULT 1,  -- 1=true, 0=false
    expect_crlf BOOLEAN NOT NULL DEFAULT 1,
    source_filename TEXT,      -- Original uploaded filename
    bytes_processed INTEGER,
    rows_processed INTEGER,
    error_count INTEGER,
    warning_count INTEGER
);

CREATE INDEX idx_runs_state ON runs(state);
CREATE INDEX idx_runs_created ON runs(created_at DESC);
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| run_id | TEXT (UUID) | Primary key, unique identifier |
| created_at | TEXT | ISO 8601 timestamp of run creation |
| updated_at | TEXT | ISO 8601 timestamp of last update |
| state | TEXT | Current state (queued, processing, completed, failed) |
| progress_pct | FLOAT | Percentage complete (0-100) |
| delimiter | TEXT | Column delimiter (pipe or comma) |
| quoted | BOOLEAN | Whether CSV quoting is expected |
| expect_crlf | BOOLEAN | Whether CRLF line endings expected |
| source_filename | TEXT | Original filename from upload |
| bytes_processed | INTEGER | Total bytes read |
| rows_processed | INTEGER | Total rows processed |
| error_count | INTEGER | Total error count |
| warning_count | INTEGER | Total warning count |

**Indexing**
- Primary key on run_id for fast lookups
- State index for filtering by status
- Created index for sorting/filtering by time

#### Table: columns

Per-column profiling results.

```sql
CREATE TABLE columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,           -- 0-based column position
    name TEXT NOT NULL,
    inferred_type TEXT NOT NULL,        -- alpha|varchar|code|numeric|money|date|mixed|unknown
    null_count INTEGER,
    nonnull_count INTEGER,
    distinct_count INTEGER,
    top_values_json TEXT,               -- JSON array of {value, count} objects
    length_min INTEGER,
    length_max INTEGER,
    length_avg REAL,
    numeric_json TEXT,                  -- JSON with numeric stats
    money_json TEXT,                    -- JSON with money-specific stats
    date_json TEXT,                     -- JSON with date stats
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_columns_run ON columns(run_id);
CREATE UNIQUE INDEX idx_columns_run_ordinal ON columns(run_id, ordinal);
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| run_id | TEXT | Foreign key to runs table |
| ordinal | INTEGER | 0-based column index |
| name | TEXT | Column name from header |
| inferred_type | TEXT | Detected type |
| null_count | INTEGER | Number of NULL values |
| nonnull_count | INTEGER | Number of non-NULL values |
| distinct_count | INTEGER | Count of unique values |
| top_values_json | TEXT | JSON array of top 10 values |
| length_min | INTEGER | Minimum string length (or NULL) |
| length_max | INTEGER | Maximum string length (or NULL) |
| length_avg | REAL | Average string length (or NULL) |
| numeric_json | TEXT | Numeric stats (if applicable) |
| money_json | TEXT | Money validation (if applicable) |
| date_json | TEXT | Date stats (if applicable) |

**Top Values JSON Schema**

```json
[
  {"value": "example_value_1", "count": 150},
  {"value": "example_value_2", "count": 100},
  {"value": null, "count": 50}
]
```

**Numeric JSON Schema**

```json
{
  "min": 0.0,
  "max": 1000.0,
  "mean": 500.0,
  "median": 450.0,
  "stddev": 250.0,
  "quantiles": {
    "p1": 10.0,
    "p5": 50.0,
    "p25": 250.0,
    "p50": 450.0,
    "p75": 750.0,
    "p95": 950.0,
    "p99": 990.0
  },
  "gaussian_pvalue": 0.05,
  "gaussian_test": "dagostino",
  "histogram": {
    "0-100": 1500,
    "100-200": 1200,
    "200-500": 2000,
    "500-1000": 1500,
    "1000+": 800
  }
}
```

**Money JSON Schema**

```json
{
  "violations_count": 5,
  "two_decimal_ok": false,
  "disallowed_symbols_found": true,
  "violation_types": {
    "wrong_decimal_count": 3,
    "has_currency_symbol": 2,
    "has_thousands_separator": 0
  }
}
```

**Date JSON Schema**

```json
{
  "detected_format": "YYYY-MM-DD",
  "min": "2020-01-01",
  "max": "2024-12-31",
  "out_of_range_count": 5,
  "distribution_by_year": {
    "2020": 1000,
    "2021": 5000,
    "2022": 10000,
    "2023": 8000,
    "2024": 6000
  },
  "distribution_by_month": {
    "2024-01": 500,
    "2024-02": 480,
    "2024-03": 520
  },
  "format_inconsistencies": 3
}
```

#### Table: errors

Categorized errors and warnings.

```sql
CREATE TABLE errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    error_code TEXT NOT NULL,  -- E_* or W_*
    error_message TEXT,
    error_count INTEGER,
    column_name TEXT,
    row_number INTEGER,
    sample_value TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_errors_run ON errors(run_id);
CREATE INDEX idx_errors_code ON errors(error_code);
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| run_id | TEXT | Foreign key to runs |
| error_code | TEXT | Error code (E_* or W_*) |
| error_message | TEXT | Human-readable message |
| error_count | INTEGER | Number of occurrences |
| column_name | TEXT | Affected column (if applicable) |
| row_number | INTEGER | First affected row (if applicable) |
| sample_value | TEXT | Example value causing error (redacted) |

#### Table: candidate_keys

Suggested uniqueness keys.

```sql
CREATE TABLE candidate_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    columns_json TEXT NOT NULL,    -- JSON array of column names
    distinct_ratio REAL,
    null_ratio_sum REAL,
    score REAL,
    suggested BOOLEAN DEFAULT 1,   -- Whether suggested to user
    confirmed BOOLEAN DEFAULT 0,   -- User has confirmed this key
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_candidate_keys_run ON candidate_keys(run_id);
CREATE INDEX idx_candidate_keys_score ON candidate_keys(score DESC);
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| run_id | TEXT | Foreign key to runs |
| columns_json | TEXT | JSON array of column names |
| distinct_ratio | REAL | Distinct values / total rows |
| null_ratio_sum | REAL | Sum of null ratios for key columns |
| score | REAL | Composite score for ranking |
| suggested | BOOLEAN | Whether in suggestions list |
| confirmed | BOOLEAN | User has confirmed key |

**Columns JSON Schema**

```json
["id"]
```

or

```json
["first_name", "last_name", "date_of_birth"]
```

#### Table: confirmed_keys

User-confirmed keys for duplicate detection.

```sql
CREATE TABLE confirmed_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    columns_json TEXT NOT NULL,     -- JSON array of column names
    duplicate_count INTEGER,        -- Number of duplicates found
    confirmed_at TEXT,              -- Timestamp of confirmation
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_confirmed_keys_run ON confirmed_keys(run_id);
```

#### Table: logs

Structured logs with PII redaction.

```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    ts TEXT NOT NULL,               -- ISO 8601 timestamp
    level TEXT NOT NULL,            -- DEBUG|INFO|WARN|ERROR
    code TEXT,                      -- Error/warning code (if applicable)
    message TEXT NOT NULL,
    redaction_applied BOOLEAN DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_logs_run ON logs(run_id);
CREATE INDEX idx_logs_level ON logs(level);
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| run_id | TEXT | Foreign key to runs |
| ts | TEXT | ISO 8601 timestamp |
| level | TEXT | Log level (DEBUG, INFO, WARN, ERROR) |
| code | TEXT | Error code (if error/warning) |
| message | TEXT | Log message (PII redacted) |
| redaction_applied | BOOLEAN | Whether redaction was applied |

---

## Per-Run Temporary Database

Each run creates a temporary SQLite database at `/data/work/runs/{run_id}/temp.db` for:
1. Exact distinct value tracking
2. Duplicate detection
3. Statistical calculations

### Temporary Tables (Per Column)

#### Table: col_{n}_values

For each column n, exact distinct tracking.

```sql
CREATE TABLE col_0_values (
    value TEXT NOT NULL,
    cnt INTEGER NOT NULL,
    UNIQUE(value)
);

CREATE INDEX idx_col_0_values_cnt ON col_0_values(cnt DESC);
```

**Purpose**: Track exact distinct values and their frequencies

**Strategy**:
- Insert each value with count=1 on first occurrence
- Increment count on duplicate
- Unique constraint ensures one entry per value
- Can spill to disk if memory-constrained

**Memory Optimization**:
- Store only value and count (minimal footprint)
- Can handle 10M+ distinct values with proper spill configuration
- Index on count for efficient top-10 queries

### Duplicate Detection

#### Table: keyhashes

For compound key duplicate detection.

```sql
CREATE TABLE keyhashes (
    keyhash TEXT PRIMARY KEY,
    count INTEGER,
    UNIQUE(keyhash)
);
```

**Purpose**: Detect duplicate rows for compound keys

**Hash Strategy**:
1. Concatenate key column values with separator
2. Handle NULLs with special marker (e.g., `__NULL__`)
3. SHA-256 hash of concatenated string
4. Store hash and count

**Example**:

For key `[first_name, last_name, dob]`, row `['John', 'Doe', '1990-01-01']`:

```
Concatenated: John||Doe||1990-01-01
Hash: <sha256>
```

For row with NULL: `['John', NULL, '1990-01-01']`:

```
Concatenated: John||__NULL__||1990-01-01
Hash: <sha256>
```

---

## File Artifacts

### Profile JSON (`/data/outputs/{run_id}/profile.json`)

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "file": {
    "rows": 1000000,
    "columns": 15,
    "delimiter": "|",
    "crlf_detected": true,
    "header": ["col1", "col2", "col3"]
  },
  "errors": [
    {
      "code": "E_NUMERIC_FORMAT",
      "message": "Non-numeric values in numeric column",
      "count": 12,
      "column": "amount"
    }
  ],
  "warnings": [
    {
      "code": "W_DATE_RANGE",
      "message": "Dates outside expected range",
      "count": 3,
      "column": "transaction_date"
    }
  ],
  "columns": [
    {
      "name": "transaction_id",
      "inferred_type": "code",
      "null_pct": 0.0,
      "distinct_count": 1000000,
      "duplicate_count": 0,
      "length": {
        "min": 8,
        "max": 8,
        "avg": 8.0
      },
      "top_values": [
        {"value": "TXN00001", "count": 1}
      ]
    }
  ],
  "candidate_keys": [
    {
      "columns": ["transaction_id"],
      "distinct_ratio": 1.0,
      "null_ratio_sum": 0.0,
      "score": 1.0
    }
  ],
  "processing": {
    "started_at": "2024-01-15T10:00:00Z",
    "completed_at": "2024-01-15T10:05:30Z",
    "duration_seconds": 330,
    "bytes_read": 1073741824,
    "rows_read": 1000000,
    "avg_bytes_per_row": 1073
  }
}
```

### Metrics CSV (`/data/outputs/{run_id}/metrics.csv`)

```csv
column_name,inferred_type,null_pct,distinct_count,length_min,length_max,length_avg,numeric_min,numeric_max,numeric_mean
transaction_id,code,0.0,1000000,8,8,8.0,,,
amount,money,0.1,50000,4,10,7.2,0.01,9999.99,245.67
transaction_date,date,0.0,365,10,10,10.0,,,
```

### Audit Log (`/data/outputs/{run_id}/audit.log.json`)

```json
[
  {
    "timestamp": "2024-01-15T10:00:00Z",
    "event": "run_created",
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "delimiter": "|",
    "quoted": true,
    "expect_crlf": true
  },
  {
    "timestamp": "2024-01-15T10:00:01Z",
    "event": "file_uploaded",
    "filename": "transactions.csv.gz",
    "sha256": "abcd1234...",
    "bytes": 1073741824,
    "compression": "gzip"
  },
  {
    "timestamp": "2024-01-15T10:00:02Z",
    "event": "processing_started",
    "expected_rows": "unknown"
  },
  {
    "timestamp": "2024-01-15T10:05:30Z",
    "event": "processing_completed",
    "rows_processed": 1000000,
    "bytes_processed": 1073741824,
    "errors": 12,
    "warnings": 3,
    "duration_seconds": 328
  },
  {
    "timestamp": "2024-01-15T10:06:00Z",
    "event": "keys_confirmed",
    "keys": [["transaction_id"], ["email"]],
    "duplicate_detection_started": true
  },
  {
    "timestamp": "2024-01-15T10:06:30Z",
    "event": "duplicate_detection_completed",
    "keys_checked": 2,
    "total_duplicates": 0
  }
]
```

---

## Data Retention

### Automatic Cleanup

Configurable retention policy for old runs:

```env
# .env
RETENTION_DAYS=30        # Keep runs from last 30 days
RETENTION_RUN_COUNT=100  # Or keep last 100 runs
RETENTION_POLICY=days    # Which policy to use (days or count)
```

### Manual Cleanup

Remove old run data:

```bash
# Remove run from database and disk
DELETE FROM runs WHERE run_id = '550e8400-...';
DELETE FROM columns WHERE run_id = '550e8400-...';
DELETE FROM errors WHERE run_id = '550e8400-...';
# And manually remove directories:
rm -rf /data/work/runs/550e8400-...
rm -rf /data/outputs/550e8400-...
```

---

## Performance Considerations

### Indexing Strategy

1. **Primary Keys**: Used for direct lookups (run_id)
2. **Foreign Keys**: Used for joins and filtering
3. **State Index**: Fast filtering by run status
4. **Score Index**: Fast sorting of candidate keys
5. **Distinct Index**: Fast top-10 queries

### Query Optimization

```sql
-- Get all columns for a run (fast with index)
SELECT * FROM columns WHERE run_id = ?;

-- Get candidate keys sorted by score (fast with index)
SELECT * FROM candidate_keys WHERE run_id = ?
ORDER BY score DESC LIMIT 5;

-- Count distinct values (uses index on col_n_values)
SELECT COUNT(*) FROM col_0_values;

-- Find duplicates efficiently
SELECT keyhash, count FROM keyhashes WHERE count > 1;
```

### Disk Space Management

For a 3 GiB file with 1M rows:

- **Main DB** (profiler.db): ~10 MB
- **Per-Run DB** (temp.db): 100-500 MB (depends on distinct values)
- **Output Files** (profile.json + metrics.csv): 5-50 MB

Total per run: ~150-600 MB

Recommendation: 10+ GiB available in `/data/work` for concurrent runs

---

## Future Enhancements

### v2 Features

1. **Partitioned Indices** - For very large datasets
2. **Query Statistics** - For optimization
3. **Row-Level Error Tracking** - Link errors to specific rows
4. **Incremental Updates** - Re-profile subset of columns
5. **Schema Versioning** - Support migrations

### Migration Strategy

Database migrations stored in `/migrations/` directory:

```
migrations/
  001_initial_schema.sql
  002_add_audit_log.sql
  003_add_candidate_keys.sql
```

Run on startup:

```python
def apply_migrations(db):
    current_version = get_schema_version(db)
    for version in get_pending_migrations(current_version):
        execute_migration(db, version)
```

---

## Documentation References

- See `API.md` for how data is exposed via API
- See `ERROR_CODES.md` for error details
- See `TYPE_INFERENCE.md` for type storage
- See `DEVELOPMENT.md` for query examples
