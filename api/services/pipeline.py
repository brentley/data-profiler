"""
Data profiling pipeline orchestrator.

This module provides the ProfilePipeline class which orchestrates the
complete data profiling workflow from file upload to final artifacts.
"""

import gzip
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ingest import (
    CRLFDetector,
    CSVParser,
    ParserConfig,
    ParserError,
    UTF8Validator,
)
from .types import TypeInferrer
from .profile import (
    NumericProfiler,
    StringProfiler,
    DateProfiler,
    MoneyProfiler,
    CodeProfiler,
)
from .distincts import DistinctCounter


@dataclass
class PipelineResult:
    """
    Result of pipeline execution.

    Attributes:
        success: Whether pipeline completed successfully
        run_id: Run identifier
        state: Pipeline state ('completed', 'failed', 'processing')
        profile: Profiling results (if successful)
        errors: List of error details
        warnings: List of warning details
        artifacts: Paths to generated artifacts
    """

    success: bool
    run_id: str
    state: str
    profile: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: Dict[str, Path] = field(default_factory=dict)


class ProfilePipeline:
    """
    Data profiling pipeline orchestrator.

    Executes the complete profiling workflow:
    1. File decompression (if .gz)
    2. UTF-8 validation
    3. CRLF detection and normalization
    4. CSV parsing
    5. Type inference
    6. Column profiling
    7. Candidate key detection
    8. Artifact generation
    """

    def __init__(
        self,
        run_id: str,
        input_path: Path,
        workspace: Path,
        config: Optional[Dict[str, Any]] = None,
        state_callback: Optional[callable] = None,
        progress_callback: Optional[callable] = None,
        preserve_on_failure: bool = False
    ):
        """
        Initialize pipeline.

        Args:
            run_id: Unique run identifier
            input_path: Path to input file
            workspace: Workspace directory for temporary files
            config: Configuration dict with delimiter, quoted, expect_crlf
            state_callback: Optional callback for state transitions (queued, processing, completed, failed)
            progress_callback: Optional callback for progress updates (0-100)
            preserve_on_failure: Whether to preserve temporary files on failure for debugging
        """
        self.run_id = run_id
        self.input_path = Path(input_path)
        self.workspace = Path(workspace)
        self.config = config or {}
        self.state_callback = state_callback
        self.progress_callback = progress_callback
        self.preserve_on_failure = preserve_on_failure

        # Extract config values
        self.delimiter = self.config.get('delimiter', '|')
        self.quoted = self.config.get('quoted', True)
        self.expect_crlf = self.config.get('expect_crlf', False)

        # Create workspace directories
        self.work_dir = self.workspace / "work" / "runs" / run_id
        self.output_dir = self.workspace / "outputs" / run_id
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Tracking
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.file_content: Optional[bytes] = None
        self.normalized_content: Optional[bytes] = None
        self.current_state: str = 'queued'

    def _set_state(self, state: str) -> None:
        """
        Update pipeline state and call callback if provided.

        Args:
            state: New state (queued, processing, completed, failed)
        """
        self.current_state = state
        if self.state_callback:
            self.state_callback(state)

    def _update_progress(self, progress: float) -> None:
        """
        Update progress and call callback if provided.

        Args:
            progress: Progress percentage (0-100)
        """
        if self.progress_callback:
            self.progress_callback(progress)

    def execute(self) -> PipelineResult:
        """
        Execute the complete pipeline.

        Returns:
            PipelineResult with success status and profiling data
        """
        try:
            # Transition to processing state
            self._set_state('processing')
            self._update_progress(0.0)

            # Stage 1: Load and decompress file
            self._load_file()
            self._update_progress(10.0)

            # Stage 2: UTF-8 validation
            if not self._validate_utf8():
                return self._create_failed_result("UTF-8 validation failed")
            self._update_progress(20.0)

            # Stage 3: CRLF detection and normalization
            self._normalize_line_endings()
            self._update_progress(30.0)

            # Stage 4: CSV parsing
            if not self._parse_csv():
                return self._create_failed_result("CSV parsing failed")
            self._update_progress(40.0)

            # Stage 5: Type inference
            type_result = self._infer_types()
            if not type_result:
                return self._create_failed_result("Type inference failed")
            self._update_progress(60.0)

            # Stage 6: Column profiling
            column_profiles = self._profile_columns(type_result)
            self._update_progress(80.0)

            # Stage 7: Build profile
            profile = self._build_profile(type_result, column_profiles)
            self._update_progress(90.0)

            # Stage 8: Generate artifacts
            self._generate_artifacts(profile)
            self._update_progress(100.0)

            # Transition to completed state
            self._set_state('completed')

            return PipelineResult(
                success=True,
                run_id=self.run_id,
                state='completed',
                profile=profile,
                errors=self.errors,
                warnings=self.warnings,
                artifacts={
                    'profile': self.output_dir / 'profile.json',
                    'metrics': self.output_dir / 'metrics.csv',
                    'report': self.output_dir / 'report.html'
                }
            )

        except Exception as e:
            self._add_error('E_PIPELINE_FAILED', str(e), 1)
            return self._create_failed_result(str(e))

    def _load_file(self) -> None:
        """Load and optionally decompress input file."""
        with open(self.input_path, 'rb') as f:
            self.file_content = f.read()

        # Check if gzipped
        if self.input_path.suffix == '.gz' or self.file_content.startswith(b'\x1f\x8b'):
            try:
                self.file_content = gzip.decompress(self.file_content)
            except Exception as e:
                self._add_error('E_GZIP_DECOMPRESS', f"Failed to decompress: {e}", 1)
                raise

    def _validate_utf8(self) -> bool:
        """
        Validate UTF-8 encoding.

        Returns:
            True if valid, False if catastrophic error
        """
        stream = BytesIO(self.file_content)
        validator = UTF8Validator(stream)
        result = validator.validate()

        if not result.is_valid:
            self._add_error('E_UTF8_INVALID', result.error or 'Invalid UTF-8', 1)
            return False

        return True

    def _normalize_line_endings(self) -> None:
        """Detect and normalize line endings."""
        stream = BytesIO(self.file_content)
        detector = CRLFDetector(stream)
        line_ending_result = detector.detect()

        # Normalize
        self.normalized_content = detector.normalize()

        # Record warnings for mixed line endings
        if line_ending_result.mixed:
            self._add_warning(
                'W_LINE_ENDING',
                f'Mixed line endings: {line_ending_result.crlf_count} CRLF, '
                f'{line_ending_result.lf_count} LF, {line_ending_result.cr_count} CR',
                1
            )

    def _parse_csv(self) -> bool:
        """
        Parse CSV and validate structure.

        Returns:
            True if parseable, False if catastrophic error
        """
        try:
            text_stream = StringIO(self.normalized_content.decode('utf-8'))
            config = ParserConfig(
                delimiter=self.delimiter,
                quoting=self.quoted,
                has_header=True,
                continue_on_error=True
            )

            parser = CSVParser(text_stream, config)

            # Parse header
            try:
                self.header_result = parser.parse_header()
                if not self.header_result.success:
                    self._add_error('E_HEADER_INVALID', 'Failed to parse header', 1)
                    return False
            except ParserError as e:
                self._add_error(e.code, e.message, 1)
                return False

            # Count rows and aggregate errors
            self.row_count = 0
            for row in parser.parse_rows():
                self.row_count += 1

            # Get error rollup
            error_rollup = parser.get_error_rollup()
            for error_code, count in error_rollup.items():
                if error_code.startswith('W_'):
                    self._add_warning(error_code, f'Parser warning: {error_code}', count)
                else:
                    self._add_error(error_code, f'Parser error: {error_code}', count)

            return True

        except Exception as e:
            self._add_error('E_CSV_PARSE_FAILED', str(e), 1)
            return False

    def _infer_types(self):
        """
        Infer column types.

        Returns:
            TypeInferenceResult or None if failed
        """
        try:
            # Write normalized content to temp file
            temp_csv = self.work_dir / 'normalized.csv'
            temp_csv.write_bytes(self.normalized_content)

            # Run type inference
            inferrer = TypeInferrer(sample_size=None)
            type_result = inferrer.infer_column_types(temp_csv, delimiter=self.delimiter)

            # Record type-specific errors/warnings
            for col_name, col_info in type_result.columns.items():
                if col_info.error_count > 0:
                    self._add_error(
                        f'E_{col_info.inferred_type.upper()}_FORMAT',
                        f'Format violations in column {col_name}',
                        col_info.error_count
                    )

                if col_info.warning_count > 0:
                    self._add_warning(
                        f'W_{col_info.inferred_type.upper()}_FORMAT',
                        f'Format warnings in column {col_name}',
                        col_info.warning_count
                    )

            return type_result

        except Exception as e:
            self._add_error('E_TYPE_INFERENCE_FAILED', str(e), 1)
            return None

    def _profile_columns(self, type_result) -> Dict[str, Dict[str, Any]]:
        """
        Profile all columns using type-specific profilers.

        Args:
            type_result: TypeInferenceResult

        Returns:
            Dictionary mapping column names to profile results
        """
        column_profiles = {}
        temp_csv = self.work_dir / 'normalized.csv'

        # Create profilers for each column
        profilers = {}
        distinct_counters = {}

        for col_name, col_info in type_result.columns.items():
            inferred_type = col_info.inferred_type

            # Create type-specific profiler
            if inferred_type == 'numeric':
                profilers[col_name] = NumericProfiler(num_bins=10)
            elif inferred_type == 'money':
                profilers[col_name] = MoneyProfiler()
            elif inferred_type == 'date':
                profilers[col_name] = DateProfiler()
            elif inferred_type == 'code':
                profilers[col_name] = CodeProfiler(top_n=10)
            else:
                profilers[col_name] = StringProfiler(top_n=10)

            # Create distinct counter
            distinct_counters[col_name] = DistinctCounter()

        # Stream through CSV and update profilers
        import csv
        with open(temp_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)

            for row in reader:
                for col_name in type_result.columns.keys():
                    value = row.get(col_name, '')
                    profilers[col_name].update(value)

        # Finalize profilers
        for col_name, col_info in type_result.columns.items():
            profiler = profilers[col_name]
            stats = profiler.finalize()

            # Get distinct count
            distinct_result = distinct_counters[col_name].count_distincts(
                temp_csv,
                col_name,
                delimiter=self.delimiter
            )

            # Build profile
            profile = {
                'name': col_name,
                'inferred_type': col_info.inferred_type,
                'null_count': stats.null_count if hasattr(stats, 'null_count') else 0,
                'distinct_count': distinct_result.distinct_count,
                'distinct_pct': distinct_result.cardinality_ratio * 100.0,
            }

            # Add type-specific stats
            if col_info.inferred_type == 'numeric':
                profile.update({
                    'min': stats.min_value,
                    'max': stats.max_value,
                    'mean': stats.mean,
                    'median': stats.median,
                    'stddev': stats.stddev,
                })
            elif col_info.inferred_type == 'money':
                profile['money_rules'] = {
                    'two_decimal_ok': stats.two_decimal_ok,
                    'disallowed_symbols_found': stats.disallowed_symbols_found,
                }
            elif col_info.inferred_type == 'date':
                profile['date_rules'] = {
                    'detected_format': stats.detected_format,
                    'format_consistent': stats.format_consistent,
                }

            column_profiles[col_name] = profile

            # Cleanup
            distinct_counters[col_name].cleanup()

        return column_profiles

    def _build_profile(self, type_result, column_profiles) -> Dict[str, Any]:
        """
        Build complete profile structure.

        Args:
            type_result: TypeInferenceResult
            column_profiles: Dictionary of column profiles

        Returns:
            Complete profile dictionary
        """
        return {
            'run_id': self.run_id,
            'file': {
                'rows': self.row_count,
                'columns': len(self.header_result.headers),
                'delimiter': self.delimiter,
                'header': self.header_result.headers,
            },
            'columns': [column_profiles[col] for col in self.header_result.headers],
            'errors': self.errors,
            'warnings': self.warnings,
        }

    def _generate_artifacts(self, profile: Dict[str, Any]) -> None:
        """
        Generate output artifacts.

        Args:
            profile: Complete profile dictionary
        """
        import json
        import csv

        # Generate profile.json
        profile_path = self.output_dir / 'profile.json'
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)

        # Generate metrics.csv
        metrics_path = self.output_dir / 'metrics.csv'
        with open(metrics_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['column_name', 'type', 'null_count', 'distinct_count', 'distinct_pct'])

            for col in profile['columns']:
                writer.writerow([
                    col['name'],
                    col['inferred_type'],
                    col.get('null_count', 0),
                    col.get('distinct_count', 0),
                    col.get('distinct_pct', 0.0),
                ])

        # Generate report.html (minimal)
        report_path = self.output_dir / 'report.html'
        with open(report_path, 'w') as f:
            f.write(f'''
<!DOCTYPE html>
<html>
<head>
    <title>Profile Report - {self.run_id}</title>
</head>
<body>
    <h1>Data Profile Report</h1>
    <h2>Run ID: {self.run_id}</h2>
    <p>Rows: {profile['file']['rows']}</p>
    <p>Columns: {profile['file']['columns']}</p>
    <h2>Columns</h2>
    <table border="1">
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Distinct Count</th>
            <th>Null Count</th>
        </tr>
''')
            for col in profile['columns']:
                f.write(f'''        <tr>
            <td>{col['name']}</td>
            <td>{col['inferred_type']}</td>
            <td>{col.get('distinct_count', 0)}</td>
            <td>{col.get('null_count', 0)}</td>
        </tr>
''')
            f.write('''    </table>
</body>
</html>
''')

        # Generate audit.log.json
        import datetime
        audit_path = self.output_dir / 'audit.log.json'
        audit_log = {
            'run_id': self.run_id,
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'input_file': str(self.input_path),
            'workspace': str(self.workspace),
            'config': self.config,
            'state': 'completed',
            'rows_processed': profile['file']['rows'],
            'columns_processed': profile['file']['columns'],
            'errors': self.errors,
            'warnings': self.warnings
        }
        with open(audit_path, 'w') as f:
            json.dump(audit_log, f, indent=2)

    def _add_error(self, code: str, message: str, count: int = 1) -> None:
        """Add error to tracking list."""
        # Check if error already exists
        existing = next((e for e in self.errors if e['code'] == code), None)
        if existing:
            existing['count'] += count
        else:
            self.errors.append({'code': code, 'message': message, 'count': count})

    def _add_warning(self, code: str, message: str, count: int = 1) -> None:
        """Add warning to tracking list."""
        # Check if warning already exists
        existing = next((w for w in self.warnings if w['code'] == code), None)
        if existing:
            existing['count'] += count
        else:
            self.warnings.append({'code': code, 'message': message, 'count': count})

    def _create_failed_result(self, message: str) -> PipelineResult:
        """Create a failed pipeline result."""
        # Transition to failed state
        self._set_state('failed')

        return PipelineResult(
            success=False,
            run_id=self.run_id,
            state='failed',
            profile=None,
            errors=self.errors,
            warnings=self.warnings,
            artifacts={}
        )
