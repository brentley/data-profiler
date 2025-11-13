# Development Guide

Setup, testing, and implementation guidelines for data profiler development.

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Docker and Docker Compose
- SQLite 3.40+
- Git

### Initial Setup

```bash
# Clone repository
git clone <repository>
cd data-profiler

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
cd api
pip install -r requirements.txt
pip install -r requirements-dev.txt
cd ..

# Install Node dependencies
cd web
npm install
cd ..

# Create .env file for development
cp .env.example .env
# Edit .env with development settings
```

### Environment Variables

Development `.env`:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Storage
WORK_DIR=./data/work
OUTPUT_DIR=./data/outputs
MAX_SPILL_GB=10

# Statistical Testing
GAUSSIAN_TEST=dagostino

# Database
DATABASE_URL=sqlite:///./data/profiler.db

# Logging
LOG_LEVEL=DEBUG

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Running Services

### Using Docker Compose (Recommended)

```bash
# Start all services in background
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f web

# Stop services
docker-compose down

# Rebuild services
docker-compose up -d --build
```

### Manual Development Mode

```bash
# Terminal 1: Start API
cd api
source ../.venv/bin/activate
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Frontend
cd web
npm run dev

# Terminal 3: (Optional) Run tests
cd api
pytest -v
```

### API Access

- API Base URL: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs` (Swagger UI)
- Alternative Docs: `http://localhost:8000/redoc` (ReDoc)
- OpenAPI Schema: `http://localhost:8000/openapi.json`

### Frontend Access

- Web App: `http://localhost:5173` (Vite dev server)
- Production Build: `http://localhost:4173` (after `npm run build && npm run preview`)

---

## Testing

### Unit Tests

```bash
cd api

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test class
pytest tests/test_parser.py::TestUTF8Validation -v

# Run with verbose output
pytest -v

# Run with specific marker
pytest -m "parser" -v
```

### Test Coverage Requirements

- Minimum: 85% line coverage
- Target: 90% line coverage
- All critical paths must have tests

Generate coverage report:

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html  # View in browser
```

### Test Organization

```
api/tests/
  __init__.py
  test_utf8.py           # UTF-8 validation tests
  test_parser.py         # CSV parser tests
  test_types.py          # Type inference tests
  test_money.py          # Money format validation
  test_date.py           # Date format validation
  test_distincts.py      # Distinct counting tests
  test_keys.py           # Key suggestion tests
  test_api.py            # API endpoint tests
  conftest.py            # Pytest fixtures
  data/
    sample_*.csv         # Test data files
    golden_*.json        # Expected output files
```

### Writing Tests (TDD)

Follow test-driven development:

```python
# 1. Write failing test first
def test_numeric_type_detection():
    """Test that numeric type is detected correctly."""
    profiler = ColumnProfiler()
    values = ["100", "150.50", "200"]
    result = profiler.infer_type(values)
    assert result.type == "numeric"

# 2. Implement feature to pass test
class ColumnProfiler:
    def infer_type(self, values):
        if all(self._is_numeric(v) for v in values):
            return ColumnType.NUMERIC
        # ... other logic

    @staticmethod
    def _is_numeric(value):
        import re
        return bool(re.match(r"^[0-9]+(\.[0-9]+)?$", value))

# 3. Run test to verify it passes
```

### Test Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a sample CSV file for testing."""
    file = tmp_path / "test.csv"
    file.write_text("id,name,amount\n1,Alice,100.00\n2,Bob,200.00\n")
    return file

@pytest.fixture
def api_client():
    """Create test API client."""
    from fastapi.testclient import TestClient
    from app import app
    return TestClient(app)

def test_upload_endpoint(api_client, sample_csv_file):
    """Test file upload endpoint."""
    with open(sample_csv_file, "rb") as f:
        response = api_client.post(
            "/runs/test-run-id/upload",
            files={"file": f}
        )
    assert response.status_code == 202
```

### Integration Tests

Test full workflows:

```python
def test_complete_profiling_workflow(api_client, sample_csv_file):
    """Test complete profiling workflow."""
    # 1. Create run
    response = api_client.post("/runs", json={"delimiter": ","})
    assert response.status_code == 201
    run_id = response.json()["run_id"]

    # 2. Upload file
    with open(sample_csv_file, "rb") as f:
        response = api_client.post(f"/runs/{run_id}/upload", files={"file": f})
    assert response.status_code == 202

    # 3. Check status until complete
    import time
    for _ in range(30):
        response = api_client.get(f"/runs/{run_id}/status")
        if response.json()["state"] == "completed":
            break
        time.sleep(0.1)

    # 4. Get profile
    response = api_client.get(f"/runs/{run_id}/profile")
    assert response.status_code == 200
    profile = response.json()
    assert profile["file"]["rows"] == 2
    assert profile["file"]["columns"] == 3
```

---

## Code Quality

### Formatting

```bash
cd api

# Format with Black
black .

# Check formatting
black --check .
```

### Linting

```bash
cd api

# Check with Ruff
ruff check .

# Fix common issues
ruff check --fix .
```

### Type Checking

