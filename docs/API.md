# API Documentation

Complete reference for the VQ8 Data Profiler REST API.

## Base URL

```
http://localhost:8000
```

## OpenAPI / Swagger Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Authentication

**v1**: No authentication required (local deployment only)

**v2+**: OAuth2/OIDC via VisiQuateID (planned)

## Common Response Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Request accepted for processing |
| 400 | Bad Request | Invalid input parameters |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists or conflicting state |
| 500 | Internal Server Error | Server error occurred |

## Error Response Format

All errors return a consistent JSON structure:

```json
{
  "detail": "Human-readable error message",
  "error_code": "E_SPECIFIC_ERROR",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Endpoints

### Health Check

Check API health and readiness.

#### `GET /healthz`

**Description**: Health check endpoint for monitoring.

**Response**: `200 OK`

```json
{
  "status": "ok",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

**Example**:
```bash
curl http://localhost:8000/healthz
```

---

### Create Run

Create a new profiling run.

#### `POST /runs`

**Description**: Initialize a new profiling run with configuration.

**Request Body**:
```json
{
  "delimiter": "|",
  "quoted": true,
  "expect_crlf": true
}
```

**Parameters**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| delimiter | string | Yes | - | Delimiter character: `\|` or `,` |
| quoted | boolean | No | true | Whether fields use double-quote escaping |
| expect_crlf | boolean | No | true | Whether to expect CRLF line endings |

**Response**: `201 Created`

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "queued",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "delimiter": "|",
    "quoted": true,
    "expect_crlf": true
  }'
```

**Error Responses**:
- `400`: Invalid delimiter or parameters

---

### Upload File

Upload a file for profiling.

#### `POST /runs/{run_id}/upload`

**Description**: Upload a CSV/TXT file (or gzipped version) for profiling.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID from `/runs` endpoint |

**Request**: `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | binary | Yes | File to upload (`.txt`, `.csv`, `.txt.gz`, `.csv.gz`) |

**Response**: `202 Accepted`

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "processing",
  "message": "File uploaded and processing started"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/runs/{run_id}/upload \
  -F "file=@/path/to/data.csv"
```

**Error Responses**:
- `400`: Invalid file format or encoding
- `404`: Run ID not found
- `409`: File already uploaded for this run

---

### Get Run Status

Check the current status of a profiling run.

#### `GET /runs/{run_id}/status`

**Description**: Retrieve current state, progress, and any errors/warnings.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID to check |

**Response**: `200 OK`

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "processing",
  "progress_pct": 45.2,
  "created_at": "2025-01-15T10:30:00Z",
  "started_at": "2025-01-15T10:30:15Z",
  "completed_at": null,
  "warnings": [
    {
      "code": "W_DATE_RANGE",
      "message": "Date outside expected range (1900-2026)",
      "count": 7
    }
  ],
  "errors": [
    {
      "code": "E_NUMERIC_FORMAT",
      "message": "Invalid numeric format (contains symbols)",
      "count": 42
    }
  ]
}
```

**State Values**:
| State | Description |
|-------|-------------|
| queued | Run created, waiting for file upload |
| processing | File uploaded and being processed |
| completed | Processing completed successfully |
| failed | Processing failed due to catastrophic error |

**Example**:
```bash
curl http://localhost:8000/runs/{run_id}/status
```

**Polling Recommendation**:
Poll every 2-5 seconds while `state` is `processing`.

**Error Responses**:
- `404`: Run ID not found

---

### Get Profile

Retrieve the complete profiling results.

#### `GET /runs/{run_id}/profile`

**Description**: Get full profile JSON with all metrics and statistics.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID to retrieve |

