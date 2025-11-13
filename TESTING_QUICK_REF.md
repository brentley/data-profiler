# Testing Quick Reference Card

## Quick Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific category
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests
pytest -m e2e              # E2E tests
pytest -m performance      # Performance tests

# Skip slow tests
pytest -m "not slow"

# Stop on first failure
pytest -x

# Run specific file
pytest api/tests/unit/test_parser.py

# Run specific test
pytest api/tests/unit/test_parser.py::test_jagged_row_catastrophic

# Watch mode (TDD)
ptw -- api/tests/unit/

# Parallel execution
pytest -n auto

# Verbose output
pytest -v

# Debug mode
pytest --pdb --showlocals
```

## Test Categories

| Marker | Description | Command |
|--------|-------------|---------|
| `unit` | Unit tests | `pytest -m unit` |
| `integration` | Integration tests | `pytest -m integration` |
| `e2e` | End-to-end tests | `pytest -m e2e` |
| `performance` | Performance tests | `pytest -m performance` |
| `slow` | Tests > 1 second | `pytest -m slow` |

## Coverage Commands

```bash
# Generate HTML report
pytest --cov=api --cov-report=html
open htmlcov/index.html

# Terminal report with missing lines
pytest --cov=api --cov-report=term-missing

# XML report (for CI)
pytest --cov=api --cov-report=xml

# Fail if coverage below 85%
pytest --cov=api --cov-fail-under=85

# Coverage for specific module
pytest --cov=api.services.parser api/tests/unit/test_parser.py
```

## TDD Workflow

```bash
# 1. Write failing test
pytest api/tests/unit/test_parser.py::test_new_feature -x

# 2. Implement feature
# ... edit code ...

# 3. Run test again (should pass)
pytest api/tests/unit/test_parser.py::test_new_feature

# 4. Watch mode for continuous feedback
ptw -- api/tests/unit/test_parser.py
```

## Common Fixtures

```python
def test_example(temp_workspace):
    """Isolated temp workspace."""
    # temp_workspace: pathlib.Path
    pass

def test_example(sample_csv_simple):
    """Sample CSV data."""
    # sample_csv_simple: str
    pass

def test_example(in_memory_db):
    """In-memory SQLite database."""
    # in_memory_db: sqlite3.Connection
    pass

def test_example(memory_profiler, time_profiler):
    """Performance profiling."""
    result = time_profiler(func, *args)
    # result['elapsed_seconds']
    # result['peak_memory_mb']
    pass
```

## Test Structure (AAA)

```python
def test_something():
    """Test description."""
    # Arrange - Setup
    data = setup_data()

    # Act - Execute
    result = function_under_test(data)

    # Assert - Verify
    assert result.is_valid is True
```

## Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("valid", True),
    ("invalid", False),
])
def test_validation(input, expected):
    """Test with multiple inputs."""
    result = validate(input)
    assert result == expected
```

## Error Testing

```python
def test_error():
    """Test error handling."""
    with pytest.raises(CustomError) as exc:
        function_that_raises()

    assert exc.value.code == "ERROR_CODE"
    assert "message" in str(exc.value)
```

## Key Test Locations

```
api/tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (70%)
│   ├── test_utf8.py            # UTF-8 validation
│   ├── test_crlf.py            # Line endings
│   ├── test_parser.py          # CSV parsing
│   └── ...
├── integration/             # Integration tests (20%)
│   └── test_full_pipeline.py   # Complete pipeline
├── performance/             # Performance tests
│   └── test_large_files.py     # Large files
└── ...

tests/e2e/                   # E2E tests (10%)
└── test_user_workflows.py   # User workflows
```

## Performance Targets

| Test | Target |
|------|--------|
| 3 GiB file | < 10 minutes |
| 100k rows | < 30 seconds |
| 250 columns | < 2 minutes |
| Throughput | > 10k rows/sec |
| Memory (3GB) | < 2 GB |

## Critical Error Codes

| Code | Type | Behavior |
|------|------|----------|
| `E_UTF8_INVALID` | Catastrophic | Stop immediately |
| `E_HEADER_MISSING` | Catastrophic | Stop immediately |
| `E_JAGGED_ROW` | Catastrophic | Stop immediately |
| `E_QUOTE_RULE` | Non-catastrophic | Continue, count |
| `E_MONEY_FORMAT` | Non-catastrophic | Continue, count |
| `W_DATE_MIXED_FORMAT` | Warning | Continue, warn |

## Documentation

- **Strategy**: `/docs/TEST_STRATEGY.md`
- **QA Report**: `/docs/QA_REPORT.md`
- **Summary**: `/TEST_SUITE_SUMMARY.md`
- **README**: `/api/tests/README.md`

## CI/CD

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: pytest --cov=api --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | `export PYTHONPATH="${PYTHONPATH}:$(pwd)"` |
| Slow tests | `pytest -n auto` (parallel) |
| Fixtures not found | Check `conftest.py` location |
| Coverage not collecting | Verify `pytest.ini` config |

## Getting Help

1. Check `/api/tests/README.md`
2. Review similar tests in `/api/tests/`
3. Check `/docs/QA_REPORT.md` for known issues
4. Examine fixtures in `/api/tests/conftest.py`

---

**Print this for quick reference during development!**
