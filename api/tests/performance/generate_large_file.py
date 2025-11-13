"""
Large File Generator for Performance Testing.

Generates large CSV files matching spec requirements:
- 3+ GiB files
- 250+ columns
- Millions of rows
- Mixed data types
- Pipe-delimited format
"""

import argparse
import sys
from pathlib import Path
from typing import Generator
import random
import time


class LargeFileGenerator:
    """Generate large test files with various characteristics."""

    def __init__(self, output_path: Path):
        """
        Initialize generator.

        Args:
            output_path: Path to output file
        """
        self.output_path = output_path
        self.bytes_written = 0

    def generate_row_data(
        self,
        row_num: int,
        num_cols: int,
        data_types: list[str] = None
    ) -> Generator[str, None, None]:
        """
        Generate row data with mixed types.

        Args:
            row_num: Row number
            num_cols: Number of columns
            data_types: List of data types per column

        Yields:
            str: Column values
        """
        if data_types is None:
            # Default mix: numeric, text, money, dates, status codes
            data_types = ['id'] + ['mixed'] * (num_cols - 1)

        for i, dtype in enumerate(data_types):
            if dtype == 'id':
                yield str(row_num)
            elif dtype == 'numeric':
                yield f"{row_num * 1.5 + i:.2f}"
            elif dtype == 'money':
                yield f"{(row_num % 10000) * 0.99:.2f}"
            elif dtype == 'date':
                # YYYYMMDD format
                year = 2020 + (row_num % 5)
                month = (row_num % 12) + 1
                day = (row_num % 28) + 1
                yield f"{year}{month:02d}{day:02d}"
            elif dtype == 'text':
                yield f"text_{row_num}_{i}"
            elif dtype == 'status':
                statuses = ['active', 'inactive', 'pending', 'archived']
                yield statuses[row_num % len(statuses)]
            elif dtype == 'category':
                yield f"cat_{row_num % 50}"
            elif dtype == 'high_cardinality':
                # Unique values for distinct count testing
                yield f"unique_{row_num}_{i}"
            else:  # mixed
                # Cycle through different types
                type_index = (row_num + i) % 7
                if type_index == 0:
                    yield str(row_num + i)
                elif type_index == 1:
                    yield f"{(row_num + i) * 1.23:.2f}"
                elif type_index == 2:
                    year = 2020 + ((row_num + i) % 5)
                    month = ((row_num + i) % 12) + 1
                    day = ((row_num + i) % 28) + 1
                    yield f"{year}{month:02d}{day:02d}"
                elif type_index == 3:
                    yield f"value_{row_num}_{i}"
                elif type_index == 4:
                    statuses = ['active', 'inactive', 'pending']
                    yield statuses[(row_num + i) % len(statuses)]
                elif type_index == 5:
                    yield f"{(row_num % 1000) * 0.99:.2f}"
                else:
                    yield f"data_{row_num % 100}_{i % 10}"

    def generate_header(self, num_cols: int) -> str:
        """
        Generate CSV header.

        Args:
            num_cols: Number of columns

        Returns:
            str: Header row
        """
        return '|'.join([f'col{i}' for i in range(num_cols)])

    def generate_file(
        self,
        num_rows: int,
        num_cols: int,
        data_types: list[str] = None,
        buffer_size: int = 1024 * 1024,  # 1MB buffer
        show_progress: bool = True
    ) -> dict:
        """
        Generate large CSV file.

        Args:
            num_rows: Number of data rows
            num_cols: Number of columns
            data_types: Optional list of data types per column
            buffer_size: Write buffer size
            show_progress: Show progress during generation

        Returns:
            dict: Generation statistics
        """
        start_time = time.time()
        rows_written = 0
        bytes_written = 0

        print(f"Generating file: {self.output_path}")
        print(f"Rows: {num_rows:,}, Columns: {num_cols}")
        print(f"Buffer size: {buffer_size:,} bytes")

        with open(self.output_path, 'w', buffering=buffer_size) as f:
            # Write header
            header = self.generate_header(num_cols)
            f.write(header + '\n')
            bytes_written += len(header) + 1

            # Write data rows
            progress_interval = max(num_rows // 20, 1000)

            for row_num in range(num_rows):
                row_data = '|'.join(self.generate_row_data(row_num, num_cols, data_types))
                f.write(row_data + '\n')
                bytes_written += len(row_data) + 1
                rows_written += 1

                if show_progress and rows_written % progress_interval == 0:
                    elapsed = time.time() - start_time
                    progress_pct = (rows_written / num_rows) * 100
                    rate = rows_written / elapsed if elapsed > 0 else 0
                    size_mb = bytes_written / (1024 * 1024)
                    print(f"Progress: {progress_pct:5.1f}% | {rows_written:,} rows | "
                          f"{size_mb:,.1f} MB | {rate:,.0f} rows/sec", end='\r')

        elapsed_time = time.time() - start_time
        file_size_bytes = self.output_path.stat().st_size
        file_size_gb = file_size_bytes / (1024 ** 3)

        stats = {
            'rows': num_rows,
            'columns': num_cols,
            'file_size_bytes': file_size_bytes,
            'file_size_gb': file_size_gb,
            'generation_time_seconds': elapsed_time,
            'rows_per_second': num_rows / elapsed_time if elapsed_time > 0 else 0,
            'bytes_per_row': file_size_bytes / num_rows if num_rows > 0 else 0
        }

        print(f"\n\nGeneration complete!")
        print(f"File size: {file_size_gb:.2f} GB ({file_size_bytes:,} bytes)")
        print(f"Time: {elapsed_time:.1f} seconds")
        print(f"Rate: {stats['rows_per_second']:,.0f} rows/sec")
        print(f"Avg row size: {stats['bytes_per_row']:.1f} bytes")

        return stats


def main():
    """Command-line interface for file generation."""
    parser = argparse.ArgumentParser(
        description='Generate large CSV files for performance testing'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output file path'
    )
    parser.add_argument(
        '--rows',
        type=int,
        default=10_000_000,
        help='Number of rows (default: 10M for ~3.2 GB with 50 cols)'
    )
    parser.add_argument(
        '--columns',
        type=int,
        default=250,
        help='Number of columns (default: 250 per spec)'
    )
    parser.add_argument(
        '--target-size-gb',
        type=float,
        help='Target file size in GB (estimates rows needed)'
    )
    parser.add_argument(
        '--buffer-size',
        type=int,
        default=1024 * 1024,
        help='Write buffer size in bytes (default: 1MB)'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress output'
    )

    args = parser.parse_args()

    # Estimate rows needed for target size
    if args.target_size_gb:
        # Estimate: ~320 bytes per row for 50 cols, ~1280 bytes for 250 cols
        estimated_bytes_per_row = args.columns * 5.12  # Rough estimate
        target_bytes = args.target_size_gb * (1024 ** 3)
        args.rows = int(target_bytes / estimated_bytes_per_row)
        print(f"Target size: {args.target_size_gb} GB")
        print(f"Estimated rows needed: {args.rows:,}")
        print(f"Estimated bytes/row: {estimated_bytes_per_row:.1f}")
        print()

    # Create output directory if needed
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Generate file
    generator = LargeFileGenerator(args.output)
    stats = generator.generate_file(
        num_rows=args.rows,
        num_cols=args.columns,
        buffer_size=args.buffer_size,
        show_progress=not args.no_progress
    )

    # Save stats
    stats_file = args.output.with_suffix('.stats.txt')
    with open(stats_file, 'w') as f:
        f.write(f"File Generation Statistics\n")
        f.write(f"{'=' * 50}\n")
        for key, value in stats.items():
            f.write(f"{key}: {value}\n")

    print(f"\nStats saved to: {stats_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
