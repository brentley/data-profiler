# Data Profiler API Documentation

Complete reference for all API endpoints, request/response models, and error handling.

## Base URL

```
http://localhost:8000  (development)
```

## Authentication

v1 has no authentication. Future versions will use OIDC via VisiQuateID.

## Endpoints

### Health Check

**GET** `/healthz`

Check API health and readiness.

**Response**

```json
{
  "status": "ok",
  "service": "data-profiler",
  "version": "1.0.0"
}
```

**Status Codes**
- `200 OK` - Service is healthy

---

### Create Profiling Run

**POST** `/runs`

Create a new profiling run. This initializes metadata but does not process any data yet.

**Request Body**

```json
{
  "delimiter": "|",
  "quoted": true,
  "expect_crlf": true
}
```

**Parameters**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| delimiter | string | Yes | - | Column delimiter: `"|"` or `","` |
| quoted | boolean | No | true | Whether to expect CSV-style quoting |
| expect_crlf | boolean | No | true | Whether to expect CRLF line endings |

**Response**

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "queued",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Status Codes**
- `201 Created` - Run successfully created
- `400 Bad Request` - Invalid parameters (invalid delimiter, etc.)

**Example**

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"delimiter": "|", "quoted": true, "expect_crlf": true}'
```

---

### Upload File

**POST** `/runs/{run_id}/upload`

Upload a file to profile. File can be `.txt`, `.csv`, or gzip-compressed variants (`.txt.gz`, `.csv.gz`).

**URL Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID from create endpoint |

**Request Body**

Multipart form data with single file:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | binary | Yes | CSV/TXT file or gzip-compressed variant |

**Response**

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "processing",
  "progress_pct": 0,
  "message": "File received and queued for processing"
}
```

**Status Codes**
- `202 Accepted` - File accepted and queued for processing
- `400 Bad Request` - Invalid file format or encoding
- `413 Payload Too Large` - File exceeds size limits
- `404 Not Found` - Run ID not found

**Example**

```bash
curl -X POST http://localhost:8000/runs/550e8400-e29b-41d4-a716-446655440000/upload \
  -F "file=@data.csv"
```

---

### Get Run Status

**GET** `/runs/{run_id}/status`

Get current processing status and any errors/warnings accumulated so far.

**URL Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID |

**Response**

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "processing",
  "progress_pct": 45,
  "errors": [
    {
      "code": "E_NUMERIC_FORMAT",
      "message": "Non-numeric values in numeric column",
      "count": 12
    }
  ],
  "warnings": [
    {
      "code": "W_DATE_RANGE",
      "message": "Dates outside expected range",
      "count": 3
    }
  ]
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| run_id | UUID | Run identifier |
| state | string | One of: `queued`, `processing`, `completed`, `failed` |
| progress_pct | number | Percentage of file processed (0-100) |
| errors | array | Catastrophic and non-catastrophic errors found |
| warnings | array | Non-catastrophic issues (processing continues) |

**State Descriptions**

- `queued` - Waiting to start processing
- `processing` - File is being processed
- `completed` - Processing finished successfully
- `failed` - Processing encountered a catastrophic error and stopped

**Status Codes**
- `200 OK` - Status retrieved
- `404 Not Found` - Run ID not found

**Example**

```bash
curl http://localhost:8000/runs/550e8400-e29b-41d4-a716-446655440000/status
```

---

### Get Full Profile

**GET** `/runs/{run_id}/profile`

Retrieve complete profiling results as JSON.

**URL Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID |

**Response**

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "file": {
    "rows": 1000000,
    "columns": 15,
    "delimiter": "|",
    "crlf_detected": true,
    "header": ["id", "name", "amount", "date"]
  },
  "errors": [...],
  "warnings": [...],
  "columns": [
    {
      "name": "id",
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
        {"value": "ID000001", "count": 1},
        {"value": "ID000002", "count": 1}
      ]
    }
  ],
  "candidate_keys": [
    {
      "columns": ["id"],
      "distinct_ratio": 1.0,
      "null_ratio_sum": 0.0,
      "score": 1.0
    }
  ]
}
```

**Full Schema Definition**

See `ColumnProfile` schema below for detailed field descriptions.

**Status Codes**
- `200 OK` - Profile retrieved
- `202 Accepted` - Profile still being computed (try again)
- `404 Not Found` - Run ID not found
- `500 Internal Server Error` - Profile generation failed

**Example**

```bash
curl http://localhost:8000/runs/550e8400-e29b-41d4-a716-446655440000/profile
```

---

### Get Metrics CSV

**GET** `/runs/{run_id}/metrics.csv`

Download profiling metrics as CSV (one row per column).

**URL Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID |

**Response Format**

CSV with the following columns:

```
column_name,inferred_type,null_pct,distinct_count,duplicate_count,length_min,length_max,length_avg,numeric_min,numeric_max,numeric_mean,numeric_median,numeric_stddev,money_violations,date_format,out_of_range_dates
```

**Status Codes**
- `200 OK` - CSV retrieved
- `404 Not Found` - Run ID not found

**Example**

```bash
curl http://localhost:8000/runs/550e8400-e29b-41d4-a716-446655440000/metrics.csv \
  -o metrics.csv