```bash
cd api

# Check types with mypy
mypy app/

# Check specific file
mypy app/services/profile.py
```

### Run All Checks

```bash
make lint      # Lint only
make fmt       # Format only
make check     # All checks
```

---

## Project Structure

### Backend Structure

```
api/
  app.py                    # FastAPI application entry point
  routers/
    runs.py                 # /runs endpoints
  services/
    ingest.py               # File ingestion pipeline
    profile.py              # Column profiling logic
    types.py                # Type inference
    distincts.py            # Exact distinct counting
    keys.py                 # Key suggestion algorithm
    report.py               # Report generation
    errors.py               # Error aggregation
  storage/
    workspace.py            # Filesystem management
    sqlite_index.py         # SQLite index management
  models/
    artifacts.py            # Pydantic models for API responses
  tests/
    conftest.py             # Pytest fixtures
    test_*.py               # Test modules
  requirements.txt          # Production dependencies
  requirements-dev.txt      # Development dependencies
```

### Frontend Structure

```
web/
  src/
    pages/
      index.tsx             # Home/upload page
      run/[id].tsx          # Run results page
    components/
      UploadForm.tsx        # File upload form
      RunStatus.tsx         # Progress display
      ColumnCard.tsx        # Per-column results card
      ErrorRollup.tsx       # Error summary table
      CandidateKeys.tsx     # Key suggestions UI
    styles/
      globals.css           # Global styles
      components.module.css # Component-specific styles
    main.tsx                # React entry point
  public/
    vite.svg                # Vite logo
  vite.config.ts            # Vite configuration
  tsconfig.json             # TypeScript configuration
  package.json              # NPM dependencies
  index.html                # HTML entry point
```

### Key Implementation Files

Backend entry point (`api/app.py`):

```python
"""
FastAPI application for data profiler.

Defines all API endpoints, request/response models, and service integrations.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from . import routers

app = FastAPI(
    title="Data Profiler API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routers.runs.router, prefix="/runs", tags=["runs"])

@app.get("/healthz")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
```

---

## Common Development Tasks

### Adding a New API Endpoint

1. **Define Request/Response Models** (`models/artifacts.py`):

```python
from pydantic import BaseModel

class MyRequest(BaseModel):
    """Request model for new endpoint."""
    param1: str
    param2: int

class MyResponse(BaseModel):
    """Response model for new endpoint."""
    result: str
    status: str
```

2. **Add Tests** (`tests/test_new_feature.py`):

```python
def test_new_endpoint_success(api_client):
    """Test successful request to new endpoint."""
    response = api_client.post(
        "/endpoint",
        json={"param1": "value", "param2": 42}
    )
    assert response.status_code == 200
    assert response.json()["result"] == "expected_result"

def test_new_endpoint_invalid_input(api_client):
    """Test error handling."""
    response = api_client.post(
        "/endpoint",
        json={"param1": "value"}  # Missing param2
    )
    assert response.status_code == 422  # Validation error
```

3. **Implement Endpoint** (`routers/runs.py`):

```python
from fastapi import APIRouter
from ..models.artifacts import MyRequest, MyResponse

router = APIRouter()

@router.post("/endpoint")
async def my_endpoint(request: MyRequest) -> MyResponse:
    """
    Process request.

    Args:
        request: MyRequest object with param1 and param2

    Returns:
        MyResponse with result

    Raises:
        HTTPException: If validation fails
    """
    result = process_request(request.param1, request.param2)
    return MyResponse(result=result, status="success")
```

4. **Document Endpoint** - Update `API.md`

### Adding Type Validation

1. **Define Validation Rules** (`services/types.py`):

```python
class TypeValidator:
    """Validates values against type patterns."""

    @staticmethod
    def validate_new_type(value: str) -> bool:
        """
        Validate that value matches new type pattern.

        Args:
            value: String value to validate

        Returns:
            True if valid, False otherwise

        Examples:
            >>> TypeValidator.validate_new_type("valid")
            True
            >>> TypeValidator.validate_new_type("invalid")
            False
        """
        import re
        return bool(re.match(r"^pattern$", value))
```

2. **Add Tests** (`tests/test_types.py`):

```python
def test_new_type_valid():
    """Test that valid values pass."""
    assert TypeValidator.validate_new_type("valid")

def test_new_type_invalid():
    """Test that invalid values fail."""
    assert not TypeValidator.validate_new_type("invalid")
```

3. **Integrate into Profiler** (`services/profile.py`):

```python
def infer_type(self, values: List[str]) -> str:
    """Infer column type from sample values."""
    # ... existing logic
    if all(TypeValidator.validate_new_type(v) for v in sample):
        return "new_type"
    # ... rest of inference
```

### Debugging Issues

#### Issue: Tests Failing with "Module not found"

```bash
cd api
python -m pytest  # Use module mode instead of direct pytest
```

#### Issue: API Not Starting

```bash
# Check logs
docker-compose logs api

# Verify Python syntax
python -m py_compile app.py

# Check dependencies
pip list | grep fastapi
```

#### Issue: File Upload Fails

