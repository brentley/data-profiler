# VQ8 Data Profiler - Comprehensive Test Strategy

## Overview

This document outlines the complete testing strategy for the VQ8 Data Profiler, covering all layers from unit tests to end-to-end integration tests. The strategy follows Test-Driven Development (TDD) principles and targets 85%+ code coverage.

## Testing Pyramid

```
        /\
       /E2E\       (10%) - Full user workflows
      /------\
     /  INT   \    (20%) - API + Service integration
    /----------\
   /    UNIT    \  (70%) - Component-level tests
  /--------------\
```

### Test Distribution
- **Unit Tests**: 70% - Fast, isolated component tests
- **Integration Tests**: 20% - Service and API integration
- **E2E Tests**: 10% - Full workflow validation

## Test Categories

### 1. Unit Tests (api/tests/unit/)

#### 1.1 UTF-8 Validation (`test_utf8.py`) ✅ STARTED
- Valid ASCII text
- Valid UTF-8 multibyte characters
- Invalid UTF-8 at various positions
- Continuation byte errors
- Truncated sequences
- BOM handling
- Overlong encoding rejection
- Large stream performance

#### 1.2 CRLF Detection (`test_crlf.py`)
- CRLF detection (\\r\\n)
- LF detection (\\n)
- Mixed line endings
- CR-only detection (\\r)
- Normalization to \\n internally
- Recording of original line ending style
- Performance with large files

#### 1.3 CSV Parser (`test_parser.py`)
- Header parsing and validation
- Constant column count enforcement
- Delimiter detection (| and ,)
- Quoting rules validation
- Embedded delimiter handling
- Embedded CRLF in quoted fields
- Double-quote escaping
- Jagged row detection
- Empty fields
- Quote-only fields
- Malformed quotes

#### 1.4 Type Inference (`test_types.py`)
- Alpha/Varchar detection
- Code field detection
- Numeric type (digits + optional decimal)
- Money type (exactly 2 decimals)
- Date detection and format consistency
- Mixed type detection
- Unknown type handling
- Null handling per type

#### 1.5 Money Rules (`test_money.py`)
- Two decimal validation
- Disallowed symbols ($, ,, parentheses)
- Violation counting
- Exclusion from stats when invalid
- Edge cases (negative, zero)
- Large amounts
- Precision edge cases

#### 1.6 Numeric Rules (`test_numeric.py`)
- Digit-only validation
- Optional decimal point
- Rejection of formatted numbers (commas)
- Rejection of currency symbols
- Scientific notation handling
- Negative numbers
- Zero values
- Very large/small numbers

#### 1.7 Date Detection (`test_date.py`)
- YYYYMMDD preferred format
- Alternative format detection
- Format consistency per column
- Out-of-range detection (< 1900, > current+1)
- Null handling
- Invalid format counting
- Mixed format errors
- Leap year handling
- Date parsing edge cases

#### 1.8 Exact Distinct Counting (`test_distincts.py`)
- SQLite-based exact counting
- Spill to disk behavior
- Top-10 value tracking
- Frequency counting
- High cardinality handling
- Memory efficiency
- Performance with millions of distincts

#### 1.9 Candidate Key Suggestion (`test_keys.py`)
- Single column candidates
- Compound key suggestions
- Scoring algorithm (distinct_ratio * (1 - null_ratio_sum))
- Tie-breaker logic
- Top-K selection
- Confirmation workflow
- Duplicate detection trigger

#### 1.10 Duplicate Detection (`test_duplicates.py`)
- Single column duplicate finding
- Compound key duplicate detection
- Hash-based duplicate checking
- Performance with large datasets
- Exact duplicate counting
- Duplicate record reporting

#### 1.11 Error Aggregation (`test_errors.py`)
- Error code generation
- Error counting and roll-up
- Catastrophic vs non-catastrophic classification
- Error message formatting
- Error position tracking
- Warning vs error distinction