```

---

### Get HTML Report

**GET** `/runs/{run_id}/report.html`

Generate and retrieve an interactive HTML report.

**URL Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID |

**Response**

HTML document with embedded CSS and JavaScript for interactive exploration.

**Status Codes**
- `200 OK` - HTML report retrieved
- `404 Not Found` - Run ID not found

**Example**

```bash
curl http://localhost:8000/runs/550e8400-e29b-41d4-a716-446655440000/report.html \
  -o report.html && open report.html
```

---

### Get Candidate Keys

**GET** `/runs/{run_id}/candidate-keys`

Retrieve suggested uniqueness keys for the dataset.

**URL Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID |

**Response**

```json
{
  "suggestions": [
    {
      "columns": ["id"],
      "distinct_ratio": 1.0,
      "null_ratio_sum": 0.0,
      "score": 1.0
    },
    {
      "columns": ["email"],
      "distinct_ratio": 0.99,
      "null_ratio_sum": 0.001,
      "score": 0.989
    },
    {
      "columns": ["first_name", "last_name", "dob"],
      "distinct_ratio": 0.98,
      "null_ratio_sum": 0.05,
      "score": 0.931
    }
  ]
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| suggestions | array | Array of suggested key candidates (up to 5) |
| columns | array | Column names forming the candidate key |
| distinct_ratio | number | Ratio of distinct values to total rows |
| null_ratio_sum | number | Sum of null ratios for columns in key |
| score | number | Composite score: `distinct_ratio * (1 - null_ratio_sum)` |

**Scoring Logic**

Keys are ranked by:
1. Distinct ratio (higher is better)
2. Lower null ratio (more complete data is better)
3. Fewer invalid values in key columns

**Status Codes**
- `200 OK` - Suggestions retrieved
- `404 Not Found` - Run ID not found
- `202 Accepted` - Suggestions still being computed

**Example**

```bash
curl http://localhost:8000/runs/550e8400-e29b-41d4-a716-446655440000/candidate-keys
```

---

### Confirm Keys

**POST** `/runs/{run_id}/confirm-keys`

Confirm selected candidate keys and trigger exact duplicate detection.

**URL Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID |

**Request Body**

```json
{
  "keys": [
    ["id"],
    ["email"]
  ]
}
```

**Parameters**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| keys | array of arrays | Yes | Array of key column combinations to check |

Each element in `keys` is an array of column names forming a composite key.

**Response**

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "processing",
  "message": "Duplicate detection in progress for 2 key combinations"
}
```

**Status Codes**
- `202 Accepted` - Duplicate detection queued
- `400 Bad Request` - Invalid key specifications
- `404 Not Found` - Run ID not found

**Processing**

After confirmation:
1. Duplicate detection runs for each key combination
2. Results are added to profile (via GET /profile)
3. Status endpoint shows progress

**Example**

```bash
curl -X POST http://localhost:8000/runs/550e8400-e29b-41d4-a716-446655440000/confirm-keys \
  -H "Content-Type: application/json" \
  -d '{"keys": [["id"], ["email"]]}'
```

---

## Data Models

### Error Object

```json
{
  "code": "E_NUMERIC_FORMAT",
  "message": "Non-numeric values found in numeric column",
  "count": 25
}
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| code | string | Error code (see ERROR_CODES.md) |
| message | string | Human-readable description |
| count | integer | Number of occurrences |

### ColumnProfile Object

