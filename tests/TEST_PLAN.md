# Data Profiler Test Plan

## Overview

This test suite follows Test-Driven Development (TDD) principles with the Red-Green-Refactor methodology. All tests were written BEFORE implementation to guide development.

## Test Coverage Goals

- **Overall Coverage**: 85%+ (enforced)
- **Critical Paths**: 100% (parsing, validation)
- **Integration Tests**: End-to-end flows
- **Performance Tests**: 3 GiB+ file handling

## Test Organization

### By Phase (TDD Red-Green-Refactor)

#### Phase 1: RED - Write Failing Tests
All tests in this suite are initially failing (RED) as they define expected behavior before implementation exists.

#### Phase 2: GREEN - Minimal Implementation
Implementation team will write minimal code to make tests pass.

#### Phase 3: REFACTOR - Improve Code Quality
With passing tests as safety net, code can be refactored with confidence.

### By Component

```
tests/
├── test_utf8_validator.py          # UTF-8 validation (Phase 2)
├── test_crlf_detector.py           # CRLF detection (Phase 3)
├── test_csv_parser.py              # CSV parsing (Phase 4)
├── test_type_inference.py          # Type detection (Phase 5)
├── test_money_validator.py         # Money format (Phase 5)
├── test_numeric_validator.py       # Numeric format (Phase 5)
├── test_date_validator.py          # Date validation (Phase 6)
├── test_distinct_counter.py        # Exact distinct counts (Phase 7)
├── test_duplicate_detector.py      # Duplicate detection (Phase 8)
├── test_candidate_keys.py          # Key suggestions (Phase 9)
├── test_error_aggregator.py        # Error roll-up (Phase 10)
├── test_api_endpoints.py           # API testing (Phase 11)
├── test_artifact_generation.py     # Report generation (Phase 12)
└── conftest.py                     # Shared fixtures
```

## Test Categories

### Unit Tests (Fast)
- Individual component testing
- No external dependencies
- Millisecond execution time
- Run frequently during development

**Markers**: `@pytest.mark.unit`

**Run**: `pytest -m unit`

### Integration Tests (Medium)
- Component interaction testing
- File I/O operations
- SQLite database operations
- Multi-second execution time

**Markers**: `@pytest.mark.integration`

**Run**: `pytest -m integration`

### Performance Tests (Slow)
- Large file handling (3 GiB+)
- Streaming validation
- Memory efficiency
- Minutes execution time

**Markers**: `@pytest.mark.slow`

**Run**: `pytest -m "not slow"` (to skip)

## Test Fixtures

### Sample Files (conftest.py)
- `sample_csv_basic` - Simple valid CSV
- `sample_csv_quoted` - Quoted fields with delimiters
- `sample_csv_crlf` - CRLF line endings
- `sample_csv_money_violations` - Money format errors
- `sample_csv_numeric_violations` - Numeric format errors
- `sample_csv_dates` - Various date formats
- `sample_csv_mixed_types` - Mixed column types
- `sample_csv_duplicates` - Duplicate records
- `sample_csv_invalid_utf8` - Invalid UTF-8 bytes
- `sample_csv_jagged` - Inconsistent column counts
- `sample_csv_no_header` - Missing header

### Golden Files (fixtures/)
Production-quality test data covering:
- Quoted commas
- Doubled quotes
- Embedded CRLF
- Money/numeric violations
- Date formats
- Mixed types
- Duplicate records
- Compound keys

## Running Tests

### Basic Test Run
```bash
pytest
```

### With Coverage Report
```bash
pytest --cov=api --cov-report=html
```

### Fast Tests Only
```bash
pytest -m "not slow"
```

### Specific Component
```bash
pytest tests/test_utf8_validator.py -v
```

### Parallel Execution
```bash
pytest -n auto
```

### Using Test Runner Script
```bash
./tests/run_tests.sh                # Full suite with coverage
./tests/run_tests.sh --fast         # Skip slow tests
./tests/run_tests.sh --unit         # Unit tests only
./tests/run_tests.sh --parallel     # Parallel execution
```

## Expected Test Results (RED Phase)

### Current Status: ALL TESTS FAILING ✓
This is correct! Tests define behavior before implementation.