```bash
# Check /data permissions
ls -la data/
chmod 777 data/

# Check file size
ls -lh uploads/

# Check disk space
df -h
```

#### Issue: Type Inference Wrong

Enable debug logging:

```python
# In services/types.py
import logging
logger = logging.getLogger(__name__)

def infer_type(values):
    logger.debug(f"Sample values: {values[:10]}")
    # ... inference logic
    logger.debug(f"Inferred type: {inferred_type}")
    return inferred_type
```

Then check logs:

```bash
docker-compose logs api | grep "Sample values"
```

---

## Documentation

### Docstring Standards

All functions and classes must have docstrings:

```python
def calculate_statistics(values: List[float]) -> dict:
    """
    Calculate statistical measures for numeric values.

    This function computes exact statistics using Welford's algorithm
    to avoid numerical instability with large datasets.

    Args:
        values: List of numeric values to analyze

    Returns:
        Dictionary containing:
        - min: Minimum value
        - max: Maximum value
        - mean: Arithmetic mean
        - median: Middle value
        - stddev: Standard deviation
        - quantiles: Dict of percentiles

    Raises:
        ValueError: If values list is empty
        TypeError: If values contain non-numeric items

    Examples:
        >>> stats = calculate_statistics([1.0, 2.0, 3.0])
        >>> stats["mean"]
        2.0
        >>> stats["median"]
        2.0

    Note:
        For very large datasets (1M+ values), consider using
        streaming calculation to reduce memory usage.

    See Also:
        - TYPE_INFERENCE.md for type detection
        - DATA_MODEL.md for statistics storage
    """
    if not values:
        raise ValueError("Cannot calculate statistics on empty list")

    # Implementation...
```

### Comment Standards

Inline comments for complex logic:

```python
# Welford's algorithm for numerically stable mean/variance
# See: https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
mean = 0.0
m2 = 0.0
count = 0

for x in values:
    count += 1
    delta = x - mean
    mean += delta / count
    delta2 = x - mean
    m2 += delta * delta2

variance = m2 / (count - 1) if count > 1 else 0
stddev = sqrt(variance)
```

---

## Performance Optimization

### Profiling

Profile performance issues:

```bash
cd api

# Profile with cProfile
python -m cProfile -s cumulative app.py > profile_stats.txt

# Use line_profiler for function-level profiling
pip install line_profiler
kernprof -l -v services/profile.py
```

### Memory Management

Monitor memory usage:

```python
import psutil
import os

process = psutil.Process(os.getpid())
print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

### Optimization Tips

1. **Streaming Processing**: Process file in chunks, not entire file
2. **SQLite Spill**: Use temp DB for large datasets
3. **Caching**: Cache frequent computations
4. **Batch Operations**: Batch DB inserts instead of row-by-row
5. **Index Optimization**: Create indices on frequently queried columns

---

## Deployment

### Local Docker Build

```bash
# Build API image
docker build -t data-profiler-api -f api/Dockerfile ./api

# Build web image
docker build -t data-profiler-web -f web/Dockerfile ./web

# Or use compose
docker-compose build
```

### Volume Mounts

Development:

```bash
docker-compose -f docker-compose.yml up
```

Production:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Troubleshooting

### FAQ

**Q: How do I profile a large file during development?**

A: Create a sample file with same structure but fewer rows:

```bash
head -1000 large_file.csv > small_sample.csv
```

**Q: How do I see detailed error messages?**

A: Enable debug logging in `.env`:

```env
LOG_LEVEL=DEBUG
```

**Q: How do I test with different delimiters?**

A: Create test files with different delimiters:

```bash
# Pipe-delimited
echo -e "id|name|amount\n1|Alice|100" > test_pipe.csv

# Comma-delimited
echo -e "id,name,amount\n1,Alice,100" > test_comma.csv
```

**Q: How do I clear old test data?**

A: Remove data directory and recreate:

```bash
rm -rf data/
mkdir -p data/work/runs data/outputs
```

**Q: How do I run a single test method?**

A: Use pytest syntax:

```bash
pytest tests/test_parser.py::TestCSVParser::test_pipe_delimiter -v
```

**Q: How do I debug async issues?**

A: Use AsyncIO debug mode:

```python
import asyncio
asyncio.run(main(), debug=True)
```

---

## Resources

### Documentation

- API Reference: `API.md`
- Error Codes: `ERROR_CODES.md`
- Type Inference: `TYPE_INFERENCE.md`
- Data Model: `DATA_MODEL.md`
- Project README: `README.md`

### External Resources

- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/
- SQLite: https://www.sqlite.org/docs.html
- React: https://react.dev/
- Vite: https://vitejs.dev/

### Testing Resources

- Pytest: https://docs.pytest.org/
- FastAPI Testing: https://fastapi.tiangolo.com/advanced/testing-dependencies/

---

## Contributing

See `README.md` for contribution guidelines.

When submitting changes:

1. All tests pass (`make test`)
2. Code is formatted (`make fmt`)
3. No linting errors (`make lint`)
4. Coverage >= 85% (`pytest --cov`)
5. Documentation updated
6. Commit message follows conventions
