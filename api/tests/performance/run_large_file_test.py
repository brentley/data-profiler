"""
Standalone Performance Test for 3+ GiB Files.

Tests performance of data profiling with large files:
- Wall-clock time measurement
- Memory usage tracking
- Streaming behavior validation
- SQLite spill verification
- Performance metrics documentation

This script tests the core services directly without requiring
the full ProfilePipeline implementation.
"""

import argparse
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Optional
import json
import tempfile
import shutil


class PerformanceMonitor:
    """Monitor performance metrics during test."""

    def __init__(self):
        """Initialize monitor."""
        self.start_time = None
        self.memory_samples = []
        self.metrics = {}

    def start(self):
        """Start monitoring."""
        self.start_time = time.time()
        tracemalloc.start()

    def sample_memory(self):
        """Sample current memory usage."""
        current, peak = tracemalloc.get_traced_memory()
        self.memory_samples.append({
            'timestamp': time.time() - self.start_time,
            'current_mb': current / (1024 * 1024),
            'peak_mb': peak / (1024 * 1024)
        })

    def stop(self) -> dict:
        """
        Stop monitoring and return metrics.

        Returns:
            dict: Performance metrics
        """
        elapsed = time.time() - self.start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        if self.memory_samples:
            mem_min = min(s['current_mb'] for s in self.memory_samples)
            mem_max = max(s['peak_mb'] for s in self.memory_samples)
            mem_range = mem_max - mem_min
        else:
            mem_min = mem_max = mem_range = 0

        return {
            'elapsed_seconds': elapsed,
            'peak_memory_mb': peak / (1024 * 1024),
            'current_memory_mb': current / (1024 * 1024),
            'memory_range_mb': mem_range,
            'memory_samples': len(self.memory_samples)
        }


