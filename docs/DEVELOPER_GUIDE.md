# Developer Guide

This guide covers setting up the development environment, understanding the codebase, adding features, and contributing to the VQ8 Data Profiler.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Architecture Overview](#architecture-overview)
4. [Testing](#testing)
5. [Adding New Features](#adding-new-features)
6. [Code Standards](#code-standards)
7. [Debugging](#debugging)
8. [Performance Optimization](#performance-optimization)
9. [Contributing](#contributing)

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker and Docker Compose
- Git
- 8 GB+ RAM
- 50 GB+ free disk space

### Initial Setup

1. **Clone Repository**:
```bash
git clone <repository-url>
cd data-profiler
```

2. **Backend Setup**:
```bash
cd api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify installation
python -c "import fastapi; print('FastAPI OK')"
```

3. **Frontend Setup**:
```bash
cd web

# Install dependencies
npm install

# Verify installation
npm run dev  # Should start dev server
```

4. **Environment Configuration**:
```bash
cp .env.example .env
# Edit .env with your local paths
```

5. **Create Data Directories**:
```bash
mkdir -p data/work data/outputs
```

### Running Locally

#### Development Mode (without Docker)

**Backend**:
```bash
cd api
source .venv/bin/activate
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd web
npm run dev
# Runs on http://localhost:5173
```

#### Docker Mode

```bash
# Build and start all services
docker compose up --build

# Or run in background
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### IDE Setup

#### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance
- ESLint
- Prettier
- Docker
- REST Client

**`.vscode/settings.json`**:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/api/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

#### PyCharm

1. Open project
2. Configure Python interpreter: Settings → Project → Python Interpreter
3. Select `api/.venv/bin/python`
4. Enable FastAPI plugin if available

## Project Structure

```
data-profiler/
├── api/                           # Backend (FastAPI)
│   ├── app.py                    # Main application entry point
│   ├── routers/                  # API route handlers
│   │   ├── __init__.py
│   │   ├── runs.py              # Run lifecycle endpoints
│   │   ├── upload.py            # File upload handling
│   │   └── artifacts.py         # Report generation
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── ingest.py            # Streaming ingestion pipeline
│   │   ├── profile.py           # Column profiling
│   │   ├── types.py             # Type inference
│   │   ├── distincts.py         # Exact distinct counting
│   │   ├── keys.py              # Candidate key suggestion
│   │   ├── report.py            # Artifact generation
│   │   └── errors.py            # Error aggregation
│   ├── storage/                  # Data persistence
│   │   ├── __init__.py
│   │   ├── workspace.py         # File system management
│   │   └── sqlite_index.py      # SQLite indexing
│   ├── models/                   # Pydantic models
│   │   ├── __init__.py
│   │   ├── artifacts.py         # Output schemas
│   │   └── requests.py          # Request schemas
│   ├── tests/                    # Test suite
│   │   ├── __init__.py
│   │   ├── test_utf8.py
│   │   ├── test_parser.py
│   │   ├── test_types.py
│   │   ├── test_money.py
│   │   ├── test_date.py
│   │   ├── test_distincts.py
│   │   ├── test_keys.py
│   │   └── test_api.py
│   ├── fixtures/                 # Test data
│   │   ├── valid_pipe.txt
│   │   ├── valid_comma.csv
│   │   ├── quoted_fields.csv
│   │   └── mixed_formats.csv
│   ├── requirements.txt          # Production dependencies
│   ├── requirements-dev.txt      # Dev dependencies
│   ├── pyproject.toml           # Python project config
│   └── Dockerfile               # API container
│
├── web/                          # Frontend (React + Vite)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── UploadPage.tsx
│   │   │   ├── StatusPage.tsx
│   │   │   └── ResultsPage.tsx
│   │   ├── components/
│   │   │   ├── UploadForm.tsx
│   │   │   ├── RunStatus.tsx
│   │   │   ├── ColumnCard.tsx
│   │   │   ├── ErrorRollup.tsx
│   │   │   └── CandidateKeys.tsx
│   │   ├── hooks/
│   │   │   ├── usePolling.ts
│   │   │   └── useRunStatus.ts
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md       # This file
│   └── OPERATIONS.md
│
├── data/                         # Data storage (gitignored)
│   ├── work/                    # Temporary workspace
│   └── outputs/                 # Final artifacts
│
├── docker-compose.yml            # Service orchestration
├── Makefile                      # Build automation
├── .env.example                  # Environment template
├── .gitignore
└── README.md
```

## Architecture Overview

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

### Key Patterns

#### Streaming Pipeline

All file processing uses streaming to handle large files:

```python
class StreamingIngestor:
    BATCH_SIZE = 10000

    async def process_file(self, file_path: Path):
        async with aiofiles.open(file_path, 'rb') as f:
            async for batch in self._read_batches(f):
                await self._process_batch(batch)
```

#### SQLite for Exact Counting

Distinct values tracked in SQLite to avoid memory exhaustion:

```python
def create_distinct_table(self, column_name: str):
    self.conn.execute(f"""
        CREATE TABLE IF NOT EXISTS col_{column_name}_distinct (
            value TEXT PRIMARY KEY
        )
    """)

def add_value(self, column_name: str, value: str):
    self.conn.execute(
        f"INSERT OR IGNORE INTO col_{column_name}_distinct (value) VALUES (?)",
        (value,)
    )
```

#### Welford's Algorithm

Online statistics without storing all values:

```python
class WelfordAggregator:
    def update(self, value: float):
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.M2 += delta * delta2

    def finalize(self) -> dict:
        variance = self.M2 / (self.count - 1) if self.count > 1 else 0
        return {
            "mean": self.mean,
            "stddev": math.sqrt(variance)
        }
```

## Testing

### Test Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_utf8_validator.py
│   ├── test_csv_parser.py
│   ├── test_type_inference.py
│   └── test_welford.py
├── integration/             # Integration tests (slower)
│   ├── test_pipeline.py
│   ├── test_api_endpoints.py
│   └── test_sqlite_index.py
└── fixtures/                # Test data
    ├── small_valid.csv     # 100 rows, all valid
    ├── large_valid.csv     # 10K rows, all valid
    ├── quoted_edge_cases.csv
    └── expected_profiles/  # Golden files
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific test file
pytest tests/unit/test_types.py -v

# Specific test
pytest tests/unit/test_types.py::test_numeric_inference -v

# Fast tests only (skip slow integration tests)
pytest -m "not slow"

# Watch mode (re-run on changes)
ptw
```

### Writing Tests

#### Unit Test Example

```python
import pytest
from services.types import infer_column_type

def test_numeric_type_inference():
    values = ["123", "456.78", "901.23"]
    result = infer_column_type(values)
    assert result == "numeric"

def test_money_type_inference():
    values = ["123.45", "678.90", "0.01"]
    result = infer_column_type(values)
    assert result == "money"

def test_mixed_type_detection():
    values = ["123", "abc", "456"]
    result = infer_column_type(values)
    assert result == "mixed"

@pytest.mark.parametrize("value,expected", [
    ("123", True),
    ("123.45", True),
    ("$123.45", False),
    ("1,234.56", False),
])
def test_numeric_validation(value, expected):
    from services.types import validate_numeric
    assert validate_numeric(value) == expected
```

#### Integration Test Example

```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_full_profiling_pipeline():
    # Create run
    response = client.post("/runs", json={
        "delimiter": "|",
        "quoted": True
    })
    assert response.status_code == 201
    run_id = response.json()["run_id"]

    # Upload file
    with open("tests/fixtures/small_valid.csv", "rb") as f:
        response = client.post(
            f"/runs/{run_id}/upload",
            files={"file": f}
        )
    assert response.status_code == 202

    # Wait for completion (or mock background task)
    # ... polling logic ...

    # Get profile
    response = client.get(f"/runs/{run_id}/profile")
    assert response.status_code == 200
    profile = response.json()

    assert profile["file"]["rows"] == 100
    assert profile["file"]["columns"] == 5
```

### Test Coverage Goals

- **Overall**: ≥85%
- **Services**: ≥90%
- **Routers**: ≥80%
- **Models**: ≥95% (mostly auto-generated by Pydantic)

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: [3.11, 3.12]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          cd api
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          cd api
          pytest --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./api/coverage.xml
```

## Adding New Features

### Adding a New Column Type

1. **Define Type in Enum** (`models/artifacts.py`):
```python
class ColumnType(str, Enum):
    ALPHA = "alpha"
    NUMERIC = "numeric"
    MONEY = "money"
    DATE = "date"
    PHONE = "phone"  # New type
```

2. **Add Validation Logic** (`services/types.py`):
```python
def validate_phone(value: str) -> bool:
    """Validate phone number format."""
    pattern = r'^\d{3}-\d{3}-\d{4}$'
    return bool(re.match(pattern, value))
```

3. **Update Type Inference** (`services/types.py`):
```python
def infer_column_type(values: List[str]) -> ColumnType:
    all_phone = True

    for value in values:
        if not validate_phone(value):
            all_phone = False
            break

    if all_phone:
        return ColumnType.PHONE

    # ... existing logic ...
```

4. **Add Type-Specific Profiling** (`services/profile.py`):
```python
def profile_phone_column(values: List[str]) -> dict:
    """Profile phone number column."""
    area_codes = defaultdict(int)

    for value in values:
        if validate_phone(value):
            area_code = value.split('-')[0]
            area_codes[area_code] += 1

    return {
        "area_codes": dict(area_codes),
        "top_area_codes": sorted(
            area_codes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
    }
```

5. **Update Model** (`models/artifacts.py`):
```python
class PhoneStats(BaseModel):
    area_codes: Dict[str, int]
    top_area_codes: List[Tuple[str, int]]

class ColumnProfile(BaseModel):
    # ... existing fields ...
    phone_stats: Optional[PhoneStats] = None
```

6. **Write Tests** (`tests/test_phone.py`):
```python
def test_phone_validation():
    assert validate_phone("555-123-4567") == True
    assert validate_phone("5551234567") == False
    assert validate_phone("555-12-4567") == False

def test_phone_inference():
    values = ["555-123-4567", "555-987-6543"]
    assert infer_column_type(values) == ColumnType.PHONE
```

### Adding a New API Endpoint

1. **Define Request/Response Models** (`models/requests.py`):
```python
class RunComparisonRequest(BaseModel):
    run_ids: List[UUID]

class RunComparisonResponse(BaseModel):
    runs: List[UUID]
    differences: List[ColumnDifference]
```

2. **Create Router Function** (`routers/comparison.py`):
```python
from fastapi import APIRouter, HTTPException
from models.requests import RunComparisonRequest, RunComparisonResponse
from services.comparison import compare_runs

router = APIRouter(prefix="/comparison", tags=["comparison"])

@router.post("/compare", response_model=RunComparisonResponse)
async def compare_profiling_runs(request: RunComparisonRequest):
    """Compare multiple profiling runs."""
    try:
        result = await compare_runs(request.run_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

3. **Implement Service Logic** (`services/comparison.py`):
```python
async def compare_runs(run_ids: List[UUID]) -> RunComparisonResponse:
    """Compare profiling results across runs."""
    profiles = []

    for run_id in run_ids:
        profile = load_profile(run_id)
        profiles.append(profile)

    differences = _compute_differences(profiles)

    return RunComparisonResponse(
        runs=run_ids,
        differences=differences
    )
```

4. **Register Router** (`app.py`):
```python
from routers import comparison

app.include_router(comparison.router)
```

5. **Write Tests** (`tests/test_comparison.py`):
```python
def test_compare_runs():
    response = client.post("/comparison/compare", json={
        "run_ids": [str(uuid4()), str(uuid4())]
    })
    assert response.status_code == 200
```

### Adding a New Frontend Component

1. **Create Component** (`web/src/components/NewFeature.tsx`):
```typescript
import React from 'react';

interface NewFeatureProps {
  data: any;
  onAction: () => void;
}

export const NewFeature: React.FC<NewFeatureProps> = ({ data, onAction }) => {
  return (
    <div className="new-feature">
      <h2>New Feature</h2>
      {/* Component content */}
      <button onClick={onAction}>Action</button>
    </div>
  );
};
```

2. **Add API Client Function** (`web/src/api/client.ts`):
```typescript
export async function newFeatureAction(runId: string): Promise<Result> {
  const response = await fetch(`${API_BASE_URL}/new-endpoint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId })
  });

  if (!response.ok) {
    throw new Error('Action failed');
  }

  return await response.json();
}
```

3. **Integrate into Page** (`web/src/pages/ResultsPage.tsx`):
```typescript
import { NewFeature } from '../components/NewFeature';

// Inside component
<NewFeature
  data={profileData}
  onAction={handleNewAction}
/>
```

4. **Add Styles** (`web/src/components/NewFeature.css`):
```css
.new-feature {
  padding: 1rem;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
}
```

## Code Standards

### Python Style Guide

Follow PEP 8 with these additions:

- **Line Length**: 100 characters max
- **Imports**: Use `isort` for consistent ordering
- **Formatting**: Use `black` formatter
- **Type Hints**: Required for all public functions
- **Docstrings**: Google style

Example:
```python
from typing import List, Optional
import pandas as pd

def process_column(
    values: List[str],
    column_name: str,
    null_marker: Optional[str] = None
) -> dict:
    """Process a single column and return profile statistics.

    Args:
        values: List of string values from the column
        column_name: Name of the column being processed
        null_marker: Optional marker for null values (default: None)

    Returns:
        Dictionary containing column profile statistics

    Raises:
        ValueError: If values list is empty
    """
    if not values:
        raise ValueError("Values list cannot be empty")

    # Implementation
    return {"name": column_name, "count": len(values)}
```

### TypeScript Style Guide

- **ESLint**: Use provided config
- **Prettier**: Auto-format on save
- **Type Safety**: Prefer interfaces over `any`
- **Components**: Functional components with hooks
- **Naming**: PascalCase for components, camelCase for functions

Example:
```typescript
interface ColumnData {
  name: string;
  type: string;
  nullPct: number;
}

export const ColumnCard: React.FC<{ data: ColumnData }> = ({ data }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="column-card">
      <h3>{data.name}</h3>
      <span className="type-badge">{data.type}</span>
    </div>
  );
};
```

### Git Commit Messages

Follow conventional commits:

```
type(scope): short description

Longer description if needed

- Bullet points for details
- Reference issues: #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (no logic change)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Build process, dependencies

Examples:
```
feat(api): add phone number type detection

Implements phone number validation and profiling statistics.
Includes area code aggregation.

Closes #45

---

fix(parser): handle doubled quotes in CSV fields

The parser was incorrectly splitting on inner quotes even when
properly escaped. Now follows RFC 4180 exactly.

---

docs(user-guide): add troubleshooting section

Added common issues and solutions for:
- Upload failures
- Processing hangs
- Unexpected types
```

## Debugging

### Backend Debugging

#### Print Debugging

```python
import logging

logger = logging.getLogger(__name__)

def problematic_function():
    logger.debug(f"Input: {input_value}")
    result = process(input_value)
    logger.debug(f"Result: {result}")
    return result
```

#### VS Code Debugging

**`.vscode/launch.json`**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    },
    {
      "name": "Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests/",
        "-v"
      ]
    }
  ]
}
```

#### Python Debugger (pdb)

```python
import pdb

