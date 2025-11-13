# Performance Testing

This directory contains performance tests and utilities for validating data profiler performance with large files.

## Issue #31: Performance Test with 3+ GiB Files

Validates performance with large files matching spec requirements:
- 3+ GiB files
- 250+ columns
- Millions of rows
- Streaming behavior (no full file load)
- Memory usage constraints
- SQLite spill for distinct counting

## Quick Start

### Generate a 3+ GiB Test File

```bash
# Generate 3+ GB file with 250 columns (default)
python generate_large_file.py \
    --output /tmp/large_test.csv \
    --target-size-gb 3.2 \
    --columns 250

# Or specify exact row count
python generate_large_file.py \
    --output /tmp/large_test.csv \
    --rows 10000000 \
    --columns 250
```

### Run Performance Tests

```bash
# Full test (generation + validation)
python run_large_file_test.py \
    --rows 10000000 \
    --columns 250 \
    --target-size-gb 3.2 \
    --output-report performance_results.json

# Use existing file
python run_large_file_test.py \
    --existing-file /tmp/large_test.csv \
    --output-report performance_results.json
```

### Run Comprehensive Test Suite (once ProfilePipeline exists)

```bash
# All performance tests
pytest tests/performance/ -v -s -m performance

# Specific test
pytest tests/performance/test_large_files.py::TestLargeFilePerformance::test_3gb_file_processing -v -s

# Skip slow tests
pytest tests/performance/ -v -m "performance and not slow"
```

## Test Files

### `generate_large_file.py`
Utility for generating large CSV test files with configurable:
- Row count
- Column count
- Data types (numeric, text, money, dates, categories)
- Mixed data types for realistic testing
- Pipe-delimited format

**Features:**
- Efficient buffered writing
- Progress reporting
- Size estimation
- Statistics output
- Configurable buffer size

**Usage:**
```bash
python generate_large_file.py --help
```

### `run_large_file_test.py`
Standalone performance validation script that tests core services:
- File generation with size validation
- Streaming ingestion performance
- Type inference performance
- Memory usage monitoring
- Throughput measurement

**Tests:**
1. **File Generation**: Create 3+ GB file with 250 columns
2. **Basic Ingestion**: Streaming read with memory monitoring
3. **Type Inference**: Sample-based type detection

**Metrics Tracked:**
- Wall-clock time
- Peak memory usage
- Memory range (validates streaming)
- Throughput (rows/second)
- File size

**Acceptance Criteria:**
- [ ] 3+ GiB file generated
- [ ] 250+ columns
- [ ] Streaming behavior (memory range < 500MB)
- [ ] Memory usage < 2GB
- [ ] Throughput > 10k rows/sec

**Usage:**
```bash
python run_large_file_test.py --help
```

### `test_large_files.py`
Comprehensive pytest-based performance test suite (requires ProfilePipeline):
- 3 GB file processing test
- 250 column file test
- Millions of rows test
- Streaming behavior validation
- SQLite spill verification
- Compressed file performance
- Scalability benchmarks
- Memory constraints validation

**Test Classes:**
- `TestLargeFilePerformance`: Core large file tests
- `TestScalabilityBenchmarks`: Scaling tests (rows/columns)
- `TestMemoryConstraints`: Memory usage validation

## Performance Targets

Based on spec requirements:

| Metric | Target | Notes |
|--------|--------|-------|
| File Size | 3+ GiB | Minimum test size |
| Columns | 250+ | Wide table support |
| Throughput | 10k+ rows/sec | Laptop performance |
| Peak Memory | < 2 GB | Streaming, not full load |
| Memory Range | < 500 MB | Constant memory usage |
| Wall-Clock Time | < 10 min | For 3 GB file on laptop |

## Architecture

### Streaming Design
All processing uses streaming to avoid loading entire files into memory:

1. **CSVIngestor**: Yields rows one at a time
2. **TypeInferenceEngine**: Samples rows, doesn't store all
3. **DistinctTracker**: SQLite-backed, spills to disk
4. **ProfileEngine**: Processes rows in single pass

### Memory Management
- Buffered file I/O (configurable buffer size)
- Generator-based row iteration
- SQLite for high-cardinality distinct counting
- Periodic memory sampling during tests

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Ensure psutil is installed for memory monitoring
pip install psutil
```

### Standalone Tests (No Pipeline Required)
```bash
# Quick validation (small file)
python run_large_file_test.py \
    --rows 100000 \
    --columns 50

# Full 3+ GB test
python run_large_file_test.py \
    --rows 10000000 \
    --columns 250 \
    --target-size-gb 3.2
```

### Full Test Suite (Requires ProfilePipeline)
```bash
# All performance tests
pytest tests/performance/ -v -s

# Only fast tests
pytest tests/performance/ -v -m "performance and not slow"

# Specific test
pytest tests/performance/test_large_files.py::TestLargeFilePerformance::test_250_column_file -v -s
```

## Interpreting Results

### Successful Test
```
ACCEPTANCE CRITERIA:
  ✓ 3+ GiB file generated: PASS
  ✓ 250+ columns: PASS
  ✓ Streaming behavior (memory < 500MB range): PASS
  ✓ Memory usage < 2GB: PASS
  ✓ Throughput > 10k rows/sec: PASS

Overall: PASS
```

### Performance Issues

**High Memory Usage**
- Check memory_range_mb: Should be < 500 MB
- If high, indicates non-streaming behavior
- Review code for buffering/caching

**Low Throughput**
- Check rows/sec: Should be > 10k
- Profile CPU usage
- Check I/O performance
- Review parsing logic

**Long Wall-Clock Time**
- For 3 GB file: Should be < 10 minutes
- Check throughput first
- Profile bottlenecks
- Consider parallelization

## File Size Estimation

Approximate file sizes for planning:

| Rows | Columns | Avg Bytes/Row | File Size |
|------|---------|---------------|-----------|
| 1M | 50 | ~320 | ~305 MB |
| 1M | 250 | ~1280 | ~1.2 GB |
| 5M | 50 | ~320 | ~1.5 GB |
| 10M | 50 | ~320 | ~3.1 GB |
| 10M | 250 | ~1280 | ~12.2 GB |
| 3M | 250 | ~1280 | ~3.7 GB |

**Formula:** `file_size_bytes ≈ rows × columns × 5.12`

This is approximate - actual size depends on data types and values.

## Troubleshooting

### Out of Disk Space
Large test files require significant disk space. Use `--workspace` to specify a location with enough space:

```bash
python run_large_file_test.py \
    --workspace /path/to/large/disk \
    --rows 10000000 \
    --columns 250
```

### Memory Errors
If tests run out of memory:
1. Check that streaming is working (memory_range_mb should be small)
2. Reduce sample size for type inference
3. Check for memory leaks
4. Monitor with `top` or `htop` during test

### Slow Generation
File generation can be slow for very large files:
- Expected: ~100k-200k rows/sec
- 10M rows ≈ 50-100 seconds
- Use `--buffer-size` to tune (default 1MB)
- Generate once, reuse with `--existing-file`

## CI/CD Integration

Performance tests are marked with `@pytest.mark.performance` and `@pytest.mark.slow` for CI filtering:

```bash
# Skip slow tests in CI
pytest -m "not slow"

# Run only performance tests
pytest -m performance

# Run all tests (including slow ones)
pytest
```

## Future Enhancements

- [ ] Parallel processing benchmarks
- [ ] Network I/O performance (S3, HTTP)
- [ ] Compression performance (gzip, bzip2, xz)
- [ ] Different delimiters performance
- [ ] Profile visualization
- [ ] Comparative benchmarking
- [ ] Regression detection