```json
{
  "name": "transaction_amount",
  "inferred_type": "money",
  "null_pct": 0.5,
  "distinct_count": 50000,
  "duplicate_count": 100,
  "length": {
    "min": 4,
    "max": 10,
    "avg": 7.2
  },
  "top_values": [
    {"value": "99.99", "count": 500},
    {"value": "50.00", "count": 400}
  ],
  "numeric_stats": {
    "min": 0.01,
    "max": 9999.99,
    "mean": 245.67,
    "median": 125.50,
    "stddev": 500.23,
    "quantiles": {
      "p1": 0.10,
      "p5": 1.00,
      "p25": 50.00,
      "p50": 125.50,
      "p75": 300.00,
      "p95": 900.00,
      "p99": 2000.00
    },
    "gaussian_pvalue": 0.0001,
    "histogram": {
      "0-100": 1500,
      "100-200": 1200,
      "200-500": 2000,
      "500-1000": 1500,
      "1000+": 800
    }
  },
  "money_rules": {
    "two_decimal_ok": true,
    "disallowed_symbols_found": false,
    "violations_count": 0
  },
  "date_stats": {
    "detected_format": "YYYY-MM-DD",
    "min": "2020-01-01",
    "max": "2024-12-31",
    "out_of_range_count": 0,
    "distribution_by_month": {
      "2024-01": 5000,
      "2024-02": 4500
    }
  }
}
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| name | string | Column name from header |
| inferred_type | string | Detected type: alpha, varchar, code, numeric, money, date, mixed, unknown |
| null_pct | number | Percentage of null/empty values (0-100) |
| distinct_count | integer | Number of unique values |
| duplicate_count | integer | Total duplicate occurrences (if keys confirmed) |
| length | object | String length statistics (min, max, avg) |
| top_values | array | Top 10 values with occurrence counts |
| numeric_stats | object | Statistics for numeric/money columns (optional) |
| money_rules | object | Money format validation results (optional) |
| date_stats | object | Date format analysis (optional) |

### Profile Object

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
  "errors": [],
  "warnings": [],
  "columns": [],
  "candidate_keys": []
}
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| run_id | UUID | Run identifier |
| file | object | File-level metadata |
| errors | array | Error objects |
| warnings | array | Warning objects |
| columns | array | Array of ColumnProfile objects |
| candidate_keys | array | Suggested uniqueness keys |

---

## Error Codes

See `ERROR_CODES.md` for complete reference including:
- Catastrophic errors (E_*)
- Non-catastrophic errors (E_*)
- Warnings (W_*)

---

## Rate Limiting

No rate limiting in v1. Future versions may implement per-user limits.

---

## Pagination

No pagination for v1. Profile JSON contains complete results.

Future versions may implement:
- `limit` and `offset` query parameters for large profiles
- Streaming JSON responses for profiles > 100MB

---

## Versioning

API version: `1.0.0`

Version info available at `GET /healthz` response.

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Profile retrieved successfully |
| 201 | Created | New run created |
| 202 | Accepted | File upload or processing accepted |
| 400 | Bad Request | Invalid delimiter or file format |
| 404 | Not Found | Run ID not found |
| 413 | Payload Too Large | File exceeds size limit |
| 500 | Internal Server Error | Processing failure |
| 503 | Service Unavailable | API overloaded or restarting |

### Error Response Format

```json
{
  "detail": "Run not found",
  "error_code": "E_RUN_NOT_FOUND",
  "run_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Examples

### Complete Workflow

```bash
# 1. Create run
RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"delimiter": "|"}' | jq -r '.run_id')

# 2. Upload file
curl -X POST http://localhost:8000/runs/$RUN_ID/upload \
  -F "file=@data.csv"

# 3. Check status (poll until complete)
curl http://localhost:8000/runs/$RUN_ID/status

# 4. Get candidate keys
curl http://localhost:8000/runs/$RUN_ID/candidate-keys

# 5. Confirm keys
curl -X POST http://localhost:8000/runs/$RUN_ID/confirm-keys \
  -H "Content-Type: application/json" \
  -d '{"keys": [["id"]]}'

# 6. Download artifacts
curl http://localhost:8000/runs/$RUN_ID/profile > profile.json
curl http://localhost:8000/runs/$RUN_ID/metrics.csv > metrics.csv
curl http://localhost:8000/runs/$RUN_ID/report.html > report.html
```

---

## Limits

### File Size

- **Maximum**: No hard limit (limited by disk space)
- **Recommended**: Test with 3-5 GiB files
- **Spill Directory**: Must have at least 2x file size available

### Columns

- **Maximum**: 500 columns (tested)
- **Minimum**: 1 column
- **Special handling**: Files with 250+ columns require more spill space

### Values

- **Max string length**: 1 MB per value (enforced)
- **Max distinct values per column**: Limited by disk space

---

## Webhooks

Not implemented in v1. Consider for v2 if needing async notifications.

---

## OpenAPI Specification

Auto-generated OpenAPI 3.1 spec available at `/openapi.json` when API is running.

View interactive documentation at `/docs` and `/redoc`.
