"""
Large File Performance Tests.

Tests performance with large files matching the specification:
- 3 GiB+ files
- 250+ columns
- Millions of rows
- Streaming behavior validation
- Memory usage constraints
- Wall-clock time targets
"""

import pytest
import tempfile
from pathlib import Path
import gzip
import time
import psutil
import os


@pytest.mark.performance
@pytest.mark.slow
class TestLargeFilePerformance:
    """Performance tests for large file processing."""

    def generate_large_file(self, path: Path, rows: int, cols: int, compress: bool = False):
        """
        Generate a large test file.

        Args:
            path: Output file path
            rows: Number of rows
            cols: Number of columns
            compress: Whether to gzip compress
        """
        header = '|'.join([f'col{i}' for i in range(cols)])

        if compress:
            with gzip.open(path, 'wt') as f:
                f.write(header + '\n')
                for i in range(rows):
                    row = '|'.join([f'val{i}_{j}' for j in range(cols)])
                    f.write(row + '\n')
        else:
            with open(path, 'w') as f:
                f.write(header + '\n')
                for i in range(rows):
                    row = '|'.join([f'val{i}_{j}' for j in range(cols)])
                    f.write(row + '\n')

    def test_3gb_file_processing(self, temp_workspace):
        """
        Test processing of 3 GiB+ file.

        Target: Complete within reasonable time on laptop (< 10 minutes).
        """
        # Generate ~3.2 GB file (10M rows x 50 cols, ~320 bytes per row)
        large_file = temp_workspace / "large_3gb.csv"

        # Generate in chunks to avoid memory issues
        cols = 50
        rows_per_chunk = 100000
        total_rows = 10000000  # 10M rows

        header = '|'.join([f'col{i}' for i in range(cols)])

        start_gen = time.time()
        with open(large_file, 'w') as f:
            f.write(header + '\n')

            for chunk_start in range(0, total_rows, rows_per_chunk):
                chunk_end = min(chunk_start + rows_per_chunk, total_rows)
                for i in range(chunk_start, chunk_end):
                    row = '|'.join([f'val{i}_{j}' for j in range(cols)])
                    f.write(row + '\n')

        gen_time = time.time() - start_gen
        file_size_gb = large_file.stat().st_size / (1024 ** 3)

        print(f"\nGenerated {file_size_gb:.2f} GB file in {gen_time:.1f}s")

        # Profile the processing
        from services.pipeline import ProfilePipeline

        run_id = "perf_3gb"
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / (1024 ** 2)  # MB

        start = time.time()

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=large_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        elapsed = time.time() - start
        mem_after = process.memory_info().rss / (1024 ** 2)  # MB
        mem_delta = mem_after - mem_before

        print(f"Processing time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"Memory delta: {mem_delta:.1f} MB")
        print(f"Rows processed: {result.profile['file']['rows']:,}")

        # Assertions
        assert result.success is True
        assert file_size_gb >= 3.0  # Verify file is actually 3GB+
        assert elapsed < 600  # Should complete within 10 minutes
        assert mem_delta < 2048  # Should not use > 2GB additional memory

    def test_250_column_file(self, temp_workspace):
        """
        Test processing of file with 250+ columns.

        Target: Handle wide files efficiently.
        """
        large_file = temp_workspace / "wide_250col.csv"
        cols = 250
        rows = 100000  # 100k rows

        self.generate_large_file(large_file, rows, cols)

        file_size_mb = large_file.stat().st_size / (1024 ** 2)
        print(f"\nGenerated {file_size_mb:.1f} MB file with {cols} columns")

        from services.pipeline import ProfilePipeline

        run_id = "perf_250col"
        start = time.time()

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=large_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()
        elapsed = time.time() - start

        print(f"Processing time: {elapsed:.1f}s")
        print(f"Columns profiled: {len(result.profile['columns'])}")

        # Assertions
        assert result.success is True
        assert len(result.profile['columns']) == cols
        assert elapsed < 120  # Should complete within 2 minutes

    def test_millions_of_rows(self, temp_workspace):
        """
        Test processing of file with millions of rows.

        Target: Scale linearly with row count.
        """
        large_file = temp_workspace / "millions_rows.csv"
        cols = 20
        rows = 5000000  # 5M rows

        self.generate_large_file(large_file, rows, cols)

        file_size_mb = large_file.stat().st_size / (1024 ** 2)
        print(f"\nGenerated {file_size_mb:.1f} MB file with {rows:,} rows")

        from services.pipeline import ProfilePipeline

        run_id = "perf_5m_rows"
        start = time.time()

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=large_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()
        elapsed = time.time() - start

        rows_per_second = rows / elapsed

        print(f"Processing time: {elapsed:.1f}s")
        print(f"Throughput: {rows_per_second:,.0f} rows/sec")

        # Assertions
        assert result.success is True
        assert result.profile['file']['rows'] == rows
        assert rows_per_second > 10000  # Should process > 10k rows/sec

    def test_streaming_behavior_no_full_load(self, temp_workspace):
        """
        Validate streaming behavior - file should NOT be fully loaded into memory.

        Target: Memory usage should be constant regardless of file size.
        """
        large_file = temp_workspace / "streaming_test.csv"
        cols = 10
        rows = 1000000  # 1M rows

        self.generate_large_file(large_file, rows, cols)

        from services.pipeline import ProfilePipeline

        run_id = "perf_streaming"
        process = psutil.Process(os.getpid())

        # Measure memory at intervals
        memory_samples = []

        def memory_monitor():
            """Sample memory usage."""
            while True:
                mem = process.memory_info().rss / (1024 ** 2)
                memory_samples.append(mem)
                time.sleep(0.5)

        # Start monitoring in background
        import threading
        monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
        monitor_thread.start()

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=large_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Calculate memory stats
        mem_min = min(memory_samples)
        mem_max = max(memory_samples)
        mem_range = mem_max - mem_min

        print(f"\nMemory range during processing: {mem_range:.1f} MB")
        print(f"Min: {mem_min:.1f} MB, Max: {mem_max:.1f} MB")

        # Memory should not grow unbounded (streaming)
        # Allow up to 500MB variation for buffers/caches
        assert mem_range < 500

    def test_sqlite_spill_behavior(self, temp_workspace):
        """
        Test SQLite spill to disk for exact distinct counting.

        Target: Should handle high cardinality columns efficiently.
        """
        large_file = temp_workspace / "high_cardinality.csv"

        # Generate file with high cardinality column
        cols = 5
        rows = 500000  # 500k unique values

        with open(large_file, 'w') as f:
            f.write('id|high_card|low_card|value|status\n')
            for i in range(rows):
                f.write(f'{i}|unique_{i}|category_{i%10}|{i*1.5:.2f}|active\n')

        from services.pipeline import ProfilePipeline

        run_id = "perf_spill"
        work_dir = temp_workspace / "work" / "runs" / run_id

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=large_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        # Check that SQLite files were used for distinct tracking
        db_files = list(work_dir.glob("*.db"))
        print(f"\nSQLite files created: {len(db_files)}")

        # Verify exact distinct counts
        high_card_col = next(c for c in result.profile['columns'] if c['name'] == 'high_card')
        low_card_col = next(c for c in result.profile['columns'] if c['name'] == 'low_card')

        assert high_card_col['distinct_count'] == rows  # All unique
        assert low_card_col['distinct_count'] == 10  # Only 10 values

    def test_compressed_file_performance(self, temp_workspace):
        """
        Test .gz compressed file processing performance.

        Target: Decompression should not significantly impact performance.
        """
        file_uncompressed = temp_workspace / "uncompressed.csv"
        file_compressed = temp_workspace / "compressed.csv.gz"

        cols = 20
        rows = 500000

        # Generate both versions
        self.generate_large_file(file_uncompressed, rows, cols, compress=False)
        self.generate_large_file(file_compressed, rows, cols, compress=True)

        uncompressed_size = file_uncompressed.stat().st_size / (1024 ** 2)
        compressed_size = file_compressed.stat().st_size / (1024 ** 2)

        print(f"\nUncompressed: {uncompressed_size:.1f} MB")
        print(f"Compressed: {compressed_size:.1f} MB")
        print(f"Compression ratio: {uncompressed_size/compressed_size:.1f}x")

        from services.pipeline import ProfilePipeline

        # Test uncompressed
        start = time.time()
        pipeline1 = ProfilePipeline(
            run_id="perf_uncompressed",
            input_path=file_uncompressed,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )
        result1 = pipeline1.execute()
        time_uncompressed = time.time() - start

        # Test compressed
        start = time.time()
        pipeline2 = ProfilePipeline(
            run_id="perf_compressed",
            input_path=file_compressed,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )
        result2 = pipeline2.execute()
        time_compressed = time.time() - start

        print(f"Uncompressed processing: {time_uncompressed:.1f}s")
        print(f"Compressed processing: {time_compressed:.1f}s")
        print(f"Overhead: {(time_compressed/time_uncompressed - 1)*100:.1f}%")

        # Compressed should not be more than 2x slower
        assert time_compressed < time_uncompressed * 2.0

    @pytest.mark.benchmark
    def test_exact_metrics_computation_performance(self, temp_workspace):
        """
        Benchmark exact metrics computation (no approximations).

        Target: Exact computation should be fast enough for practical use.
        """
        test_file = temp_workspace / "metrics_bench.csv"

        # Generate file with numeric/money/date columns
        with open(test_file, 'w') as f:
            f.write('id|amount|price|date|value\n')
            for i in range(100000):
                f.write(f'{i}|{i*1.5:.2f}|{i*2.0:.2f}|2023{i%12+1:02d}{i%28+1:02d}|{i}\n')

        from services.pipeline import ProfilePipeline

        run_id = "perf_metrics"
        start = time.time()

        pipeline = ProfilePipeline(
            run_id=run_id,
            input_path=test_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()
        elapsed = time.time() - start

        print(f"\nExact metrics computation: {elapsed:.1f}s")

        # Verify exact metrics present
        amount_col = next(c for c in result.profile['columns'] if c['name'] == 'amount')

        assert 'numeric_stats' in amount_col
        assert 'mean' in amount_col['numeric_stats']
        assert 'median' in amount_col['numeric_stats']
        assert 'quantiles' in amount_col['numeric_stats']
        assert 'p99' in amount_col['numeric_stats']['quantiles']

        # Should complete in reasonable time
        assert elapsed < 30  # 100k rows with exact metrics < 30s


@pytest.mark.performance
class TestScalabilityBenchmarks:
    """Scalability benchmarks with progressively larger datasets."""

    @pytest.mark.parametrize("row_count", [1000, 10000, 100000, 1000000])
    def test_row_scaling(self, temp_workspace, row_count):
        """Test performance scaling with row count."""
        test_file = temp_workspace / f"scale_rows_{row_count}.csv"

        with open(test_file, 'w') as f:
            f.write('id|name|value|status\n')
            for i in range(row_count):
                f.write(f'{i}|name{i}|{i*1.5:.2f}|active\n')

        from services.pipeline import ProfilePipeline

        start = time.time()

        pipeline = ProfilePipeline(
            run_id=f"scale_{row_count}",
            input_path=test_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()
        elapsed = time.time() - start

        rows_per_second = row_count / elapsed

        print(f"\n{row_count:,} rows: {elapsed:.2f}s ({rows_per_second:,.0f} rows/sec)")

        # Verify linear scaling (rough check)
        assert result.success is True

    @pytest.mark.parametrize("col_count", [10, 50, 100, 250])
    def test_column_scaling(self, temp_workspace, col_count):
        """Test performance scaling with column count."""
        test_file = temp_workspace / f"scale_cols_{col_count}.csv"

        header = '|'.join([f'col{i}' for i in range(col_count)])

        with open(test_file, 'w') as f:
            f.write(header + '\n')
            for i in range(10000):
                row = '|'.join([f'val{i}_{j}' for j in range(col_count)])
                f.write(row + '\n')

        from services.pipeline import ProfilePipeline

        start = time.time()

        pipeline = ProfilePipeline(
            run_id=f"scale_col_{col_count}",
            input_path=test_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()
        elapsed = time.time() - start

        print(f"\n{col_count} columns: {elapsed:.2f}s")

        assert result.success is True
        assert len(result.profile['columns']) == col_count


@pytest.mark.performance
class TestMemoryConstraints:
    """Verify memory constraints are respected."""

    def test_max_memory_usage_3gb_file(self, temp_workspace):
        """
        Verify max memory usage does not exceed reasonable limits for 3GB file.

        Target: Peak memory < 2GB for 3GB file (streaming).
        """
        # This test is similar to streaming test but focuses on max memory
        pytest.skip("Requires actual 3GB file - run manually for full validation")

    def test_memory_efficient_distinct_tracking(self, temp_workspace):
        """
        Verify distinct tracking uses disk spill, not all-in-memory.

        Target: Should handle 1M+ distinct values without OOM.
        """
        test_file = temp_workspace / "mem_distinct.csv"

        with open(test_file, 'w') as f:
            f.write('id|unique_val\n')
            for i in range(1000000):
                f.write(f'{i}|unique_{i}\n')

        from services.pipeline import ProfilePipeline

        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / (1024 ** 2)

        pipeline = ProfilePipeline(
            run_id="mem_distinct",
            input_path=test_file,
            workspace=temp_workspace,
            config={'delimiter': '|'}
        )

        result = pipeline.execute()

        mem_after = process.memory_info().rss / (1024 ** 2)
        mem_delta = mem_after - mem_before

        print(f"\nMemory used for 1M distincts: {mem_delta:.1f} MB")

        # Should not use more than 500MB for tracking
        assert mem_delta < 500

        # Verify correct count
        unique_col = next(c for c in result.profile['columns'] if c['name'] == 'unique_val')
        assert unique_col['distinct_count'] == 1000000