**Response**: `200 OK`

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "file": {
    "rows": 500000,
    "columns": 50,
    "delimiter": "|",
    "crlf_detected": true,
    "header": ["id", "name", "age", "city", ...]
  },
  "errors": [
    {
      "code": "E_NUMERIC_FORMAT",
      "message": "Invalid numeric format",
      "count": 42
    }
  ],
  "warnings": [
    {
      "code": "W_DATE_RANGE",
      "message": "Date out of range",
      "count": 7
    }
  ],
  "columns": [
    {
      "name": "id",
      "inferred_type": "numeric",
      "null_pct": 0.0,
      "distinct_count": 500000,
      "top_values": [],
      "length": {
        "min": 1,
        "max": 6,
        "avg": 4.2
      },
      "numeric_stats": {
        "min": 1,
        "max": 500000,
        "mean": 250000.5,
        "median": 250000,
        "stddev": 144337.5,
        "quantiles": {
          "p1": 5000,
          "p5": 25000,
          "p25": 125000,
          "p50": 250000,
          "p75": 375000,
          "p95": 475000,
          "p99": 495000
        },
        "gaussian_pvalue": 0.85
      }
    },
    {
      "name": "purchase_date",
      "inferred_type": "date",
      "null_pct": 2.3,
      "distinct_count": 1825,
      "top_values": [
        {"value": "20250115", "count": 452},
        {"value": "20250114", "count": 448}
      ],
      "date_stats": {
        "detected_format": "YYYYMMDD",
        "min": "2020-01-01",
        "max": "2025-01-15",
        "out_of_range_count": 0
      }
    },
    {
      "name": "amount",
      "inferred_type": "money",
      "null_pct": 0.1,
      "distinct_count": 125000,
      "numeric_stats": {
        "min": 0.00,
        "max": 9999.99,
        "mean": 342.89,
        "median": 298.50,
        "stddev": 187.23,
        "quantiles": {
          "p25": 150.00,
          "p50": 298.50,
          "p75": 450.00
        }
      },
      "money_rules": {
        "two_decimal_ok": true,
        "disallowed_symbols_found": false,
        "violations_count": 0
      }
    }
  ],
  "candidate_keys": [
    {
      "columns": ["id"],
      "distinct_ratio": 1.0,
      "null_ratio_sum": 0.0,
      "score": 1.0
    },
    {
      "columns": ["order_date", "customer_id"],
      "distinct_ratio": 0.998,
      "null_ratio_sum": 0.003,
      "score": 0.995
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8000/runs/{run_id}/profile > profile.json
```

**Error Responses**:
- `404`: Run ID not found
- `409`: Processing not complete yet

---

### Download Metrics CSV

Download per-column metrics as CSV.

#### `GET /runs/{run_id}/metrics.csv`

**Description**: Export column metrics in CSV format for spreadsheet analysis.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID to download |

**Response**: `200 OK`

**Content-Type**: `text/csv`

**CSV Format**:
```csv
column_name,type,row_count,null_count,null_pct,distinct_count,min,max,mean,median,stddev
id,numeric,500000,0,0.0,500000,1,500000,250000.5,250000,144337.5
name,alpha,500000,1250,0.25,489000,,,,,,
age,numeric,500000,500,0.1,100,18,95,42.5,41,18.2
amount,money,500000,50,0.01,125000,0.00,9999.99,342.89,298.50,187.23
purchase_date,date,500000,11500,2.3,1825,2020-01-01,2025-01-15,,,
```

**Example**:
```bash
curl http://localhost:8000/runs/{run_id}/metrics.csv > metrics.csv
```

**Error Responses**:
- `404`: Run ID not found
- `409`: Processing not complete yet

---

### Download HTML Report

Generate and download interactive HTML report.

#### `GET /runs/{run_id}/report.html`

**Description**: Generate a self-contained HTML report with visualizations.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID to download |

**Response**: `200 OK`

**Content-Type**: `text/html`

**Features**:
- Interactive tables (sortable, filterable)
- Charts and visualizations
- Dark mode compatible
- Fully self-contained (no external dependencies)
- Printable format

**Example**:
```bash
curl http://localhost:8000/runs/{run_id}/report.html > report.html
open report.html  # macOS
```

**Error Responses**:
- `404`: Run ID not found
- `409`: Processing not complete yet

---

### Get Candidate Keys

Retrieve suggested uniqueness keys.

#### `GET /runs/{run_id}/candidate-keys`

**Description**: Get automatically suggested single and compound candidate keys.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID to query |

**Response**: `200 OK`

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "suggestions": [
    {
      "columns": ["id"],
      "distinct_ratio": 1.0,
      "null_ratio_sum": 0.0,
      "score": 1.0,
      "type": "single"
    },
    {
      "columns": ["order_date", "customer_id"],
      "distinct_ratio": 0.998,
      "null_ratio_sum": 0.003,
      "score": 0.995,
      "type": "compound"
    },
    {
      "columns": ["email"],
      "distinct_ratio": 0.997,
      "null_ratio_sum": 0.002,
      "score": 0.995,
      "type": "single"
    }
  ]
}
```

**Scoring Formula**:
```
score = (distinct_ratio * (1 - null_ratio_sum)) / (1 + invalid_count)
```

**Interpretation**:
- **Score ≥ 0.99**: Excellent candidate (likely unique)
- **Score 0.95-0.99**: Good candidate (few duplicates)
- **Score < 0.95**: May have many duplicates

**Example**:
```bash
curl http://localhost:8000/runs/{run_id}/candidate-keys
```

**Error Responses**:
- `404`: Run ID not found
- `409`: Processing not complete yet

---

### Confirm Candidate Keys

Confirm selected keys and trigger duplicate detection.

#### `POST /runs/{run_id}/confirm-keys`

**Description**: Confirm one or more candidate keys to perform exact duplicate detection.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| run_id | UUID | Run ID to update |

**Request Body**:
```json
{
  "keys": [
    ["id"],
    ["order_date", "customer_id"]
  ]
}
```

**Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| keys | array | Yes | Array of key column arrays |

**Response**: `202 Accepted`

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Duplicate detection started",
  "confirmed_keys": [
    ["id"],
    ["order_date", "customer_id"]
  ]
}
```

**Processing**:
The system will:
1. Create hash tables for each confirmed key
2. Scan all rows and compute key hashes
3. Count duplicate hashes
4. Update profile with duplicate counts

**Checking Results**:
Poll `/runs/{run_id}/status` until state returns to `completed`, then retrieve updated `/runs/{run_id}/profile` with duplicate counts.

**Example**:
```bash
curl -X POST http://localhost:8000/runs/{run_id}/confirm-keys \
  -H "Content-Type: application/json" \
  -d '{
    "keys": [
      ["id"],
      ["order_date", "customer_id"]
    ]
  }'
