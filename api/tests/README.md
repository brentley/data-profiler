# VQ8 Data Profiler Test Suite

## Overview

This directory contains the comprehensive test suite for the VQ8 Data Profiler. The tests follow Test-Driven Development (TDD) principles and provide extensive coverage across unit, integration, and E2E layers.

## Quick Start

### Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or with development dependencies
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html

# Open coverage report
open htmlcov/index.html
```

## Test Structure

```
api/tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (70%)
│   ├── test_utf8.py            # UTF-8 validation
│   ├── test_crlf.py            # Line ending detection
│   ├── test_parser.py          # CSV parsing
│   ├── test_types.py           # Type inference
│   ├── test_money.py           # Money validation
│   ├── test_numeric.py         # Numeric validation
│   ├── test_date.py            # Date detection
│   ├── test_distincts.py       # Distinct counting
│   ├── test_keys.py            # Candidate keys
│   ├── test_duplicates.py      # Duplicate detection
│   ├── test_errors.py          # Error aggregation
│   └── test_statistics.py      # Statistics computation
├── integration/             # Integration tests (20%)
│   ├── test_full_pipeline.py   # Complete pipeline
│   ├── test_api_endpoints.py   # API integration
│   ├── test_sqlite_storage.py  # Database integration
│   └── test_streaming.py       # Streaming behavior
├── performance/             # Performance tests (10%)
│   ├── test_large_files.py     # Large file processing
│   └── test_scalability.py     # Scalability benchmarks
└── scenarios/               # Error scenario tests
    ├── test_catastrophic.py    # Catastrophic errors
    └── test_non_catastrophic.py # Non-catastrophic errors
```

## Test Categories

### Unit Tests

Test individual components in isolation.

```bash
# Run all unit tests
pytest -m unit

# Run specific module
pytest api/tests/unit/test_parser.py

# Run specific test
pytest api/tests/unit/test_parser.py::TestCSVParserRows::test_jagged_row_catastrophic
```

**Key Modules**:
- **test_utf8.py**: UTF-8 stream validation, encoding detection
- **test_crlf.py**: Line ending detection and normalization
- **test_parser.py**: CSV parsing, quoting rules, error handling
- **test_types.py**: Type inference (numeric, money, date, code)
- **test_money.py**: Money format validation (2 decimals, no symbols)
- **test_date.py**: Date format detection and consistency

### Integration Tests

Test component interaction and complete workflows.

```bash
# Run all integration tests
pytest -m integration

# Run pipeline tests
pytest api/tests/integration/test_full_pipeline.py
```

**Key Tests**:
- Complete upload → process → download flow
- Error propagation through pipeline
- State transitions and management
- Resource cleanup and isolation

### Performance Tests

Validate performance targets and scalability.

```bash
# Run performance tests
pytest -m performance

# Skip slow tests during development
pytest -m "not slow"

# Run with benchmarks
pytest -m performance --benchmark-only
```

**Targets**:
- 3 GiB file: < 10 minutes
- 100k rows: < 30 seconds
- 250 columns: < 2 minutes
- Memory: < 2 GB for 3 GB file
- Throughput: > 10k rows/sec

### E2E Tests

Test complete user workflows end-to-end.

```bash
# Run E2E tests
pytest -m e2e

# Run specific workflow
pytest tests/e2e/test_user_workflows.py::TestCompleteUserWorkflow::test_happy_path_upload_to_download
```

## Test Execution Patterns

### TDD Workflow

```bash
# 1. Write a failing test
pytest api/tests/unit/test_parser.py::test_new_feature -x

# 2. Implement feature to pass test
# ... edit code ...

# 3. Run test again
pytest api/tests/unit/test_parser.py::test_new_feature

# 4. Watch mode for continuous feedback
ptw -- api/tests/unit/test_parser.py
```

### Coverage Analysis

```bash
# Generate coverage report
pytest --cov=api --cov-report=html --cov-report=term-missing

# Check specific module coverage
pytest --cov=api.services.ingest --cov-report=term-missing api/tests/unit/test_utf8.py

# Fail if coverage below threshold
pytest --cov=api --cov-fail-under=85
```

### Parallel Execution

```bash
# Run tests in parallel (4 workers)
pytest -n 4

# Auto-detect number of CPUs
pytest -n auto

# Parallel with coverage (requires pytest-cov>=2.10.0)
pytest -n auto --cov=api
```

## Fixtures

### Workspace Fixtures

```python
def test_example(temp_workspace, temp_db_path):
    """Test with isolated workspace."""
    # temp_workspace: pathlib.Path to temp directory
    # temp_db_path: pathlib.Path to temp SQLite database
    assert temp_workspace.exists()