def complex_logic(data):
    pdb.set_trace()  # Breakpoint
    result = process(data)
    return result
```

### Frontend Debugging

#### Browser DevTools

1. Open Chrome DevTools (F12)
2. Go to Sources tab
3. Set breakpoints in TypeScript files
4. Inspect network requests in Network tab

#### React DevTools

Install React DevTools extension:
- Inspect component tree
- View props and state
- Track re-renders

#### Console Logging

```typescript
console.log('Data:', data);
console.table(arrayData);
console.error('Error:', error);
```

### Docker Debugging

```bash
# View logs
docker compose logs api -f
docker compose logs web -f

# Enter container
docker compose exec api bash
docker compose exec web sh

# Inspect container
docker inspect data-profiler_api_1

# Check resource usage
docker stats
```

## Performance Optimization

### Profiling Python Code

#### cProfile

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
process_large_file(file_path)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

#### line_profiler

```bash
pip install line_profiler

# Add @profile decorator
@profile
def slow_function():
    # ...

kernprof -l -v script.py
```

#### memory_profiler

```bash
pip install memory_profiler

# Add @profile decorator
@profile
def memory_intensive_function():
    # ...

python -m memory_profiler script.py
```

### Optimization Strategies

#### 1. Batch Processing

```python
# Bad: One row at a time
for row in rows:
    process_row(row)

