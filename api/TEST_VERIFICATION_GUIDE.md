# Test Verification Guide

## Overview

This guide explains how to verify the complete test suite for the VQ8 Data Profiler after fixes have been applied by the Python Expert and Test Engineer agents.

## Success Criteria

- **Target:** 450/450 tests passing (100% pass rate)
- **Minimum Acceptable:** 427/450 tests passing (95% pass rate)
- **Critical Paths:** All critical functionality tests must pass
- **Zero Errors:** No collection or execution errors

## Verification Tools

### 1. Quick Status Check
For a rapid overview of test status:

```bash
cd /Users/brent/git/data-profiler/api
./check_test_status.sh
```

**Output:**
- Quick summary of pass/fail counts
- Timestamp
- Overall status indicator

**Use when:**
- Checking if other agents are done
- Quick sanity check
- Monitoring during long-running fixes

### 2. Full Verification Suite
For comprehensive verification and reporting:

```bash
cd /Users/brent/git/data-profiler/api
python verify_tests.py
```

**Output:**
- Complete test execution log
- Detailed pass/fail breakdown
- Critical path verification
- Comprehensive final report
- JSON results file

**Use when:**
- Final verification before CI/CD
- Generating official test reports
- Documenting test status

### 3. Failure Analysis
For detailed analysis of remaining failures:

```bash
cd /Users/brent/git/data-profiler/api
python analyze_test_failures.py
```

**Output:**
- Categorized failure list
- Root cause identification
- Priority-ordered fix recommendations
- Detailed error patterns

**Use when:**
- Tests are failing and need investigation
- Identifying remaining work
- Planning fix priority

## Verification Workflow

### Step 1: Wait for Agents to Complete

Monitor for completion signals:
- Python Expert completes implementation fixes
- Test Engineer completes test updates
- Both agents report "DONE" or "COMPLETE"

### Step 2: Initial Status Check

```bash
./check_test_status.sh
```

Expected output if successful:
```
==================================
QUICK TEST STATUS CHECK
==================================
Time: Thu Nov 14 12:00:00 PST 2025

Running quick test check...

450 passed in 7.5s

==================================

✓ STATUS: ALL TESTS PASSING
```

### Step 3: Full Verification

```bash
python verify_tests.py
```

This will:
1. Run complete test suite (450 tests)
2. Verify critical paths individually
3. Generate comprehensive report
4. Save results to JSON

### Step 4: Review Results

Check the final report output:

**Success (100% pass rate):**
```
TEST VERIFICATION REPORT
================================================================================

Tests Run:       450
Expected:        450
Passed:          450
Failed:          0
Errors:          0
Pass Rate:       100.0%

SUCCESS CRITERIA
--------------------------------------------------------------------------------
✓ Target test count:  True  (450/450)
✓ All tests passing:  True  (450/450)
✓ Critical paths:     True

FINAL STATUS: ✓ SUCCESS - READY FOR CI/CD

All 450 tests passing with 100% pass rate.
Critical paths verified successfully.
Test suite is production-ready.
```

**Partial Success (95%+ pass rate):**
```
FINAL STATUS: ⚠ PARTIAL SUCCESS

Pass rate: 96.7% (>= 95% threshold)
Remaining failures: 15
Manual review recommended before CI/CD deployment.
```

**Needs Work (<95% pass rate):**
```
FINAL STATUS: ✗ NEEDS WORK

Pass rate: 87.1% (< 95% threshold)
Failed tests: 58
Error count: 0
Additional fixes required.
```

### Step 5: Handle Failures (if any)

If tests are still failing:

```bash
python analyze_test_failures.py
```

This provides:
- Categorized list of failures
- Root cause identification
- Recommended fix order

**Example output:**
```
FAILURES BY CATEGORY
--------------------------------------------------------------------------------

TypeInferrer API (37 failures)
----------------------------------------
  • tests/test_type_inference.py::test_integers_only
  • tests/test_type_inference.py::test_valid_money_two_decimals
  ... and 35 more

RECOMMENDED FIXES (Priority Order)
--------------------------------------------------------------------------------
1. Fix TypeInferrer API (37 tests)
   - Check services/types.py for correct method names
   - Update tests/test_type_inference.py
```

