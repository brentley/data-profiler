# Architecture Documentation

## Overview

The VQ8 Data Profiler is built as a modern, streaming-based data profiling system designed to handle large files (3+ GiB) with exact metrics computation on commodity hardware. This document describes the system architecture, component interactions, and design decisions.

## System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Client Browser                        │
│                   (React + Vite + Tailwind)                  │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP/REST
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                      API Server (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Request Routing Layer                    │   │
│  │        (/runs, /upload, /profile, /status)           │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                           │                                   │
│  ┌────────────────────────▼─────────────────────────────┐   │
│  │         Streaming Ingestion Pipeline                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │   Reader   │→ │   Parser   │→ │  Profilers │     │   │
│  │  │ (UTF-8/GZ) │  │ (CSV/Quote)│  │ (Stats/Type)│     │   │
│  │  └────────────┘  └────────────┘  └──────┬─────┘     │   │
│  └────────────────────────────────────────│─────────────┘   │
│                                            │                  │
│  ┌────────────────────────────────────────▼─────────────┐   │
│  │              Storage & Indexing Layer                 │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │  SQLite    │  │ Temp Spill │  │  Outputs   │     │   │
│  │  │  Indices   │  │   Files    │  │ (JSON/CSV) │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘     │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    Persistent Storage                         │
│  /data/work/              /data/outputs/                     │
│  ├── runs/                ├── {run_id}/                      │
│  │   └── {run_id}/        │   ├── profile.json              │
│  │       ├── *.sqlite     │   ├── metrics.csv               │
│  │       └── temp_*       │   ├── report.html               │
│                            │   └── audit.log.json            │
└──────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend (Web UI)

**Technology Stack:**
- React 18 with TypeScript
- Vite (build tool and dev server)
- Tailwind CSS (styling)
- Dark mode support

**Key Components:**

#### Upload Flow
- `UploadForm.tsx`: File selection and configuration
  - File type validation (`.txt`, `.csv`, `.gz`)
  - Delimiter selection (`|` or `,`)
  - Quote handling toggle
  - CRLF expectation setting

#### Monitoring
- `RunStatus.tsx`: Real-time progress tracking
  - WebSocket or polling for updates
  - Progress bar (0-100%)
  - Toast notifications for errors/warnings
  - State visualization (queued → processing → completed/failed)

#### Results Dashboard
- `ResultsDashboard.tsx`: Main results view
  - File summary card (rows, columns, delimiter, CRLF detection)
  - Error roll-up table (grouped by error code)
  - Candidate keys section
  - Download buttons (JSON, CSV, HTML)

- `ColumnCard.tsx`: Per-column detailed view
  - Type badge with color coding
  - Null percentage gauge
  - Distinct count
  - Top 10 values chart
  - Type-specific statistics (numeric/money/date)

- `CandidateKeys.tsx`: Key management interface
  - Suggested keys with scoring
  - Single vs. compound key indicators
  - Confirmation checkboxes
  - Duplicate detection trigger

#### Error Display
- `ErrorRollup.tsx`: Aggregated error visualization
  - Error code with description
  - Count per error type
  - Color coding (catastrophic vs. non-catastrophic)
  - Drill-down capability

**State Management:**
- React hooks for local state
- Context API for global state (run metadata, current run ID)
- No Redux (keeping it simple for v1)

### 2. Backend API (FastAPI)

**Technology Stack:**
- Python 3.11+
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Pydantic (data validation)
- SQLite3 (indexing and storage)

**Architecture Layers:**

#### Router Layer (`routers/`)
Handles HTTP request/response:
- `runs.py`: Run lifecycle management
  - POST `/runs` - Create new run
  - GET `/runs/{run_id}/status` - Check progress
  - GET `/runs/{run_id}/profile` - Retrieve results
  - GET `/runs/{run_id}/candidate-keys` - Get suggestions
  - POST `/runs/{run_id}/confirm-keys` - Trigger duplicate detection

- `upload.py`: File upload handling
  - POST `/runs/{run_id}/upload` - Multipart file upload
  - Streaming upload to avoid memory exhaustion
  - Immediate validation (UTF-8, gzip detection)

- `artifacts.py`: Report generation
  - GET `/runs/{run_id}/metrics.csv` - Metrics table
  - GET `/runs/{run_id}/report.html` - HTML report
  - Artifact caching for repeated downloads

#### Service Layer (`services/`)
Business logic and processing:

**`ingest.py`**: Streaming ingestion
```python
class StreamingIngestor:
    def __init__(self, run_id, config):
        self.reader = UTF8Reader()
        self.parser = CSVParser(config)
        self.profilers = ColumnProfilers()

    async def process_stream(self, file_handle):
        # Stream-based processing with batching
        async for batch in self.reader.read_batches(file_handle):
            validated = self.validate_utf8(batch)
            rows = self.parser.parse_rows(validated)
            await self.profilers.update(rows)
```

**`profile.py`**: Column profiling
- Per-column type inference
- Statistical aggregation (exact)
- Distribution computation
- Top-N value tracking

**`types.py`**: Type detection
- `infer_column_type()`: Multi-pass type inference
- `validate_numeric()`: Numeric format validation
- `validate_money()`: Money format validation (2 decimals)
- `detect_date_format()`: Date pattern detection
- `check_consistency()`: Cross-row consistency validation

**`distincts.py`**: Exact distinct counting
```python
class DistinctCounter:
    def __init__(self, run_id, column_name):
        self.db = SQLiteIndex(run_id)
        self.table = f"col_{column_name}_distinct"

    def add_value(self, value):
        # INSERT OR IGNORE for exact distinct counting
        self.db.execute(
            f"INSERT OR IGNORE INTO {self.table} (value) VALUES (?)",
            (value,)
        )

    def get_count(self):
        return self.db.query(f"SELECT COUNT(*) FROM {self.table}")[0]
```

**`keys.py`**: Candidate key suggestion
- Score calculation: `(distinct_ratio * (1 - null_ratio)) / invalid_count`
- Single-column candidate identification
- Compound key generation (2-3 column combinations)
- Duplicate detection after confirmation

**`report.py`**: Artifact generation
- JSON profile serialization
- CSV metrics table creation
- HTML report templating
- Audit log formatting

**`errors.py`**: Error aggregation
- Error code definitions
- Count rollup by code
- Severity classification (catastrophic vs. non-catastrophic)
- Message templating

#### Storage Layer (`storage/`)

**`workspace.py`**: File system management
```python
class Workspace:
    def __init__(self, run_id):
        self.run_id = run_id
        self.work_dir = Path(WORK_DIR) / "runs" / str(run_id)
        self.output_dir = Path(OUTPUT_DIR) / str(run_id)

    def ensure_directories(self):
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
```

**`sqlite_index.py`**: SQLite index management
```python
class SQLiteIndex:
    def __init__(self, run_id):
        self.db_path = workspace.get_db_path(run_id)
        self.conn = sqlite3.connect(self.db_path)

    def create_distinct_table(self, column_name):
        self.execute(f"""
            CREATE TABLE IF NOT EXISTS col_{column_name}_distinct (
                value TEXT PRIMARY KEY
            )
        """)

    def create_compound_key_table(self, key_columns):
        self.execute(f"""
            CREATE TABLE IF NOT EXISTS key_hashes (
                hash TEXT PRIMARY KEY,
                count INTEGER DEFAULT 1
            )
        """)
```

#### Model Layer (`models/`)
Pydantic models for data validation:

**`artifacts.py`**: Output schemas
```python
class ColumnProfile(BaseModel):
    name: str
    inferred_type: ColumnType
    null_pct: float
    distinct_count: int
    top_values: List[TopValue]
    length: Optional[LengthStats]
    numeric_stats: Optional[NumericStats]
    money_rules: Optional[MoneyValidation]
    date_stats: Optional[DateStats]

class Profile(BaseModel):
    run_id: UUID
    file: FileMetadata
    errors: List[ErrorDetail]
    warnings: List[ErrorDetail]
    columns: List[ColumnProfile]
    candidate_keys: List[CandidateKey]
```

## Data Flow

### Upload and Processing Flow

```
1. User uploads file
   ↓
2. POST /runs → Create run_id
   ↓
3. POST /runs/{run_id}/upload
   ↓
4. Stream to disk (chunked upload)
   ↓
5. Background task starts
   ↓
6. Streaming ingestion pipeline:

   File → Reader → Parser → Profilers → SQLite

   ├─ UTF-8 validation (byte-level)
   ├─ Gzip decompression (if .gz)
   ├─ CRLF normalization
   ├─ CSV parsing (quote-aware)
   ├─ Header extraction
   ├─ Column count validation
   ├─ Per-row profiling:
   │  ├─ Type inference
   │  ├─ Null tracking
   │  ├─ Length computation
   │  ├─ Value insertion to SQLite (distincts)
   │  └─ Statistical aggregation (Welford)
   ├─ Distribution computation (post-pass from SQLite)
   ├─ Candidate key scoring
   └─ Artifact generation

7. Write outputs:
   ├─ /data/outputs/{run_id}/profile.json
   ├─ /data/outputs/{run_id}/metrics.csv
   ├─ /data/outputs/{run_id}/report.html
   └─ /data/outputs/{run_id}/audit.log.json

8. Update run state to "completed"
   ↓
9. Frontend polls /runs/{run_id}/status
   ↓
10. User views results and downloads artifacts
```

### Type Inference Flow

```
For each column:

1. Initialize type hints:
   all_numeric = True
   all_money = True
   all_date = True
   date_formats = set()

2. For each non-null value:

   ├─ Check numeric: ^[0-9]+(\.[0-9]+)?$
   │  If fail: all_numeric = False
   │
   ├─ Check money: ^[0-9]+\.[0-9]{2}$
   │  If fail: all_money = False
   │
   └─ Check date: try multiple formats
      If match: add format to date_formats
      If fail: all_date = False

3. After all rows:

   if all_money:
       return MONEY
   elif all_numeric:
       return NUMERIC
   elif all_date and len(date_formats) == 1:
       return DATE
   elif cardinality < 100 and cardinality / row_count < 0.01:
       return CODE
   elif max_length > 255:
       return VARCHAR
   elif len(date_formats) > 1:
       return MIXED (error: inconsistent date formats)
   else:
       return ALPHA
```

### Candidate Key Suggestion Flow

```
1. After profiling completes:

2. For each column:
   distinct_ratio = distinct_count / row_count
   null_ratio = null_count / row_count

   if distinct_ratio > 0.95 and null_ratio < 0.05:
       Add to single-key candidates

3. For compound keys:
   Generate 2-column combinations where both have:
   - distinct_ratio > 0.7
   - null_ratio < 0.10

   Create compound hash: hash(col1 + "|" + col2)
   Count distinct hashes via SQLite

   if distinct_hash_count / row_count > 0.995:
       Add to compound-key candidates

4. Score all candidates:
   score = (distinct_ratio * (1 - null_ratio_sum)) / (1 + invalid_count)

5. Sort by score descending

6. Return top 5-10 suggestions to UI
```

## Storage Design

### SQLite Schema

```sql
-- Main run metadata
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state TEXT NOT NULL,
    progress_pct REAL DEFAULT 0,
    delimiter TEXT NOT NULL,
    expect_crlf BOOLEAN,
    quoted BOOLEAN,
    source_filename TEXT
);

-- Structured logs
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    code TEXT,
    message TEXT NOT NULL,
    redaction_applied BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Column profiles
CREATE TABLE columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    name TEXT NOT NULL,
    inferred_type TEXT NOT NULL,
    null_count INTEGER DEFAULT 0,
    nonnull_count INTEGER DEFAULT 0,
    distinct_count INTEGER DEFAULT 0,
    top_values_json TEXT,
    length_min INTEGER,
    length_max INTEGER,
    length_avg REAL,
    numeric_json TEXT,
    money_json TEXT,
    date_json TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Error rollup
CREATE TABLE errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Candidate keys
CREATE TABLE candidate_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    columns_json TEXT NOT NULL,
    distinct_ratio REAL NOT NULL,
    null_ratio_sum REAL NOT NULL,
    score REAL NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Confirmed keys for duplicate detection
CREATE TABLE confirmed_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    columns_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Per-column distinct value tracking (created dynamically)
CREATE TABLE col_{column_name}_distinct (
    value TEXT PRIMARY KEY
);

-- Compound key hash tracking (created on demand)
CREATE TABLE key_hashes (
    hash TEXT PRIMARY KEY
);
```

### Directory Structure

```
/data/
├── work/                          # Temporary workspace
│   └── runs/
│       └── {run_id}/
│           ├── run.sqlite         # Main SQLite DB
│           ├── temp_upload.csv    # Uploaded file
│           └── spill_*.tmp        # Temporary spill files
│
└── outputs/                       # Final artifacts
    └── {run_id}/
        ├── profile.json           # Full profile
        ├── metrics.csv            # Per-column metrics
        ├── report.html            # Interactive report
        └── audit.log.json         # Audit trail
```

## Streaming Pipeline Design

### Why Streaming?

For 3+ GiB files, loading everything into memory is not feasible on commodity hardware. The streaming pipeline ensures:

1. **Constant Memory Usage**: Process data in fixed-size batches
2. **Exact Metrics**: SQLite handles exact distinct counting without memory limits
3. **Early Failure Detection**: Catastrophic errors detected immediately
4. **Progress Tracking**: Byte count allows accurate progress percentage

### Batch Processing

```python
BATCH_SIZE = 10000  # rows

async def process_file(file_path):
    reader = StreamingReader(file_path)
    profiler = StreamingProfiler()

    async for batch in reader.batches(BATCH_SIZE):
        # Process batch
        profiler.update(batch)

        # Update progress
        progress_pct = (reader.bytes_read / reader.total_bytes) * 100
        await update_status(run_id, progress_pct)

        # Check for cancellation
        if should_cancel(run_id):
            break

    # Final pass for distributions
    profiler.finalize()
```

### Welford's Algorithm

For computing exact mean and standard deviation in one pass:

```python
class WelfordAggregator:
    def __init__(self):
        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0

    def update(self, value):
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.M2 += delta * delta2

    def finalize(self):
        if self.count < 2:
            return None
        variance = self.M2 / (self.count - 1)
        stddev = math.sqrt(variance)
        return {"mean": self.mean, "stddev": stddev}
```

### SQLite for Exact Counting

Instead of hash sets in memory, use SQLite:

```python
def count_distinct(column_name, values):
    # Create table if not exists
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS col_{column_name}_distinct (
            value TEXT PRIMARY KEY
        )
    """)

    # Insert all values (duplicates ignored)
    conn.executemany(
        f"INSERT OR IGNORE INTO col_{column_name}_distinct (value) VALUES (?)",
        [(v,) for v in values]
    )

    # Count distinct
    result = conn.execute(
        f"SELECT COUNT(*) FROM col_{column_name}_distinct"
    ).fetchone()

    return result[0]
```

## Error Handling Strategy

### Error Classification

1. **Catastrophic Errors** (stop processing):
   - `E_UTF8_INVALID`: Invalid UTF-8 byte sequence
   - `E_HEADER_MISSING`: No header row found
   - `E_JAGGED_ROW`: Inconsistent column count

2. **Non-Catastrophic Errors** (continue processing):
   - `E_QUOTE_RULE`: Quote escaping violation
   - `E_UNQUOTED_DELIM`: Unquoted embedded delimiter
   - `E_NUMERIC_FORMAT`: Invalid numeric format
   - `E_MONEY_FORMAT`: Invalid money format
   - `E_DATE_MIXED_FORMAT`: Inconsistent date formats
   - `W_DATE_RANGE`: Date out of expected range
   - `W_LINE_ENDING`: Mixed line endings

### Error Aggregation

Instead of storing every error occurrence, aggregate by code:

```python
class ErrorAggregator:
    def __init__(self):
        self.errors = defaultdict(int)

    def record(self, error_code, message):
        key = (error_code, message)
        self.errors[key] += 1

    def get_rollup(self):
        return [
            {"code": code, "message": msg, "count": count}
            for (code, msg), count in self.errors.items()
        ]
```

## PHI/PII Protection

### Logging Strategy

Never log actual data values, only metadata:

```python
# ❌ BAD - Logs PHI
logger.info(f"Found invalid SSN: {ssn_value}")

# ✅ GOOD - Logs only count
logger.info("Found invalid SSN format", extra={
    "error_code": "E_SSN_FORMAT",
    "count": 1,
    "column": "ssn_column"
})
```

### Audit Trail

Record processing metadata without PHI:

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-01-15T10:30:00Z",
  "input_file_hash": "sha256:abc123...",
  "byte_count": 3221225472,
  "row_count": 1500000,
  "column_count": 247,
  "delimiter": "|",
  "utf8_valid": true,
  "errors": {
    "E_NUMERIC_FORMAT": 42,
    "W_DATE_RANGE": 7
  },
  "processing_time_seconds": 127.5
}
```

## Performance Optimization

### Key Design Decisions

1. **SQLite for Indexing**: Faster than Python sets for large distinct counts
2. **Batched Processing**: Balance between memory and I/O
3. **Single-Pass Profiling**: Most metrics computed in one pass
4. **Lazy Distribution**: Only compute full distributions when needed
5. **Streaming Upload**: Avoid storing entire file in memory

### Expected Performance

On a modern laptop (16 GB RAM, SSD):

| File Size | Columns | Rows      | Processing Time |
|-----------|---------|-----------|-----------------|
| 100 MB    | 50      | 500K      | ~5 seconds      |
| 1 GB      | 100     | 2M        | ~30 seconds     |
| 3 GB      | 250     | 5M        | ~2 minutes      |
| 10 GB     | 300     | 15M       | ~8 minutes      |

## Scalability Considerations

### Current Limitations (v1)

- Single-threaded processing
- Local storage only
- No distributed processing
- Synchronous background tasks

### Future Improvements (v2+)

- Multi-threaded column profiling
- S3 integration for storage
- Distributed processing with Dask/Ray
- Async background job queue (Celery)
- Caching layer (Redis)
- Connection pooling for SQLite

## Security Architecture

### v1 (Local Deployment)

- No authentication (localhost only)
- No TLS (local traffic)
- File system isolation via Docker volumes
- No external network calls

### v2+ (Production Deployment)

```
┌─────────────┐
│  VisiQuate  │
│     ID      │ (OIDC Provider)
└──────┬──────┘
       │
       │ OAuth2/OIDC
       │