```

**Error Responses**:
- `400`: Invalid key columns (not in dataset)
- `404`: Run ID not found
- `409`: Processing not complete yet or already confirmed

---

## Data Models

### ColumnType Enum

```
alpha       - General string data
varchar     - Variable-length string
code        - Dictionary-like codes
numeric     - Numbers with optional decimal
money       - Exactly 2 decimal places
date        - Consistent date format
mixed       - Multiple types detected (error condition)
unknown     - Cannot determine type
```

### ColumnProfile Object

```json
{
  "name": "string",
  "inferred_type": "ColumnType",
  "null_pct": "float",
  "distinct_count": "integer",
  "top_values": [
    {
      "value": "string",
      "count": "integer"
    }
  ],
  "length": {
    "min": "integer",
    "max": "integer",
    "avg": "float"
  },
  "numeric_stats": {
    "min": "float",
    "max": "float",
    "mean": "float",
    "median": "float",
    "stddev": "float",
    "quantiles": {
      "p1": "float",
      "p5": "float",
      "p25": "float",
      "p50": "float",
      "p75": "float",
      "p95": "float",
      "p99": "float"
    },
    "gaussian_pvalue": "float"
  },
  "money_rules": {
    "two_decimal_ok": "boolean",
    "disallowed_symbols_found": "boolean",
    "violations_count": "integer"
  },
  "date_stats": {
    "detected_format": "string",
    "min": "string (ISO date)",
    "max": "string (ISO date)",
    "out_of_range_count": "integer"
  }
}
```

### ErrorDetail Object

```json
{
  "code": "string",
  "message": "string",
  "count": "integer"
}
```

### CandidateKey Object

```json
{
  "columns": ["string"],
  "distinct_ratio": "float",
  "null_ratio_sum": "float",
  "score": "float"
}
```

## Rate Limiting

**v1**: No rate limiting (local deployment)

**v2+**: Planned rate limits (per-user):
- 10 concurrent runs
- 100 runs per day
- 1 TB total upload per month

## Webhooks

**v1**: Not supported

**v2+**: Webhook notifications for:
- Processing completed
- Processing failed
- Duplicate detection completed

## Pagination

**v1**: Not applicable (single-file processing)

**v2+**: Planned pagination for:
- Run history listing
- Multi-file batch results

## Code Examples

### Python

```python
import requests
import time

