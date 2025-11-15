"""
HTML report generation for profiling results.

This module generates a clean, self-contained HTML report from profiling data.
"""

from typing import Any, Dict, List
from uuid import UUID


def generate_html_report(
    run_id: UUID,
    file_metadata: Dict[str, Any],
    columns: List[Dict[str, Any]],
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
    candidate_keys: List[Dict[str, Any]]
) -> str:
    """
    Generate an HTML report from profiling results.

    Args:
        run_id: Run UUID
        file_metadata: File metadata (rows, columns, delimiter, etc.)
        columns: List of column profiles
        errors: List of errors
        warnings: List of warnings
        candidate_keys: List of candidate key suggestions

    Returns:
        Complete HTML report as a string
    """
    # Extract file metadata
    row_count = file_metadata.get('rows', 0)
    col_count = file_metadata.get('columns', 0)
    delimiter = file_metadata.get('delimiter', ',')
    delimiter_name = _delimiter_to_name(delimiter)
    crlf_detected = file_metadata.get('crlf_detected', False)

    # Detection info
    delimiter_detected = file_metadata.get('delimiter_detected', False)
    delimiter_confidence = file_metadata.get('delimiter_confidence')
    quoting_detected = file_metadata.get('quoting_detected', False)
    quoting_confidence = file_metadata.get('quoting_confidence')
    quoted = file_metadata.get('quoted', False)

    # Calculate aggregate statistics
    total_errors = sum(e.get('count', 0) for e in errors)
    total_warnings = sum(w.get('count', 0) for w in warnings)

    # Start building HTML
    html_parts = []

    # HTML header with embedded CSS
    html_parts.append(f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Profile Report - {run_id}</title>
    <script>
        function toggleCollapsible(event) {{
            event.preventDefault();
            const header = event.currentTarget;
            const content = header.nextElementSibling;
            content.classList.toggle('show');

            // Update arrow indicator
            const arrow = header.querySelector('.arrow');
            if (arrow) {{
                arrow.textContent = content.classList.contains('show') ? '▼' : '▶';
            }}
        }}
    </script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #212529;
            background: #f8f9fa;
            padding: 2rem;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 2rem;
        }}

        .header {{
            border-bottom: 3px solid #116df8;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }}

        h1 {{
            color: #116df8;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        h2 {{
            color: #116df8;
            font-size: 1.5rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #dee2e6;
        }}

        h3 {{
            color: #495057;
            font-size: 1.2rem;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
        }}

        .run-id {{
            color: #6c757d;
            font-size: 0.9rem;
            font-family: monospace;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }}

        .summary-card {{
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 6px;
            border-left: 4px solid #116df8;
        }}

        .summary-card.warning {{
            border-left-color: #ff5100;
        }}

        .summary-card.error {{
            border-left-color: #dc3545;
        }}

        .summary-card.success {{
            border-left-color: #28a745;
        }}

        .summary-label {{
            font-size: 0.85rem;
            color: #6c757d;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}

        .summary-value {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #212529;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
        }}

        th {{
            background: #116df8;
            color: white;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #dee2e6;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .type-badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .type-numeric {{ background: #d1ecf1; color: #0c5460; }}
        .type-alpha {{ background: #d4edda; color: #155724; }}
        .type-varchar {{ background: #d4edda; color: #155724; }}
        .type-date {{ background: #fff3cd; color: #856404; }}
        .type-money {{ background: #f8d7da; color: #721c24; }}
        .type-code {{ background: #e2e3e5; color: #383d41; }}
        .type-mixed {{ background: #e2e3e5; color: #383d41; }}
        .type-unknown {{ background: #e2e3e5; color: #383d41; }}

        .error-list, .warning-list {{
            list-style: none;
            margin: 1rem 0;
        }}

        .error-list li, .warning-list li {{
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
            border-left: 4px solid;
        }}

        .error-list li {{
            background: #f8d7da;
            border-left-color: #dc3545;
            color: #721c24;
        }}

        .warning-list li {{
            background: #fff3cd;
            border-left-color: #ff5100;
            color: #856404;
        }}

        .error-code {{
            font-family: monospace;
            font-weight: bold;
            margin-right: 0.5rem;
        }}

        .error-count {{
            float: right;
            background: rgba(0,0,0,0.1);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
        }}

        .footer {{
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid #dee2e6;
            text-align: center;
            color: #6c757d;
            font-size: 0.85rem;
        }}

        .footer-logo {{
            color: #116df8;
            font-weight: bold;
            font-size: 1rem;
        }}

        .detection-info {{
            background: #e7f3ff;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
            font-size: 0.9rem;
        }}

        .detection-info strong {{
            color: #116df8;
        }}

        .top-values {{
            font-size: 0.85rem;
            color: #6c757d;
        }}

        .top-value-item {{
            display: inline-block;
            margin-right: 1rem;
            white-space: nowrap;
        }}

        .null-count {{
            color: #dc3545;
            font-weight: 600;
        }}

        .distinct-count {{
            color: #116df8;
            font-weight: 600;
        }}

        .collapsible-section {{
            margin-top: 1rem;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            overflow: hidden;
        }}

        .collapsible-header {{
            background: #f8f9fa;
            padding: 0.75rem;
            cursor: pointer;
            user-select: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
            color: #116df8;
        }}

        .collapsible-header:hover {{
            background: #e9ecef;
        }}

        .collapsible-content {{
            display: none;
            padding: 1rem;
            border-top: 1px solid #dee2e6;
        }}

        .collapsible-content.show {{
            display: block;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }}

        .metric-card {{
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 0.75rem;
        }}

        .metric-label {{
            font-size: 0.75rem;
            color: #6c757d;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}

        .metric-value {{
            font-size: 1rem;
            color: #212529;
            font-weight: 500;
            word-break: break-word;
        }}

        @media print {{
            body {{
                padding: 0;
                background: white;
            }}

            .container {{
                box-shadow: none;
            }}

            tr:hover {{
                background: transparent;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Data Profile Report</h1>
            <div class="run-id">Run ID: {run_id}</div>
        </div>
''')

    # File summary section
    html_parts.append('''
        <h2>File Summary</h2>
        <div class="summary-grid">
''')

    html_parts.append(f'''
            <div class="summary-card">
                <div class="summary-label">Total Rows</div>
                <div class="summary-value">{row_count:,}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Total Columns</div>
                <div class="summary-value">{col_count}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Delimiter</div>
                <div class="summary-value">{delimiter_name}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Line Endings</div>
                <div class="summary-value">{'CRLF' if crlf_detected else 'LF'}</div>
            </div>
''')

    # Quality metrics
    if total_errors == 0 and total_warnings == 0:
        html_parts.append('''
            <div class="summary-card success">
                <div class="summary-label">Quality Status</div>
                <div class="summary-value">Clean</div>
            </div>
''')
    elif total_errors > 0:
        html_parts.append(f'''
            <div class="summary-card error">
                <div class="summary-label">Errors</div>
                <div class="summary-value">{total_errors:,}</div>
            </div>
''')

    if total_warnings > 0:
        html_parts.append(f'''
            <div class="summary-card warning">
                <div class="summary-label">Warnings</div>
                <div class="summary-value">{total_warnings:,}</div>
            </div>
''')

    html_parts.append('        </div>')

    # Detection info if available
    if delimiter_detected or quoting_detected:
        html_parts.append('''
        <div class="detection-info">
            <strong>Auto-Detection Results:</strong>
''')

        if delimiter_detected and delimiter_confidence:
            html_parts.append(f'''
            <div>Delimiter auto-detected as <strong>{delimiter_name}</strong> with {delimiter_confidence:.0%} confidence</div>
''')

        if quoting_detected and quoting_confidence:
            quoting_status = "quoted" if quoted else "unquoted"
            html_parts.append(f'''
            <div>Fields detected as <strong>{quoting_status}</strong> with {quoting_confidence:.0%} confidence</div>
''')

        html_parts.append('        </div>')

    # Errors section
    if errors:
        html_parts.append('''
        <h2>Errors</h2>
        <ul class="error-list">
''')
        for error in errors:
            code = error.get('code', 'UNKNOWN')
            message = error.get('message', 'No message')
            count = error.get('count', 0)
            html_parts.append(f'''
            <li>
                <span class="error-code">{code}</span>
                <span>{message}</span>
                <span class="error-count">{count:,} occurrence(s)</span>
            </li>
''')
        html_parts.append('        </ul>')

    # Warnings section
    if warnings:
        html_parts.append('''
        <h2>Warnings</h2>
        <ul class="warning-list">
''')
        for warning in warnings:
            code = warning.get('code', 'UNKNOWN')
            message = warning.get('message', 'No message')
            count = warning.get('count', 0)
            html_parts.append(f'''
            <li>
                <span class="error-code">{code}</span>
                <span>{message}</span>
                <span class="error-count">{count:,} occurrence(s)</span>
            </li>
''')
        html_parts.append('        </ul>')

    # Column profiles section
    html_parts.append('''
        <h2>Column Profiles</h2>
        <p>Click on any column name to expand and see detailed metrics</p>
''')

    for col in columns:
        col_name = col.get('name', 'Unknown')
        col_type = col.get('type', 'unknown')
        null_count = col.get('null_count', 0)
        distinct_count = col.get('distinct_count', 0)
        distinct_pct = col.get('distinct_pct', 0.0)

        # Build collapsible section with detailed metrics
        html_parts.append(f'''
        <div class="collapsible-section">
            <a href="#" class="collapsible-header" onclick="toggleCollapsible(event)">
                <span><span class="arrow">▶</span> {col_name} <span class="type-badge type-{col_type}">{col_type}</span></span>
                <span style="font-size: 0.85rem; font-weight: normal; color: #6c757d;">{distinct_count:,} distinct, {null_count:,} nulls</span>
            </a>
            <div class="collapsible-content">
                <div class="metrics-grid">
''')

        # Basic metrics
        html_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-label">Null Count</div>
                        <div class="metric-value">{null_count:,}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Distinct Count</div>
                        <div class="metric-value">{distinct_count:,}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Distinct %</div>
                        <div class="metric-value">{distinct_pct:.1f}%</div>
                    </div>
''')

        # Type-specific metrics
        if col_type == 'numeric':
            min_val = col.get('min')
            max_val = col.get('max')
            mean = col.get('mean')
            median = col.get('median')
            stddev = col.get('stddev')
            quantiles = col.get('quantiles', {})
            gaussian_pvalue = col.get('gaussian_pvalue')

            html_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-label">Min Value</div>
                        <div class="metric-value">{_format_number(min_val) if min_val is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Value</div>
                        <div class="metric-value">{_format_number(max_val) if max_val is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Mean</div>
                        <div class="metric-value">{_format_number(mean) if mean is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Median</div>
                        <div class="metric-value">{_format_number(median) if median is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Std Dev</div>
                        <div class="metric-value">{_format_number(stddev) if stddev is not None else 'N/A'}</div>
                    </div>
''')

            if gaussian_pvalue is not None:
                html_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-label">Gaussian p-value</div>
                        <div class="metric-value">{gaussian_pvalue:.4f}</div>
                    </div>
''')

            if quantiles:
                html_parts.append('''
                    <div class="metric-card">
                        <div class="metric-label">Quantiles</div>
                        <div class="metric-value"><small>''')
                for q_name, q_value in sorted(quantiles.items()):
                    if q_value is not None:
                        html_parts.append(f'{q_name}: {_format_number(q_value)}<br>')
                html_parts.append('</small></div>\n                    </div>')

        elif col_type == 'money':
            min_val = col.get('min_value')
            max_val = col.get('max_value')
            valid_count = col.get('valid_count')
            invalid_count = col.get('invalid_count')
            two_decimal_ok = col.get('two_decimal_ok')
            disallowed_symbols = col.get('disallowed_symbols_found')

            html_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-label">Min Value</div>
                        <div class="metric-value">${_format_number(min_val) if min_val is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Value</div>
                        <div class="metric-value">${_format_number(max_val) if max_val is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Valid Count</div>
                        <div class="metric-value">{valid_count if valid_count is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Invalid Count</div>
                        <div class="metric-value">{invalid_count if invalid_count is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">2 Decimal OK</div>
                        <div class="metric-value">{'Yes' if two_decimal_ok else 'No'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Disallowed Symbols</div>
                        <div class="metric-value">{'Found' if disallowed_symbols else 'None'}</div>
                    </div>
''')

        elif col_type == 'date':
            min_date = col.get('min_date')
            max_date = col.get('max_date')
            detected_format = col.get('detected_format')
            format_consistent = col.get('format_consistent')
            valid_count = col.get('valid_count')
            invalid_count = col.get('invalid_count')
            span_days = col.get('span_days')

            html_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-label">Min Date</div>
                        <div class="metric-value">{min_date if min_date else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Date</div>
                        <div class="metric-value">{max_date if max_date else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Detected Format</div>
                        <div class="metric-value">{detected_format if detected_format else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Format Consistent</div>
                        <div class="metric-value">{'Yes' if format_consistent else 'No'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Valid Count</div>
                        <div class="metric-value">{valid_count if valid_count is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Invalid Count</div>
                        <div class="metric-value">{invalid_count if invalid_count is not None else 'N/A'}</div>
                    </div>
''')

            if span_days is not None:
                html_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-label">Date Range (Days)</div>
                        <div class="metric-value">{span_days:,}</div>
                    </div>
''')

        elif col_type in ['alpha', 'varchar', 'code', 'mixed', 'unknown']:
            min_length = col.get('min_length')
            max_length = col.get('max_length')
            avg_length = col.get('avg_length')
            has_non_ascii = col.get('has_non_ascii')
            character_types = col.get('character_types', [])
            cardinality_ratio = col.get('cardinality_ratio')

            html_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-label">Min Length</div>
                        <div class="metric-value">{min_length if min_length is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Length</div>
                        <div class="metric-value">{max_length if max_length is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Avg Length</div>
                        <div class="metric-value">{f"{avg_length:.1f}" if avg_length is not None else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Non-ASCII Chars</div>
                        <div class="metric-value">{'Yes' if has_non_ascii else 'No'}</div>
                    </div>
''')

            if col_type == 'code' and cardinality_ratio is not None:
                html_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-label">Cardinality Ratio</div>
                        <div class="metric-value">{cardinality_ratio:.1%}</div>
                    </div>
''')

            if character_types:
                html_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-label">Character Types</div>
                        <div class="metric-value"><small>{', '.join(character_types)}</small></div>
                    </div>
''')

        # Top values
        top_values = col.get('top_values', [])
        if top_values:
            html_parts.append('''
                </div>
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #dee2e6;">
                    <h4 style="margin-bottom: 0.5rem;">Top Values</h4>
                    <div style="font-size: 0.9rem;">
''')
            for i, item in enumerate(top_values[:10], 1):
                value = item.get('value', '')
                count = item.get('count', 0)
                value_str = str(value)[:100]
                if len(str(value)) > 100:
                    value_str += '...'
                value_str = value_str.replace('<', '&lt;').replace('>', '&gt;')
                html_parts.append(f'                        <div style="margin-bottom: 0.5rem;"><strong>{i}.</strong> {value_str} <span style="color: #6c757d;">({count:,})</span></div>\n')
            html_parts.append('''
                    </div>
''')
        else:
            html_parts.append('''
                </div>
''')

        html_parts.append('''
            </div>
        </div>
''')

    # Candidate keys section
    if candidate_keys:
        html_parts.append('''
        <h2>Candidate Keys</h2>
        <p>These columns have high cardinality and may be suitable as primary keys:</p>
        <table>
            <thead>
                <tr>
                    <th>Column(s)</th>
                    <th>Distinct Ratio</th>
                    <th>Null Ratio</th>
                    <th>Score</th>
                </tr>
            </thead>
            <tbody>
''')

        for key in candidate_keys:
            columns_list = key.get('columns', [])
            columns_str = ', '.join(columns_list)
            distinct_ratio = key.get('distinct_ratio', 0.0)
            null_ratio = key.get('null_ratio_sum', 0.0)
            score = key.get('score', 0.0)

            html_parts.append(f'''
                <tr>
                    <td><strong>{columns_str}</strong></td>
                    <td>{distinct_ratio:.1%}</td>
                    <td>{null_ratio:.1%}</td>
                    <td>{score:.3f}</td>
                </tr>
''')

        html_parts.append('''
            </tbody>
        </table>
''')

    # Footer
    html_parts.append('''
        <div class="footer">
            <div class="footer-logo">VisiQuate Data Profiler</div>
            <div>Generated from REST API v1.0</div>
        </div>
    </div>
</body>
</html>
''')

    return ''.join(html_parts)


def _delimiter_to_name(delimiter: str) -> str:
    """Convert delimiter character to friendly name."""
    delimiter_map = {
        ',': 'Comma',
        '|': 'Pipe',
        '\t': 'Tab',
        ';': 'Semicolon'
    }
    return delimiter_map.get(delimiter, repr(delimiter))


def _build_statistics_html(col: Dict[str, Any], col_type: str) -> str:
    """Build statistics HTML based on column type."""
    stats_parts = []

    if col_type == 'numeric':
        min_val = col.get('min')
        max_val = col.get('max')
        mean = col.get('mean')
        median = col.get('median')
        stddev = col.get('stddev')

        if min_val is not None:
            stats_parts.append(f"Min: {_format_number(min_val)}")
        if max_val is not None:
            stats_parts.append(f"Max: {_format_number(max_val)}")
        if mean is not None:
            stats_parts.append(f"Mean: {_format_number(mean)}")
        if median is not None:
            stats_parts.append(f"Median: {_format_number(median)}")
        if stddev is not None:
            stats_parts.append(f"StdDev: {_format_number(stddev)}")

    elif col_type == 'money':
        min_val = col.get('min_value')
        max_val = col.get('max_value')
        valid_count = col.get('valid_count')
        invalid_count = col.get('invalid_count')

        if min_val is not None:
            stats_parts.append(f"Min: ${_format_number(min_val)}")
        if max_val is not None:
            stats_parts.append(f"Max: ${_format_number(max_val)}")
        if valid_count is not None:
            stats_parts.append(f"Valid: {valid_count:,}")
        if invalid_count is not None and invalid_count > 0:
            stats_parts.append(f"Invalid: {invalid_count:,}")

    elif col_type == 'date':
        min_date = col.get('min_date')
        max_date = col.get('max_date')
        detected_format = col.get('detected_format')
        valid_count = col.get('valid_count')
        invalid_count = col.get('invalid_count')

        if min_date:
            stats_parts.append(f"Min: {min_date}")
        if max_date:
            stats_parts.append(f"Max: {max_date}")
        if detected_format:
            stats_parts.append(f"Format: {detected_format}")
        if valid_count is not None:
            stats_parts.append(f"Valid: {valid_count:,}")
        if invalid_count is not None and invalid_count > 0:
            stats_parts.append(f"Invalid: {invalid_count:,}")

    elif col_type in ['alpha', 'varchar', 'code', 'mixed', 'unknown']:
        min_length = col.get('min_length')
        max_length = col.get('max_length')
        avg_length = col.get('avg_length')

        if min_length is not None:
            stats_parts.append(f"Min Len: {min_length}")
        if max_length is not None:
            stats_parts.append(f"Max Len: {max_length}")
        if avg_length is not None:
            stats_parts.append(f"Avg Len: {avg_length:.1f}")

    return '<br>'.join(stats_parts) if stats_parts else '-'


def _build_top_values_html(top_values: List[Dict[str, Any]]) -> str:
    """Build top values HTML."""
    if not top_values:
        return '-'

    items = []
    for i, item in enumerate(top_values[:5]):  # Show top 5
        value = item.get('value', '')
        count = item.get('count', 0)
        # Escape HTML and truncate long values
        value_str = str(value)[:50]
        if len(str(value)) > 50:
            value_str += '...'
        value_str = value_str.replace('<', '&lt;').replace('>', '&gt;')
        items.append(f'<span class="top-value-item">{value_str} ({count:,})</span>')

    return '<br>'.join(items)


def _format_number(value: float) -> str:
    """Format number for display."""
    if value is None:
        return 'N/A'

    # Use appropriate formatting based on magnitude
    if abs(value) >= 1000000:
        return f"{value:,.0f}"
    elif abs(value) >= 1:
        return f"{value:,.2f}"
    else:
        return f"{value:.4f}"