┌──────▼──────────────────────────────────┐
│          API Gateway                     │
│  ┌────────────────────────────────┐     │
│  │   TLS 1.3 Termination          │     │
│  │   HSTS, CSP Headers            │     │
│  └──────────┬─────────────────────┘     │
│             │                            │
│  ┌──────────▼─────────────────────┐     │
│  │   Auth Middleware              │     │
│  │   - JWT Validation             │     │
│  │   - RBAC Check                 │     │
│  └──────────┬─────────────────────┘     │
│             │                            │
│  ┌──────────▼─────────────────────┐     │
│  │   Rate Limiting                │     │
│  │   - Per-user quotas            │     │
│  │   - Endpoint throttling        │     │
│  └──────────┬─────────────────────┘     │
└─────────────┼──────────────────────────┘
              │
     ┌────────▼────────┐
     │  Data Profiler  │
     │   Backend API   │
     └─────────────────┘
```

## Deployment Architecture

### Docker Compose Stack

```yaml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
    environment:
      - WORK_DIR=/data/work
      - OUTPUT_DIR=/data/outputs
      - MAX_SPILL_GB=50
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

  web:
    build: ./web
    ports:
      - "5173:5173"
    depends_on:
      - api
    environment:
      - VITE_API_URL=http://localhost:8000