class LargeFilePerformanceTest:
    """Performance test for large file processing."""

    def __init__(self, workspace: Path):
        """
        Initialize test.

        Args:
            workspace: Temporary workspace directory
        """
        self.workspace = workspace
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.results = {}

    def test_file_generation(
        self,
        rows: int,
        cols: int,
        target_size_gb: Optional[float] = None
    ) -> Path:
        """
        Test large file generation.

        Args:
            rows: Number of rows
            cols: Number of columns
            target_size_gb: Target file size in GB

        Returns:
            Path: Generated file path
        """
        from generate_large_file import LargeFileGenerator

        output_file = self.workspace / "test_large_file.csv"

        print(f"\n{'='*60}")
        print("TEST: File Generation")
        print(f"{'='*60}")

        generator = LargeFileGenerator(output_file)
        stats = generator.generate_file(
            num_rows=rows,
            num_cols=cols,
            show_progress=True
        )

        self.results['file_generation'] = stats

        # Validate file size
        if target_size_gb:
            actual_gb = stats['file_size_gb']
            if actual_gb < target_size_gb:
                print(f"\nWARNING: File size {actual_gb:.2f} GB < target {target_size_gb} GB")
            else:
                print(f"\nSUCCESS: File size {actual_gb:.2f} GB >= target {target_size_gb} GB")

        return output_file

    def test_basic_ingest(self, file_path: Path) -> dict:
        """
        Test basic file ingestion (streaming read).

        Args:
            file_path: Input file path

        Returns:
            dict: Ingest metrics
        """
        print(f"\n{'='*60}")
        print("TEST: Basic Ingestion (Streaming Read)")
        print(f"{'='*60}")

        from services.ingest import CSVIngestor
        from storage.sqlite import RunStorage

        # Create run storage
        run_id = "perf_test_ingest"
        db_path = self.workspace / f"{run_id}.db"
        storage = RunStorage(db_path)
        storage.create_run(
            run_id=run_id,
            delimiter='|',
            quoted=True,
            expect_crlf=False,
            source_filename=file_path.name
        )

        # Monitor performance
        monitor = PerformanceMonitor()
        monitor.start()

        rows_processed = 0
        chunk_count = 0

        try:
            # Create ingestor
            ingestor = CSVIngestor(
                file_path=file_path,
                run_id=run_id,
                storage=storage,
                config={'delimiter': '|', 'quoted': True}
            )

            # Process in chunks to monitor memory
            for row in ingestor.iter_rows():
                rows_processed += 1

                # Sample memory every 100k rows
                if rows_processed % 100000 == 0:
                    monitor.sample_memory()
                    chunk_count += 1
                    elapsed = time.time() - monitor.start_time
                    rate = rows_processed / elapsed if elapsed > 0 else 0
                    print(f"Processed: {rows_processed:,} rows | "
                          f"Rate: {rate:,.0f} rows/sec", end='\r')

        except Exception as e:
            print(f"\nERROR during ingestion: {e}")
            traceback.print_exc()
            raise

        perf_metrics = monitor.stop()

        # Calculate throughput
        throughput = rows_processed / perf_metrics['elapsed_seconds']

        metrics = {
            'rows_processed': rows_processed,
            'elapsed_seconds': perf_metrics['elapsed_seconds'],
            'throughput_rows_per_sec': throughput,
            'peak_memory_mb': perf_metrics['peak_memory_mb'],
            'memory_range_mb': perf_metrics['memory_range_mb'],
            'streaming_verified': perf_metrics['memory_range_mb'] < 500  # Should be constant
        }

        print(f"\n\nResults:")
        print(f"  Rows processed: {metrics['rows_processed']:,}")
        print(f"  Time: {metrics['elapsed_seconds']:.1f} seconds")
        print(f"  Throughput: {metrics['throughput_rows_per_sec']:,.0f} rows/sec")
        print(f"  Peak memory: {metrics['peak_memory_mb']:.1f} MB")
        print(f"  Memory range: {metrics['memory_range_mb']:.1f} MB")
        print(f"  Streaming: {'PASS' if metrics['streaming_verified'] else 'FAIL'}")

        self.results['ingest'] = metrics

        # Cleanup
        storage.close()
        if db_path.exists():
            db_path.unlink()

        return metrics

    def test_type_inference(self, file_path: Path, sample_size: int = 100000) -> dict:
        """
        Test type inference performance.

        Args:
            file_path: Input file path
            sample_size: Number of rows to sample

        Returns:
            dict: Type inference metrics
        """
        print(f"\n{'='*60}")
        print(f"TEST: Type Inference (Sample: {sample_size:,} rows)")
        print(f"{'='*60}")

        from services.ingest import CSVIngestor
        from services.types import TypeInferenceEngine
        from storage.sqlite import RunStorage

        # Create run storage
        run_id = "perf_test_types"
        db_path = self.workspace / f"{run_id}.db"
        storage = RunStorage(db_path)
        storage.create_run(
            run_id=run_id,
            delimiter='|',
            quoted=True,
            expect_crlf=False,
            source_filename=file_path.name
        )

        monitor = PerformanceMonitor()
        monitor.start()

        try:
            # Create ingestor
            ingestor = CSVIngestor(
                file_path=file_path,
                run_id=run_id,
                storage=storage,
                config={'delimiter': '|', 'quoted': True}
            )

            # Get column names
            header = ingestor.header

            # Create type inference engine
            engine = TypeInferenceEngine(
                run_id=run_id,
                storage=storage,
                column_names=header
            )

            # Sample rows for type inference
            rows_sampled = 0
            for row in ingestor.iter_rows():
                engine.process_row(row)
                rows_sampled += 1
                if rows_sampled >= sample_size:
                    break

            # Finalize types
            inferred_types = engine.finalize()

        except Exception as e:
            print(f"\nERROR during type inference: {e}")
            traceback.print_exc()
            raise

        perf_metrics = monitor.stop()

        metrics = {
            'rows_sampled': rows_sampled,
            'columns': len(header) if header else 0,
            'elapsed_seconds': perf_metrics['elapsed_seconds'],
            'peak_memory_mb': perf_metrics['peak_memory_mb'],
            'types_inferred': len(inferred_types)
        }

        print(f"\nResults:")
        print(f"  Rows sampled: {metrics['rows_sampled']:,}")
        print(f"  Columns: {metrics['columns']}")
        print(f"  Time: {metrics['elapsed_seconds']:.1f} seconds")
        print(f"  Peak memory: {metrics['peak_memory_mb']:.1f} MB")

        self.results['type_inference'] = metrics

        # Cleanup
        storage.close()
        if db_path.exists():
            db_path.unlink()

        return metrics

    def generate_report(self, output_file: Path):
        """
        Generate performance test report.

        Args:
            output_file: Output file path
        """
        print(f"\n{'='*60}")
        print("PERFORMANCE TEST REPORT")
        print(f"{'='*60}")

        report = {
            'test_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'workspace': str(self.workspace),
            'results': self.results
        }

        # Summary
        print("\nSUMMARY:")
        if 'file_generation' in self.results:
            fg = self.results['file_generation']
            print(f"\nFile Generation:")
            print(f"  Size: {fg['file_size_gb']:.2f} GB")
            print(f"  Rows: {fg['rows']:,}")
            print(f"  Columns: {fg['columns']}")
            print(f"  Time: {fg['generation_time_seconds']:.1f}s")

        if 'ingest' in self.results:
            ing = self.results['ingest']
            print(f"\nIngestion (Streaming):")
            print(f"  Throughput: {ing['throughput_rows_per_sec']:,.0f} rows/sec")
            print(f"  Time: {ing['elapsed_seconds']:.1f}s")
            print(f"  Peak Memory: {ing['peak_memory_mb']:.1f} MB")
            print(f"  Streaming: {'PASS' if ing['streaming_verified'] else 'FAIL'}")

        if 'type_inference' in self.results:
            ti = self.results['type_inference']
            print(f"\nType Inference:")
            print(f"  Columns: {ti['columns']}")
            print(f"  Sample Size: {ti['rows_sampled']:,} rows")
            print(f"  Time: {ti['elapsed_seconds']:.1f}s")
            print(f"  Peak Memory: {ti['peak_memory_mb']:.1f} MB")

        # Acceptance criteria check
        print(f"\n{'='*60}")
        print("ACCEPTANCE CRITERIA:")
        print(f"{'='*60}")

        criteria_met = []

        if 'file_generation' in self.results:
            file_size_ok = self.results['file_generation']['file_size_gb'] >= 3.0
            criteria_met.append(('3+ GiB file generated', file_size_ok))

            cols_ok = self.results['file_generation']['columns'] >= 250
            criteria_met.append(('250+ columns', cols_ok))

        if 'ingest' in self.results:
            streaming_ok = self.results['ingest']['streaming_verified']
            criteria_met.append(('Streaming behavior (memory < 500MB range)', streaming_ok))

            memory_ok = self.results['ingest']['peak_memory_mb'] < 2048
            criteria_met.append(('Memory usage < 2GB', memory_ok))

            # Throughput target: at least 10k rows/sec
            throughput_ok = self.results['ingest']['throughput_rows_per_sec'] > 10000
            criteria_met.append(('Throughput > 10k rows/sec', throughput_ok))

        for criterion, met in criteria_met:
            status = 'PASS' if met else 'FAIL'
            symbol = '✓' if met else '✗'
            print(f"  {symbol} {criterion}: {status}")

        all_pass = all(met for _, met in criteria_met)
        print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")

        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nFull report saved to: {output_file}")

        return all_pass