```
Expected Failures:
- test_utf8_validator.py: 13 tests (ModuleNotFoundError: api.services.validators)
- test_crlf_detector.py: 14 tests (ModuleNotFoundError: api.services.validators)
- test_csv_parser.py: 20 tests (ModuleNotFoundError: api.services.parser)
- test_type_inference.py: 28 tests (ModuleNotFoundError: api.services.types)
- test_money_validator.py: 19 tests (ModuleNotFoundError: api.services.validators)
- test_numeric_validator.py: 23 tests (ModuleNotFoundError: api.services.validators)
- test_date_validator.py: 26 tests (ModuleNotFoundError: api.services.validators)
- test_distinct_counter.py: 18 tests (ModuleNotFoundError: api.services.distincts)
- test_duplicate_detector.py: 18 tests (ModuleNotFoundError: api.services.duplicates)
- test_candidate_keys.py: 15 tests (ModuleNotFoundError: api.services.keys)
- test_error_aggregator.py: 21 tests (ModuleNotFoundError: api.services.errors)
- test_api_endpoints.py: 21 tests (ModuleNotFoundError: api.app)
- test_artifact_generation.py: 18 tests (ModuleNotFoundError: api.services.artifacts)

Total: 254 tests (ALL FAILING as expected in RED phase)
```

## Test Success Criteria (GREEN Phase)

Once implementation is complete, all tests should pass with:
- 85%+ code coverage
- No catastrophic errors unhandled
- Performance benchmarks met:
  - 3 GiB file processed in < 10 minutes
  - UTF-8 validation < 1 GB/minute
  - Distinct counting exact (not approximate)

## Critical Test Scenarios

### 1. Catastrophic Errors (Must Stop Processing)
- Invalid UTF-8 byte sequence
- Missing header row
- Inconsistent column count (jagged rows)

**Tests**:
- `test_catastrophic_failure_*` in test_csv_parser.py
- `test_invalid_utf8_*` in test_utf8_validator.py

### 2. Non-Catastrophic Errors (Continue + Report)
- Quoting rule violations
- Unquoted delimiter in field
- Numeric format violations (commas, dollar signs)
- Money format violations (wrong decimals)
- Mixed date formats
- Out-of-range dates

**Tests**: All `test_invalid_*` and `test_error_*` tests

### 3. Exact Metrics (No Approximations)
- Distinct count must be exact
- Duplicate detection must be complete
- Frequency distributions must be accurate

**Tests**:
- `test_exact_counting_guarantee` in test_distinct_counter.py
- `test_duplicate_detection_*` in test_duplicate_detector.py

### 4. Streaming and Memory Efficiency
- Process 3 GiB+ files without loading into memory
- Use SQLite for on-disk storage
- Stream-based validation

**Tests**:
- `test_utf8_validator_streams_large_files`
- `test_large_file_streaming`
- `test_sqlite_storage_for_large_datasets`

## Test Data Requirements

### Small Files (< 1 MB)
For fast unit tests covering logic paths

### Medium Files (1-100 MB)
For integration tests covering typical use cases

### Large Files (3+ GiB)
For performance and streaming tests (marked as `slow`)

## Integration with CI/CD

### Pre-commit Checks
```bash
pytest -m unit --maxfail=1
```

### Pull Request Checks
```bash
pytest -m "not slow" --cov=api --cov-fail-under=85
```

### Nightly/Release Checks
```bash
pytest --cov=api --cov-fail-under=85
```

## Test Maintenance

### Adding New Tests
1. Write test first (RED)
2. Verify test fails for right reason
3. Implement minimal code (GREEN)
4. Refactor with test safety net

### Updating Tests
- Tests define contract/behavior
- Update tests ONLY when requirements change
- Maintain backward compatibility

### Test Smells to Avoid
- ❌ Tests that test implementation details
- ❌ Flaky tests (non-deterministic)
- ❌ Slow tests without `@pytest.mark.slow`
- ❌ Tests with external dependencies (mock them)
- ❌ Tests that modify global state

## Performance Benchmarks

| Operation | Target | Test |
|-----------|--------|------|
| UTF-8 validation | > 1 GB/min | test_utf8_validator_streams_large_files |
| CSV parsing | > 500k rows/min | test_large_file_streaming |
| Distinct counting | Exact, not approx | test_exact_counting_guarantee |
| Duplicate detection | < 10s for 50k rows | test_duplicate_detection_performance_large_file |
| Type inference | < 5s for 100k rows | test_type_inference_sampling_strategy |
| Artifact generation | < 5s for 10k rows | test_artifact_generation_performance |

## Next Steps

### For Implementation Team (Python Specialist)
1. Read all test files to understand expected behavior
2. Start with Phase 2 (UTF-8 validation)
3. Make tests pass ONE AT A TIME
4. Implement minimal code to pass each test
5. Refactor only when tests are green
6. Coordinate with TDD agent for any test clarifications

### For QA Team
1. Review test coverage after implementation
2. Add edge case tests as discovered
3. Performance test with real 3 GiB+ files
4. Security testing for PII handling in logs

### For Documentation Team
1. Document test patterns used
2. Create test data generation scripts
3. Document how to run tests locally
4. Integration test scenarios for manual validation