#### 1.12 Statistics Computation (`test_statistics.py`)
- Welford's algorithm for mean/stddev
- Exact quantile computation (p1, p5, p25, p50, p75, p95, p99)
- Histogram generation (exact bins)
- Gaussian test (D'Agostino/Pearson)
- Median calculation
- Min/max tracking
- Length statistics (min/max/avg)
- Character set analysis

### 2. Integration Tests (api/tests/integration/)

#### 2.1 Full Pipeline (`test_pipeline_integration.py`)
- Upload → Parse → Profile → Artifacts
- Multi-column file processing
- Error propagation through pipeline
- State transitions
- Progress tracking
- Cancellation handling

#### 2.2 API Endpoints (`test_api_integration.py`)
- POST /runs (create run)
- POST /runs/{id}/upload (file upload)
- GET /runs/{id}/status (polling)
- GET /runs/{id}/profile (JSON retrieval)
- GET /runs/{id}/metrics.csv (CSV download)
- GET /runs/{id}/report.html (HTML download)
- GET /runs/{id}/candidate-keys (suggestions)
- POST /runs/{id}/confirm-keys (confirmation)

#### 2.3 SQLite Storage (`test_sqlite_integration.py`)
- Run metadata storage
- Column profile persistence
- Error/warning storage
- Candidate key storage
- Temp table creation/cleanup
- Index performance
- Concurrent access handling

#### 2.4 Streaming Behavior (`test_streaming.py`)
- No full file load into memory
- Chunk-based processing
- Memory usage validation
- Spill to disk verification
- Resource cleanup

### 3. Performance Tests (api/tests/performance/)

#### 3.1 Large File Tests (`test_large_files.py`)
- 3 GiB+ file processing
- 250+ column files
- Millions of rows
- Wall-clock time measurement
- Memory usage profiling
- CPU utilization
- Disk I/O monitoring

#### 3.2 Scalability Tests (`test_scalability.py`)
- Progressive file size testing
- Column count scaling
- Row count scaling
- Distinct value scaling
- Performance regression detection

### 4. Error Scenario Tests (api/tests/scenarios/)

#### 4.1 Catastrophic Errors (`test_catastrophic.py`)
- Invalid UTF-8 → immediate stop
- Missing header → immediate stop
- Jagged rows → immediate stop
- Proper error messages
- Clean resource cleanup

#### 4.2 Non-Catastrophic Errors (`test_non_catastrophic.py`)
- Quoting violations → continue
- Format violations → continue, count
- Date inconsistencies → warn
- Numeric format issues → exclude
- Error roll-up validation

#### 4.3 Edge Cases (`test_edge_cases.py`)
- Empty files
- Single row files
- Single column files
- All-null columns
- All-distinct columns
- All-duplicate columns
- Unicode edge cases
- Very long field values
- Binary content detection

### 5. End-to-End Tests (tests/e2e/)

#### 5.1 User Workflows (`test_workflows.py`)
- Complete upload flow
- Progress monitoring
- Results viewing
- Error handling display
- Candidate key workflow
- Artifact downloads
- Multi-run management

#### 5.2 Frontend Integration (`test_frontend.py`)
- Upload form submission
- Status polling
- Toast notifications
- Error roll-up display
- Per-column card rendering
- Dark mode compatibility
- Responsive design validation

#### 5.3 Sample Files (`test_samples.py`)
- Process golden file samples
- Validate against expected profiles
- Regression detection
- Format variation coverage

## Test Data Management

### Golden Files (examples/)
- `simple_pipe.txt` - Basic pipe-delimited
- `quoted_commas.csv` - Comma with embedded quotes
- `money_violations.csv` - Money format edge cases
- `date_formats.csv` - Various date formats
- `mixed_types.csv` - Type inference challenges
- `large_sample.txt.gz` - Compressed file test
- `utf8_multibyte.csv` - International characters
- `edge_cases.csv` - Boundary conditions

### Test Data Generators (api/tests/fixtures/)
- Random data generation
- Controlled error injection
- Cardinality control
- Null percentage control
- Type distribution control

## Test Infrastructure

### Fixtures (api/tests/conftest.py)
```python
@pytest.fixture
def temp_workspace():
    """Isolated workspace for each test."""

@pytest.fixture
def sample_csv():
    """Standard test CSV data."""

@pytest.fixture
def large_file_generator():
    """Generate large test files on demand."""

@pytest.fixture
def mock_sqlite_db():
    """In-memory SQLite for fast tests."""

@pytest.fixture
def api_client():
    """FastAPI test client."""
```

### Test Utilities (api/tests/utils/)
- `csv_generator.py` - Create test CSV files
- `data_factory.py` - Generate realistic data
- `assertions.py` - Custom assertions
- `matchers.py` - Custom matchers
- `profilers.py` - Memory/time profilers

## Coverage Requirements

### Overall Target: 85%+

#### Critical Paths: 95%+
- UTF-8 validation
- CSV parsing
- Type inference
- Error handling
- API endpoints

#### Standard Components: 85%+
- Statistics computation
- Candidate keys
- Storage operations
- Report generation

#### UI Components: 70%+
- Frontend components
- Visual elements
- User interactions

## CI/CD Integration

### GitHub Actions Workflow
```yaml
test:
  - Unit tests (parallel)
  - Integration tests (sequential)
  - Coverage report
  - Performance benchmarks

quality-gates:
  - Coverage >= 85%
  - No critical security issues
  - Performance within limits
  - All E2E tests pass
```

## Test Execution

### Local Development
```bash
# Run all tests
make test

# Run specific category
pytest api/tests/unit/
pytest api/tests/integration/
pytest tests/e2e/

# With coverage
pytest --cov=api --cov-report=html

# Performance tests
pytest api/tests/performance/ --benchmark

# Watch mode for TDD
ptw -- api/tests/
```

### Docker Environment
```bash
# Full test suite in Docker
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Integration tests with services
docker-compose -f docker-compose.test.yml run --rm api pytest api/tests/integration/
```

## Success Criteria

### Test Quality Metrics
- ✅ 85%+ code coverage
- ✅ All critical paths covered
- ✅ Zero flaky tests
- ✅ Fast feedback (<5 min for unit tests)
- ✅ Comprehensive error scenarios
- ✅ Performance benchmarks established
- ✅ Golden file regression suite

### Test Documentation
- ✅ Clear test names
- ✅ Docstrings for complex tests
- ✅ Inline comments for non-obvious assertions
- ✅ README in each test directory
- ✅ Test strategy document (this file)

### Continuous Improvement
- Regular test review and refactoring
- Performance benchmark tracking
- Flaky test elimination
- Coverage gap analysis
- Test execution time optimization

## Next Steps

1. **Phase 1**: Complete unit tests for core validators
2. **Phase 2**: API integration tests
3. **Phase 3**: Performance test framework
4. **Phase 4**: E2E workflow tests
5. **Phase 5**: Golden file regression suite
6. **Phase 6**: CI/CD integration
7. **Phase 7**: Test documentation and handoff

## Notes

- All tests follow TDD: Write test first, implement to pass
- Tests are independent and can run in any order
- No test should depend on another test's state
- Clean up all resources in teardown/fixtures
- Use factories/fixtures for test data, not hard-coded values
- Mock external dependencies, test real integration separately