### Step 6: Report Results

Report final status with:
- Pass rate
- Number of failures (if any)
- Critical path status
- Next steps (if needed)

## Test Categories

### Critical Paths (Must Pass)
- Audit Logging (31 tests)
- Candidate Keys (26 tests)
- Date Validation (29 tests)
- Money Validation (22 tests)
- API Health Checks (2 tests)

### High Priority
- Type Inference (37 tests)
- CSV Parser (28 tests)
- Distinct Counting (30 tests)
- Line Endings (14 tests)

### Integration Tests
- Full Pipeline (42 tests)
- Error Handling (31 tests)
- API Endpoints (23 tests)

## Known Issue Categories

Based on previous analysis, watch for these issue patterns:

### 1. API Signature Mismatches
- **TypeInferrer:** Method name changes (`infer_type` vs `infer`)
- **CSVParser:** Constructor expects `ParserConfig` object
- **DistinctCounter:** Missing `add_batch()` method

### 2. Database Issues
- 500 errors on `/runs` endpoints
- Missing `run_id` in responses
- Database initialization failures

### 3. Missing Modules
- `services.pipeline` module not found
- Import errors in integration tests

## Continuous Monitoring

While agents are working, you can monitor progress:

```bash
# Check every 30 seconds
watch -n 30 './check_test_status.sh'

# Or manually check periodically
./check_test_status.sh
```

## Test Execution Details

### Command Used
```bash
pytest tests/ --ignore=tests/performance -v --tb=short
```

### Exclusions
- Performance tests (require `psutil` package)
- Tests are excluded to avoid dependency issues

### Timeout
- Maximum execution time: 5 minutes
- Typical execution time: 7-10 seconds

### Output Files
- `test_verification_results.json` - Detailed results in JSON
- `test_failure_analysis.txt` - Failure analysis report
- `.coverage` - Code coverage data
- `htmlcov/` - HTML coverage report

## Troubleshooting

### Tests Hang or Timeout
```bash
# Kill hung processes
pkill -f pytest

# Try with single worker
pytest tests/ --ignore=tests/performance -v --tb=short -n 0
```

### Database Errors
```bash
# Clean test database
rm -f test.db

# Re-run tests
python verify_tests.py
```

### Import Errors
```bash
# Verify virtual environment
source .venv/bin/activate
python -c "import services; import models; import routers"
```

### Coverage Issues
```bash
# Clear coverage data
rm -f .coverage
rm -rf htmlcov/

# Run tests with fresh coverage
pytest tests/ --cov=. --cov-report=html
```

## Success Indicators

### 100% Pass Rate Achieved
- All 450 tests passing
- Zero failures
- Zero errors
- Critical paths verified
- Ready for CI/CD pipeline

### Next Steps After Success
1. Generate coverage report
2. Review code quality metrics
3. Update CHANGELOG
4. Tag release
5. Deploy to CI/CD

## Escalation

If verification fails after fixes:

1. **Re-run analysis:**
   ```bash
   python analyze_test_failures.py
   ```

2. **Identify new failure patterns:**
   - Check if issues are different from original
   - Look for regression in fixed areas

3. **Report back to agents:**
   - Provide specific failure details
   - Include error messages
   - Request targeted fixes

4. **Iterate:**
   - Wait for new fixes
   - Re-verify
   - Repeat until success criteria met

## Performance Metrics

### Expected Performance
- **Execution Time:** 7-10 seconds (450 tests)
- **Tests per Second:** 45-64 tests/sec
- **Memory Usage:** < 500 MB
- **Coverage:** > 85% (configured threshold)

### Benchmark Comparison
- **Unit Tests:** < 5 seconds
- **Integration Tests:** < 3 seconds
- **E2E Tests:** < 2 seconds
- **Total:** < 10 seconds

## Additional Resources

- **Test Results Analysis:** `TEST_RESULTS_ANALYSIS.md`
- **Coverage Report:** `htmlcov/index.html`
- **Pytest Configuration:** `pyproject.toml`
- **Test Structure:** `tests/` directory

## Contact

For issues with the verification process:
- Check agent status
- Review error logs
- Re-run with verbose output
- Report anomalies to orchestrator