```

### Data Fixtures

```python
def test_with_sample_data(sample_csv_simple, sample_csv_with_nulls):
    """Test with predefined sample data."""
    # sample_csv_simple: str with basic CSV content
    # sample_csv_with_nulls: str with null values
    assert len(sample_csv_simple) > 0
```

### Performance Fixtures

```python
def test_performance(memory_profiler, time_profiler):
    """Test with performance profiling."""
    result = time_profiler(my_function, arg1, arg2)
    assert result['elapsed_seconds'] < 1.0

    mem_result = memory_profiler(my_function, arg1, arg2)
    assert mem_result['peak_memory_mb'] < 100
```

## Writing New Tests

### Test Naming Convention

```python
# Good test names - descriptive and clear
def test_valid_utf8_with_multibyte_characters():
    """Valid UTF-8 with multibyte characters should pass."""
    pass

def test_jagged_row_stops_immediately():
    """Jagged row should stop processing immediately."""
    pass

# Bad test names - vague
def test_utf8():
    pass

def test_parser():
    pass
```

### Test Structure (AAA Pattern)

```python
def test_example():
    """Test description."""
    # Arrange - Set up test data and conditions
    data = b"test data"
    validator = UTF8Validator(BytesIO(data))

    # Act - Execute the code being tested
    result = validator.validate()

    # Assert - Verify the results
    assert result.is_valid is True
    assert result.error is None
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input_data,expected", [
    (b"valid", True),
    (b"\xFF\xFF", False),
    (b"", True),
])
def test_utf8_validation(input_data, expected):
    """Test UTF-8 validation with various inputs."""
    validator = UTF8Validator(BytesIO(input_data))
    result = validator.validate()
    assert result.is_valid == expected
```

### Error Testing

```python
def test_catastrophic_error():
    """Test catastrophic error handling."""
    with pytest.raises(ParserError) as exc_info:
        parser.parse()

    assert exc_info.value.code == 'E_JAGGED_ROW'
    assert exc_info.value.is_catastrophic is True
    assert 'line 2' in str(exc_info.value)
```

## Markers

Tests can be marked for selective execution:

```python
@pytest.mark.unit
def test_unit():
    """Unit test."""
    pass

@pytest.mark.integration
def test_integration():
    """Integration test."""
    pass

@pytest.mark.slow
def test_slow():
    """Test that takes >1 second."""
    pass

@pytest.mark.performance
@pytest.mark.slow
def test_large_file():
    """Performance test with large file."""
    pass
```

Run specific markers:

```bash
pytest -m unit           # Unit tests only
pytest -m "not slow"     # Exclude slow tests
pytest -m "unit and not slow"  # Fast unit tests only
```

## Continuous Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run tests
        run: pytest --cov=api --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests Fail to Import Modules

```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install package in development mode
pip install -e .
```

### Fixtures Not Found

```bash
# Ensure conftest.py is in the correct location
# Pytest discovers conftest.py in the test directory hierarchy
ls api/tests/conftest.py
```

### Slow Test Execution

```bash
# Identify slow tests
pytest --durations=10

# Run in parallel
pytest -n auto

# Use testmon for smart test selection
pytest --testmon
```

### Coverage Not Collecting

```bash
# Ensure source path is correct
pytest --cov=api --cov-report=term

# Check pytest.ini [coverage:run] configuration
cat pytest.ini
```

## Best Practices

### ✅ Do

- Write tests before implementation (TDD)
- Test one thing per test
- Use descriptive test names
- Clean up resources in fixtures
- Parametrize similar tests
- Use appropriate markers
- Keep tests independent
- Mock external dependencies

### ❌ Don't

- Write tests that depend on other tests
- Use sleep() for timing (use proper waiting)
- Test implementation details
- Copy-paste test code (use fixtures/helpers)
- Ignore flaky tests
- Skip tests without good reason
- Hard-code paths or values
- Leave resource leaks

## Resources

- **Test Strategy**: `/docs/TEST_STRATEGY.md`
- **QA Report**: `/docs/QA_REPORT.md`
- **Pytest Docs**: https://docs.pytest.org/
- **Coverage Docs**: https://coverage.readthedocs.io/

## Support

For questions or issues with the test suite:

1. Check the QA Report for known issues
2. Review test strategy documentation
3. Examine similar existing tests
4. Consult with QA Engineer agent

## Maintenance

### Updating Fixtures

Edit `conftest.py` to add or modify shared fixtures.

### Adding Test Categories

Add markers to `pytest.ini`:

```ini
[pytest]
markers =
    your_marker: Description of marker
```

### Performance Baselines

Update performance targets in `/docs/TEST_STRATEGY.md` after establishing baselines.

---

**Last Updated**: 2025-11-13
**Test Framework Version**: 1.0.0
**Pytest Version**: 7.4.0+