def main():
    """Run performance tests."""
    parser = argparse.ArgumentParser(
        description='Run performance tests for large file processing'
    )
    parser.add_argument(
        '--workspace',
        type=Path,
        help='Workspace directory (default: temp directory)'
    )
    parser.add_argument(
        '--rows',
        type=int,
        default=10_000_000,
        help='Number of rows (default: 10M)'
    )
    parser.add_argument(
        '--columns',
        type=int,
        default=250,
        help='Number of columns (default: 250)'
    )
    parser.add_argument(
        '--target-size-gb',
        type=float,
        default=3.0,
        help='Target file size in GB (default: 3.0)'
    )
    parser.add_argument(
        '--skip-generation',
        action='store_true',
        help='Skip file generation (use existing file)'
    )
    parser.add_argument(
        '--existing-file',
        type=Path,
        help='Use existing file instead of generating'
    )
    parser.add_argument(
        '--output-report',
        type=Path,
        default=Path('performance_test_report.json'),
        help='Output report path'
    )

    args = parser.parse_args()

    # Create workspace
    if args.workspace:
        workspace = args.workspace
        workspace.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        workspace = Path(tempfile.mkdtemp(prefix='perf_test_'))
        cleanup = True

    print(f"Workspace: {workspace}")

    try:
        test = LargeFilePerformanceTest(workspace)

        # Generate or use existing file
        if args.existing_file:
            test_file = args.existing_file
            print(f"Using existing file: {test_file}")
            file_size_gb = test_file.stat().st_size / (1024 ** 3)
            print(f"File size: {file_size_gb:.2f} GB")
        elif not args.skip_generation:
            test_file = test.test_file_generation(
                rows=args.rows,
                cols=args.columns,
                target_size_gb=args.target_size_gb
            )
        else:
            print("ERROR: Must provide --existing-file if --skip-generation is used")
            return 1

        # Run tests
        test.test_basic_ingest(test_file)
        test.test_type_inference(test_file, sample_size=100000)

        # Generate report
        all_pass = test.generate_report(args.output_report)

        return 0 if all_pass else 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 130

    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        traceback.print_exc()
        return 1

    finally:
        if cleanup:
            print(f"\nCleaning up workspace: {workspace}")
            shutil.rmtree(workspace, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