# Good: Batch processing
BATCH_SIZE = 10000
for i in range(0, len(rows), BATCH_SIZE):
    batch = rows[i:i+BATCH_SIZE]
    process_batch(batch)
```

#### 2. SQLite Optimization

```python
# Use transactions for bulk inserts
with conn:
    conn.executemany(
        "INSERT INTO table (col) VALUES (?)",
        [(val,) for val in values]
    )

# Create indices after bulk inserts
conn.execute("CREATE INDEX idx_col ON table(col)")
```

#### 3. Streaming

```python
# Bad: Load entire file
with open(file, 'r') as f:
    data = f.read()  # Memory exhaustion

# Good: Stream file
with open(file, 'r') as f:
    for line in f:
        process_line(line)
```

## Contributing

### Contribution Workflow

1. **Fork Repository**
2. **Create Feature Branch**:
```bash
git checkout -b feature/add-phone-type
```

3. **Make Changes**:
- Write tests first (TDD)
- Implement feature
- Ensure tests pass
- Update documentation

4. **Run Checks**:
```bash
make lint
make test
make fmt
```

5. **Commit Changes**:
```bash
git add .
git commit -m "feat(types): add phone number type detection"
```

6. **Push and Create PR**:
```bash
git push origin feature/add-phone-type
# Create PR on GitHub
```

### Code Review Checklist

- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] No secrets or credentials in code
- [ ] PHI/PII handling follows guidelines
- [ ] Performance considered
- [ ] Backward compatibility maintained

### Release Process

1. Update version in `pyproject.toml` and `package.json`
2. Update CHANGELOG.md
3. Create release branch: `release/v1.1.0`
4. Run full test suite
5. Tag release: `git tag v1.1.0`
6. Push tag: `git push --tags`
7. GitHub Actions will build and publish

---

## FAQ

**Q: How do I add a new statistical test?**

A: Add function in `services/profile.py`, update `NumericStats` model, add tests.

**Q: How do I test with large files?**

A: Use `tests/fixtures/generate_large.py` to create test files, mark tests with `@pytest.mark.slow`.

**Q: How do I debug background tasks?**

A: Use synchronous mode for testing, or add logging at key points.

**Q: How do I update dependencies?**

A: Use `pip-tools` for Python, `npm audit fix` for Node. Test thoroughly.

**Q: How do I handle breaking changes?**

A: Increment major version, provide migration guide, maintain compatibility for one version.

---

For more information:
- [Architecture Documentation](ARCHITECTURE.md)
- [API Documentation](API.md)
- [User Guide](USER_GUIDE.md)
- [Operations Guide](OPERATIONS.md)
