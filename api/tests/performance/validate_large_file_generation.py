"""
Large File Generation Validation for Issue #31.

This script validates that we can generate 3+ GiB test files
with 250 columns as required by the spec. Once the ProfilePipeline
is implemented, use run_large_file_test.py for full performance testing.

Current status: File generation validated, profiling pending pipeline implementation.
"""

import argparse
import sys
from pathlib import Path
import time


def validate_file_generation():
    """Validate large file generation capability."""
    from generate_large_file import LargeFileGenerator

    print("=" * 70)
    print("PERFORMANCE TEST VALIDATION - GitHub Issue #31")
    print("=" * 70)
    print()
    print("Objective: Validate performance with 3+ GiB files, 250 columns")
    print()

    # Test 1: Generate a 3+ GB file with 250 columns
    print("TEST 1: Generate 3+ GiB file with 250 columns")
    print("-" * 70)

    output_dir = Path("/tmp/data-profiler-perf-test")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "large_test_3gb_250col.csv"

    print(f"Output file: {output_file}")
    print()

    # Estimate rows needed for 3+ GB with 250 columns
    # Approximate: 250 columns * 5.12 bytes/column = ~1280 bytes/row
    # For 3.2 GB: 3.2 * 1024^3 / 1280 = ~2.6M rows
    target_rows = 2_600_000
    target_cols = 250
    target_size_gb = 3.2

    print(f"Target configuration:")
    print(f"  Rows: {target_rows:,}")
    print(f"  Columns: {target_cols}")
    print(f"  Target size: {target_size_gb} GB")
    print()

    # Generate file
    generator = LargeFileGenerator(output_file)

    start_time = time.time()
    stats = generator.generate_file(
        num_rows=target_rows,
        num_cols=target_cols,
        show_progress=True
    )
    generation_time = time.time() - start_time

    print()
    print("RESULTS:")
    print("-" * 70)
    print(f"✓ File size: {stats['file_size_gb']:.2f} GB")
    print(f"✓ Rows: {stats['rows']:,}")
    print(f"✓ Columns: {stats['columns']}")
    print(f"✓ Generation time: {generation_time:.1f} seconds ({generation_time/60:.1f} minutes)")
    print(f"✓ Generation rate: {stats['rows_per_second']:,.0f} rows/sec")
    print(f"✓ Average row size: {stats['bytes_per_row']:.1f} bytes")
    print()

    # Validation
    validation_results = []

    # Check 1: File size >= 3 GB
    size_ok = stats['file_size_gb'] >= 3.0
    validation_results.append(("3+ GiB file generated", size_ok))

    # Check 2: 250 columns
    cols_ok = stats['columns'] >= 250
    validation_results.append(("250+ columns", cols_ok))

    # Check 3: Reasonable generation time (< 15 minutes for 3GB)
    time_ok = generation_time < 900
    validation_results.append(("Generation time < 15 min", time_ok))

    # Display validation results
    print("ACCEPTANCE CRITERIA:")
    print("-" * 70)
    for criterion, passed in validation_results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {criterion}: {status}")

    all_pass = all(passed for _, passed in validation_results)
    print()
    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")
    print()

    # Performance expectations
    print("EXPECTED PERFORMANCE CHARACTERISTICS:")
    print("-" * 70)
    print("When ProfilePipeline is implemented, expected performance:")
    print()
    print(f"  File size: {stats['file_size_gb']:.2f} GB")
    print(f"  Rows: {stats['rows']:,}")
    print(f"  Columns: {stats['columns']}")
    print()
    print("  Expected processing metrics:")
    print(f"    - Wall-clock time: < 10 minutes (600 seconds)")
    print(f"    - Throughput: > 10,000 rows/sec")
    print(f"    - Peak memory: < 2 GB")
    print(f"    - Memory range: < 500 MB (streaming behavior)")
    print()
    print("  Streaming behavior validation:")
    print("    - File should NOT be fully loaded into memory")
    print("    - Row-by-row processing via generators")
    print("    - Constant memory usage regardless of file size")
    print()
    print("  SQLite spill for distinct counting:")
    print("    - High-cardinality columns use disk-backed SQLite")
    print("    - Exact distinct counts without memory overflow")
    print("    - Automatic spill to disk when needed")
    print()

    # Next steps
    print("NEXT STEPS:")
    print("-" * 70)
    print("1. Implement ProfilePipeline class (services/pipeline.py)")
    print("2. Run full performance test: python run_large_file_test.py")
    print("3. Or run pytest suite: pytest tests/performance/test_large_files.py")
    print()
    print(f"Test file location: {output_file}")
    print(f"Test file can be reused with --existing-file flag")
    print()

    # Save results
    results_file = output_dir / "validation_results.txt"
    with open(results_file, 'w') as f:
        f.write("Large File Generation Validation Results\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"File: {output_file}\n")
        f.write(f"Size: {stats['file_size_gb']:.2f} GB\n")
        f.write(f"Rows: {stats['rows']:,}\n")
        f.write(f"Columns: {stats['columns']}\n")
        f.write(f"Generation time: {generation_time:.1f} seconds\n")
        f.write(f"Generation rate: {stats['rows_per_second']:,.0f} rows/sec\n\n")
        f.write("Acceptance Criteria:\n")
        for criterion, passed in validation_results:
            status = "PASS" if passed else "FAIL"
            f.write(f"  {criterion}: {status}\n")
        f.write(f"\nOverall: {'PASS' if all_pass else 'FAIL'}\n")

    print(f"Results saved to: {results_file}")
    print()

    return 0 if all_pass else 1


def main():
    """Run validation."""
    parser = argparse.ArgumentParser(
        description='Validate large file generation for performance testing'
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick test with smaller file (100k rows, 50 cols)'
    )

    args = parser.parse_args()

    if args.quick:
        print("Running quick validation with smaller file...")
        print("Use without --quick flag for full 3GB validation")
        print()
        # For quick test, just verify generator works
        from generate_large_file import LargeFileGenerator
        output_file = Path("/tmp/quick_test.csv")
        generator = LargeFileGenerator(output_file)
        stats = generator.generate_file(num_rows=100000, num_cols=50, show_progress=True)
        print()
        print(f"Quick test complete: {stats['file_size_gb']:.3f} GB generated")
        return 0

    try:
        return validate_file_generation()
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\nValidation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
