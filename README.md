# VQ8 Data Profiler

A local, Dockerized web application for profiling large pipe-delimited CSV/TXT files (3+ GiB) with exact metrics and comprehensive validation.

## Features

### Core Capabilities
- **Large File Support**: Process 3+ GiB files with 250+ columns on a laptop
- **Exact Metrics**: No approximations - SQLite-based exact distinct counting
- **Streaming Architecture**: Constant memory usage via disk spill
- **Type Inference**: Detects alpha, varchar, code, numeric, money, date types
- **Validation**: UTF-8, CRLF, CSV quoting, type format rules
- **Candidate Keys**: Auto-suggest single/compound uniqueness keys
- **Error Roll-up**: Aggregate errors by type with counts (PII-aware)

### Data Quality Checks
- UTF-8 encoding validation (catastrophic on first invalid byte)
- Header requirement enforcement
- Constant column count (jagged rows = catastrophic error)
- CSV quoting rules (doubled quotes, embedded delimiters)
- Money format: exactly 2 decimals, no $, ,, ()
- Numeric format: `^[0-9]+(\.[0-9]+)?$` only
- Date format: one consistent format per column (prefer YYYYMMDD)
- Out-of-range date detection (< 1900 or > current year + 1)

### Statistical Analysis
- Exact distinct counts (SQLite-based, no HyperLogLog)
- Top-10 value frequencies (min-heap algorithm)
- Welford's algorithm for mean/standard deviation
- Exact histogram generation
- Gaussian-ness test (D'Agostino/Pearson)
- Date distributions by month/year
- Candidate key scoring: `distinct_ratio * (1 - null_ratio_sum)`

## Project Structure

```
data-profiler/
├── api/                    # Python FastAPI backend
│   ├── services/          # Core business logic
│   │   ├── ingest.py     # UTF-8, CRLF, CSV parsing
│   │   ├── types.py      # Type inference, money/date validation
│   │   ├── distincts.py  # Exact distinct counting (SQLite)
│   │   ├── keys.py       # Candidate key suggestion
│   │   ├── profile.py    # Column profiling, stats
│   │   ├── errors.py     # Error aggregation
│   │   └── report.py     # JSON/CSV/HTML generation
│   ├── storage/           # Data persistence
│   │   ├── workspace.py  # Run directory management
│   │   └── sqlite_index.py # Per-column SQLite databases
│   ├── models/            # Pydantic data models
│   │   └── artifacts.py  # Profile, ColumnProfile, Errors
│   ├── routers/           # FastAPI route handlers
│   │   └── runs.py       # /runs endpoints
│   ├── tests/             # TDD test suite (8 files, 150+ tests)
│   └── app.py             # FastAPI application
├── web/                   # React frontend (TODO)
├── data/                  # Local data directory (gitignored - PHI!)
│   ├── work/             # Temp files, SQLite spill
│   └── outputs/          # JSON/CSV/HTML artifacts
└── docker-compose.yml     # Multi-service orchestration
```

## Installation

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- 8GB+ RAM recommended
- 50GB+ disk space for large file processing

### Local Development Setup

```bash
# Clone repository
cd /Users/brent/git/data-profiler

# Create virtual environment
cd api
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Copy environment config
cp ../.env.example ../.env

# Run tests
pytest
```

## Testing

### Run All Tests
```bash
cd api
pytest -v
```

### Run with Coverage
```bash
pytest --cov=services --cov=storage --cov=models --cov-report=html
open htmlcov/index.html
```

### Run Specific Test Suite
```bash
pytest tests/test_utf8.py -v
pytest tests/test_money.py -v
pytest tests/test_candidate_keys.py -v
```

### Test Organization
- **test_utf8.py**: UTF-8 validation (13 tests)
- **test_line_endings.py**: CRLF detection (15 tests)
- **test_csv_parser.py**: CSV parsing rules (30+ tests)
- **test_type_inference.py**: Type detection (40+ tests)
- **test_money.py**: Money validation (25+ tests)
- **test_date.py**: Date validation (30+ tests)
- **test_distincts.py**: Exact distinct counting (25+ tests)
- **test_candidate_keys.py**: Key suggestion (20+ tests)

**Total: 8 test files, 150+ test cases, targeting 85%+ coverage**

## Architecture

### TDD Approach
This project follows **strict Test-Driven Development**:
1. Tests written FIRST (all 8 test files complete)
2. Implementation follows tests
3. Refactor while keeping tests green
4. No code without a failing test first

### Streaming Pipeline
```
File Upload → UTF-8 Validator → Line Ending Normalizer → CSV Parser
                                                              ↓
                                                        Type Inferencer
                                                              ↓
                                                    Column Profilers (parallel)
                                                              ↓
                                               Exact Distinct Counter (SQLite)
                                                              ↓
                                                  Candidate Key Analyzer
                                                              ↓
                                              Report Generator (JSON/CSV/HTML)
```

### Error Handling

**Catastrophic Errors** (stop immediately):
- Invalid UTF-8 at any byte offset
- Missing header row
- Jagged rows (inconsistent column count)

**Non-Catastrophic Errors** (count and continue):
- Quoting violations
- Type format violations (money, date, numeric)
- Mixed date formats
- Out-of-range dates

### Memory Management
- **Streaming**: 64KB chunk size, constant memory
- **Spill to SQLite**: After 1GB in-memory threshold
- **Batch processing**: 10k rows per batch
- **Cleanup**: Automatic temp file removal

## API Endpoints

### Run Lifecycle
```
POST   /runs                     Create profiling run
POST   /runs/{run_id}/upload     Upload file
GET    /runs/{run_id}/status     Poll processing status
GET    /runs/{run_id}/profile    Get full profile (JSON)
GET    /runs/{run_id}/metrics.csv   Download CSV metrics
GET    /runs/{run_id}/report.html   Download HTML report
```

### Candidate Keys
```
GET    /runs/{run_id}/candidate-keys   Get suggestions
POST   /runs/{run_id}/confirm-keys     Confirm and detect duplicates
```

### Health
```
GET    /healthz                   Health check
```

## Configuration

### Environment Variables (.env)
```bash
# Directories
WORK_DIR=/data/work
OUTPUT_DIR=/data/outputs

# Limits
MAX_SPILL_GB=50
MEMORY_THRESHOLD_MB=1024

# Processing
CHUNK_SIZE=65536
BATCH_SIZE=10000

# Statistical tests
GAUSSIAN_TEST=dagostino

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
PII_REDACTION=true
```

## Security & Compliance

### PHI Handling
- All data treated as HIPAA-scoped PHI
- **Never commit data files** (enforced by .gitignore)
- PII-aware logging: values never logged, only counts
- Structured audit trail per run
- Local-only storage in v1

### Audit Trail Contents
- Input file SHA-256 hash
- Byte count and row count
- UTF-8 validation result
- Parser configuration
- Metrics summary
- Error roll-ups (counts only, no values)

## Performance Targets

### Scalability
- **File size**: 3+ GiB
- **Columns**: 250+
- **Processing time**: < 10 minutes on laptop
- **Memory**: Constant (regardless of file size)
- **Accuracy**: Exact metrics (no approximations)

### Benchmarks (Target)
- UTF-8 validation: 500+ MB/s
- CSV parsing: 200+ MB/s
- Distinct counting: 1M rows/second
- Type inference: 2M values/second

## Type System

### Type Detection Rules

| Type | Pattern | Example | Notes |
|------|---------|---------|-------|
| **numeric** | `^[0-9]+(\.[0-9]+)?$` | `123`, `45.67` | No commas, $, () |
| **money** | Numeric + exactly 2 decimals | `123.45` | No $, ,, () |
| **date** | One format per column | `20220101` | Prefer YYYYMMDD |
| **alpha** | All letters | `ABC`, `xyz` | String type |
| **varchar** | Mixed content | `abc123` | String type |
| **code** | Low cardinality (< 10%) | `A`, `B`, `C` | Dictionary-like |
| **mixed** | Multiple types | - | Inconsistent |
| **unknown** | Cannot determine | - | All nulls |

### Validation Rules

**Money**:
- Exactly 2 decimal places required
- No dollar signs ($)
- No commas (,)
- No parentheses for negatives ()

**Date**:
- One consistent format per column
- Out-of-range warning: year < 1900 or > current + 1
- Leap year validation
- Valid days per month

## Candidate Key Suggestion

### Scoring Algorithm
```python
score = distinct_ratio * (1 - null_ratio_sum)
```

Where:
- `distinct_ratio = distinct_count / total_count`
- `null_ratio_sum = sum(null_count / total_count for each column)`

### Thresholds
- **Single column**: Min score 0.8, min distinct ratio 0.9
- **Compound key**: Min score 0.8
- **Max nulls**: 10% for primary key

### Workflow
1. Analyzer suggests top 5 candidates
2. User confirms selection
3. Duplicate detector runs (hash-based)
4. Results include duplicate examples

## Documentation

Comprehensive documentation is available in the `/docs` directory:

### Getting Started
- **[Quickstart Guide](docs/QUICKSTART.md)** - Get up and running in 5 minutes
- **[User Guide](docs/USER_GUIDE.md)** - Complete user documentation with examples

### Technical Documentation
- **[Architecture](docs/ARCHITECTURE.md)** - System design, components, and data flow
- **[API Reference](docs/API.md)** - Complete REST API documentation with examples
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Development setup, contributing, and extending

### Operations
- **[Operations Guide](docs/OPERATIONS.md)** - Deployment, monitoring, and maintenance
- **[Error Codes](docs/ERROR_CODES.md)** - Complete error code reference with solutions

### Quick Links
- **Interactive API Docs**: http://localhost:8000/docs (when running)
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/healthz

## Development Roadmap

### Phase 1: Test Suite ✓ COMPLETE
- [x] 8 test files with 150+ test cases
- [x] Project configuration (pyproject.toml, requirements.txt)
- [x] Environment setup (.env.example, .gitignore)
- [x] **Documentation Suite ✓ NEW**
  - [x] Architecture documentation
  - [x] API reference with examples
  - [x] Comprehensive user guide
  - [x] Developer guide
  - [x] Operations and deployment guide
  - [x] Error code reference
  - [x] Quickstart guide

### Phase 2: Core Implementation (NEXT)
- [ ] UTF-8 validator (services/ingest.py)
- [ ] Line ending detector (services/ingest.py)
- [ ] CSV parser (services/ingest.py)
- [ ] Type inference engine (services/types.py)
- [ ] Money validator (services/types.py)
- [ ] Date validator (services/types.py)
- [ ] Exact distinct counter (services/distincts.py)
- [ ] Candidate key analyzer (services/keys.py)

### Phase 3: API & Reports
- [ ] FastAPI application setup
- [ ] Run lifecycle endpoints
- [ ] Report generation (JSON, CSV, HTML)
- [ ] Error aggregation
- [ ] Audit logging

### Phase 4: Frontend
- [ ] React + Vite setup
- [ ] Upload interface
- [ ] Status polling with progress
- [ ] Results dashboard
- [ ] Per-column drill-down
- [ ] Error roll-up display
- [ ] Candidate key confirmation UI

### Phase 5: Deployment
- [ ] Docker Compose orchestration
- [ ] Volume management
- [ ] Health checks
- [ ] Resource limits

## Contributing

### Code Quality
- **Black**: Code formatting (line length 100)
- **Ruff**: Linting and style checks
- **mypy**: Static type checking
- **pytest**: Unit and integration tests
- **Coverage**: Minimum 85% required

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

### Security Scanning
```bash
bandit -r services/ storage/ models/
safety check
pip-audit
```

## License

Proprietary - VisiQuate Internal Use Only

## Contact

VisiQuate Development Team

---

**Status**: Phase 1 Complete (Test Suite) | Phase 2 In Progress (Implementation)

**Test Coverage**: 0% (no implementation yet) | **Target**: 85%+

**Tests Written**: 8 files, 150+ test cases | **Tests Passing**: 0 (waiting for implementation)