# Create run
response = requests.post("http://localhost:8000/runs", json={
    "delimiter": "|",
    "quoted": True,
    "expect_crlf": True
})
run_id = response.json()["run_id"]

# Upload file
with open("data.csv", "rb") as f:
    requests.post(
        f"http://localhost:8000/runs/{run_id}/upload",
        files={"file": f}
    )

# Poll status
while True:
    response = requests.get(f"http://localhost:8000/runs/{run_id}/status")
    status = response.json()

    if status["state"] == "completed":
        break
    elif status["state"] == "failed":
        print("Processing failed:", status["errors"])
        break

    print(f"Progress: {status['progress_pct']:.1f}%")
    time.sleep(2)

# Get results
profile = requests.get(f"http://localhost:8000/runs/{run_id}/profile").json()
print(f"Profiled {profile['file']['rows']} rows with {profile['file']['columns']} columns")
```

### JavaScript

```javascript
// Create run
const createResponse = await fetch("http://localhost:8000/runs", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    delimiter: "|",
    quoted: true,
    expect_crlf: true
  })
});
const { run_id } = await createResponse.json();

// Upload file
const formData = new FormData();
formData.append("file", fileInput.files[0]);

await fetch(`http://localhost:8000/runs/${run_id}/upload`, {
  method: "POST",
  body: formData
});

// Poll status
const pollStatus = async () => {
  const response = await fetch(`http://localhost:8000/runs/${run_id}/status`);
  const status = await response.json();

  if (status.state === "completed") {
    // Get profile
    const profile = await fetch(`http://localhost:8000/runs/${run_id}/profile`);
    return await profile.json();
  } else if (status.state === "failed") {
    throw new Error("Processing failed");
  } else {
    // Continue polling
    setTimeout(pollStatus, 2000);
  }
};

const profile = await pollStatus();
```

### cURL

```bash
#!/bin/bash

# Create run and capture run_id
RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"delimiter":"|","quoted":true}' \
  | jq -r '.run_id')

echo "Created run: $RUN_ID"

# Upload file
curl -X POST http://localhost:8000/runs/$RUN_ID/upload \
  -F "file=@data.csv"

# Poll status
while true; do
  STATE=$(curl -s http://localhost:8000/runs/$RUN_ID/status | jq -r '.state')

  if [ "$STATE" = "completed" ]; then
    echo "Processing completed"
    break
  elif [ "$STATE" = "failed" ]; then
    echo "Processing failed"
    exit 1
  fi

  PROGRESS=$(curl -s http://localhost:8000/runs/$RUN_ID/status | jq -r '.progress_pct')
  echo "Progress: $PROGRESS%"

  sleep 2
done

# Download results
curl http://localhost:8000/runs/$RUN_ID/profile > profile.json
curl http://localhost:8000/runs/$RUN_ID/metrics.csv > metrics.csv
curl http://localhost:8000/runs/$RUN_ID/report.html > report.html

echo "Results downloaded"
```

## Versioning

API version is included in responses but not in URL path (v1).

**Current Version**: 1.0.0

**Version Header**:
```
X-API-Version: 1.0.0
```

**Backward Compatibility**:
- Breaking changes will increment major version
- New fields added will not break existing clients
- Deprecated fields will include deprecation warnings

## Support

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Architecture**: See `ARCHITECTURE.md`
- **User Guide**: See `USER_GUIDE.md`
- **Developer Guide**: See `DEVELOPER_GUIDE.md`
