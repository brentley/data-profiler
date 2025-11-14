# Test Fixes Summary

## Status: In Progress

This document tracks test file fixes needed to align with the actual API implementation completed by the Python Expert.

## Completed Fixes

### test_api_endpoints.py ✅
**File**: `/Users/brent/git/data-profiler/tests/test_api_endpoints.py`

**Changes Made**:
1. ✅ Fixed `test_healthz_endpoint()` - Updated to match HealthResponse model
   - Changed from expecting `{"status": "OK"}`
   - To checking `status == "ok"` plus `timestamp` and `version` fields

2. ✅ Removed duplicate `api_client` fixture
   - Was defined in both conftest.py and test file
   - Kept the one in conftest.py which includes workspace setup

3. ✅ Fixed `test_confirm_keys()` request structure
   - Changed from nested arrays: `{"keys": [["ID"], ["ID", "Name"]]}`
   - To flat list: `{"keys": ["ID", "Name"]}`
   - Matches ConfirmKeysRequest model which expects `List[str]`

4. ✅ Fixed `test_confirm_keys_invalid_columns()` request structure
   - Same fix as above: flat list instead of nested arrays

### test_type_inference.py ✅
**File**: `/Users/brent/git/data-profiler/tests/test_type_inference.py`

**Status**: No changes needed
- All imports are correct (uses TypeInferrer not TypeInferencer)
- Test structure aligns with actual implementation
- ColumnTypeInfo and TypeInferenceResult are correctly imported

## Tests Needing Complete Rewrite

### test_candidate_keys.py ⚠️
**File**: `/Users/brent/git/data-profiler/tests/test_candidate_keys.py`

**Issue**: API mismatch between test expectations and implementation

**Expected (in tests)**:
```python
from api.services.keys import CandidateKeyFinder

finder = CandidateKeyFinder()
suggestions = finder.suggest_keys(csv_path, delimiter="|")
```

**Actual Implementation**:
```python
from api.services.keys import CandidateKeyAnalyzer

analyzer = CandidateKeyAnalyzer()
candidates = analyzer.suggest_candidates(
    column_stats={"col1": {"distinct_count": 100, "total_count": 100, "null_count": 0}},
    pair_stats=None,
    triple_stats=None
)
```

**What Needs to Change**:
- CandidateKeyAnalyzer works with pre-computed statistics dictionaries
- Does not read CSV files directly
- Returns dictionaries, not objects with attributes
- Suggestions come from the API endpoint `/runs/{run_id}/candidate-keys` which computes stats from profiles

**Recommendation**:
1. Either rewrite tests to work with statistics dictionaries
2. Or test the API endpoint instead of the service class directly
3. Or create a wrapper class CandidateKeyFinder that reads CSVs and calls CandidateKeyAnalyzer

## Tests Verified as Compatible

The following test files have been checked and appear compatible with the implementation:

- [x] **test_distinct_counter.py** ✅
  - All imports correct (uses DistinctCounter, DistinctCountResult)
  - Return attributes match implementation
  - count_distincts() method exists
  - DistinctCountResult has all expected fields: distinct_count, total_count, null_count, empty_count, cardinality_ratio, frequencies, storage_method, spill_file_path, is_exact
  - get_top_n() method exists
  - No changes needed

- [x] **test_type_inference.py** ✅
  - All imports correct
  - No changes needed

## Tests Pending Review

The following test files have not been checked yet for compatibility issues:

- [ ] test_artifact_generation.py
- [ ] test_crlf_detector.py
- [ ] test_csv_parser.py
- [ ] test_date_validator.py
- [ ] test_duplicate_detector.py
- [ ] test_error_aggregator.py
- [ ] test_money_validator.py
- [ ] test_numeric_validator.py
- [ ] test_utf8_validator.py
- [ ] e2e/test_full_workflow.py
- [ ] e2e/test_user_workflows.py

## Next Steps

1. **Immediate**: Check remaining test files for import/API mismatches
2. **Short-term**: Decide on approach for test_candidate_keys.py rewrite
3. **Medium-term**: Run pytest to identify remaining failures
4. **Long-term**: Achieve >85% test coverage target

## Known Good Patterns

### Correct Imports ✅
```python
from api.services.types import TypeInferrer, TypeInferenceResult, ColumnTypeInfo
from api.services.ingest import UTF8Validator, CRLFDetector, CSVParser
from api.services.keys import CandidateKeyAnalyzer, DuplicateDetector
```

### API Client Usage ✅
```python
def test_example(api_client):  # Fixture from conftest.py
    response = api_client.post("/runs", json={"delimiter": "|"})
    assert response.status_code == 201
```

### Health Check ✅
```python
response = api_client.get("/healthz")
data = response.json()
assert data["status"] == "ok"
assert "timestamp" in data
assert "version" in data
```