```

## Monitoring and Observability

### Metrics to Track

1. **Processing Metrics**:
   - Files processed per hour
   - Average processing time by file size
   - Error rate by error code
   - Peak memory usage
   - Disk usage in work directory

2. **User Metrics**:
   - Upload success rate
   - Time to first result
   - Report download rate
   - API endpoint latency

3. **System Metrics**:
   - CPU utilization
   - Memory utilization
   - Disk I/O throughput
   - SQLite query performance

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

logger.info("profiling_started",
    run_id=run_id,
    file_size_bytes=file_size,
    column_count=column_count,
    delimiter=delimiter
)

logger.info("profiling_completed",
    run_id=run_id,
    duration_seconds=duration,
    row_count=row_count,
    error_count=len(errors)
)
```

## Testing Strategy

### Unit Tests
- UTF-8 validation logic
- CSV parser with various quote scenarios
- Type inference for each type
- Statistical algorithms (Welford, quantiles)
- Error aggregation
- Candidate key scoring

### Integration Tests
- End-to-end file processing
- API endpoints with real files
- Multi-column type scenarios
- Large file handling (sample 100 MB+)
- Error recovery scenarios

### Test Data
- Golden files with known metrics
- Edge cases (single row, single column, all nulls)
- Error scenarios (bad UTF-8, jagged rows)
- Quote edge cases (doubled quotes, embedded delimiters)

## Future Enhancements

### Phase 2
- WebSocket for real-time progress
- Parallel column profiling (multi-threaded)
- Advanced statistical tests (Shapiro-Wilk, KS test)
- Custom regex validation rules
- Schema hint files

### Phase 3
- Multi-file comparison
- Temporal analysis (compare runs over time)
- Data lineage tracking
- ML-based anomaly detection
- Advanced visualizations (D3.js)

### Phase 4
- Cloud deployment (AWS/GCP/Azure)
- Multi-user workspaces
- RBAC with fine-grained permissions
- S3/Blob storage integration
- Data catalog integration

---

## Conclusion

The VQ8 Data Profiler architecture prioritizes:
1. **Exactness**: No approximations in metrics
2. **Scalability**: Handle 3+ GiB files on laptops
3. **Privacy**: PHI/PII protection by design
4. **Simplicity**: Clear component boundaries
5. **Extensibility**: Easy to add new types, checks, and features

The streaming pipeline with SQLite-backed indexing provides the foundation for exact profiling at scale, while maintaining simplicity and local-first operation for sensitive data.
