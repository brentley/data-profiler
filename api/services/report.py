"""
HTML Report Generation Service.

This module provides functionality to generate professional HTML reports
from profiling results, including responsive design and print-friendly formatting.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from ..models.run import (
    ProfileResponse,
    ColumnProfileResponse,
    ErrorDetail,
    CandidateKey,
)


class HTMLReportGenerator:
    """Generate professional HTML reports from profile data."""

    def __init__(self, profile: ProfileResponse):
        """
        Initialize HTML report generator.

        Args:
            profile: Complete profile response data
        """
        self.profile = profile

    def generate(self) -> str:
        """
        Generate complete HTML report.

        Returns:
            HTML string with embedded CSS and complete report
        """
        html_parts = [
            self._generate_header(),
            self._generate_summary(),
            self._generate_errors_warnings(),
            self._generate_candidate_keys(),
            self._generate_column_profiles(),
            self._generate_footer(),
        ]

        return "\n".join(html_parts)

    def _generate_header(self) -> str:
        """Generate HTML header with CSS styling."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Profile Report - {self.profile.run_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
            font-size: 2em;
        }}

        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}

        h3 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }}

        .summary-card .label {{
            font-size: 0.9em;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        .summary-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }}

        thead {{
            background: #34495e;
            color: white;
        }}

        th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 12px;
            border-bottom: 1px solid #ecf0f1;
        }}

        tbody tr:hover {{
            background: #f8f9fa;
        }}

        .type-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .type-numeric {{ background: #3498db; color: white; }}
        .type-string {{ background: #2ecc71; color: white; }}
        .type-alpha {{ background: #2ecc71; color: white; }}
        .type-varchar {{ background: #2ecc71; color: white; }}
        .type-date {{ background: #9b59b6; color: white; }}
        .type-money {{ background: #f39c12; color: white; }}
        .type-code {{ background: #1abc9c; color: white; }}
        .type-mixed {{ background: #95a5a6; color: white; }}
        .type-unknown {{ background: #7f8c8d; color: white; }}

        .alert {{
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }}

        .alert-error {{
            background: #fee;
            border-left: 4px solid #e74c3c;
            color: #c0392b;
        }}

        .alert-warning {{
            background: #fef8e7;
            border-left: 4px solid #f39c12;
            color: #d68910;
        }}

        .alert-success {{
            background: #eafaf1;
            border-left: 4px solid #27ae60;
            color: #1e8449;
        }}

        .column-section {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
            border: 1px solid #dee2e6;
        }}

        .stats-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}

        .stat-item {{
            padding: 10px;
            background: white;
            border-radius: 4px;
            border: 1px solid #dee2e6;
        }}

        .stat-label {{
            font-size: 0.85em;
            color: #7f8c8d;
            margin-bottom: 4px;
        }}

        .stat-value {{
            font-size: 1.2em;
            font-weight: 600;
            color: #2c3e50;
        }}

        .top-values {{
            margin: 15px 0;
        }}

        .top-value-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px;
            background: white;
            margin: 5px 0;
            border-radius: 4px;
            border: 1px solid #dee2e6;
        }}

        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}

        code {{
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
        }}

        /* Print styles */
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}

            .container {{
                box-shadow: none;
                padding: 20px;
            }}

            .column-section {{
                page-break-inside: avoid;
            }}

            h2 {{
                page-break-after: avoid;
            }}
        }}

        /* Responsive design */
        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
            }}

            .summary-grid {{
                grid-template-columns: 1fr;
            }}

            table {{
                font-size: 0.9em;
            }}

            th, td {{
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Data Profile Report</h1>
        <p><strong>Run ID:</strong> <code>{self.profile.run_id}</code></p>
        <p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
"""

    def _generate_summary(self) -> str:
        """Generate file summary section."""
        file = self.profile.file
        total_errors = sum(e.count for e in self.profile.errors)
        total_warnings = sum(w.count for w in self.profile.warnings)

        return f"""
        <h2>File Summary</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <div class="label">Total Rows</div>
                <div class="value">{file.rows:,}</div>
            </div>
            <div class="summary-card">
                <div class="label">Total Columns</div>
                <div class="value">{file.columns}</div>
            </div>
            <div class="summary-card">
                <div class="label">Delimiter</div>
                <div class="value">{self._escape_html(file.delimiter)}</div>
            </div>
            <div class="summary-card">
                <div class="label">Line Endings</div>
                <div class="value">{"CRLF" if file.crlf_detected else "LF"}</div>
            </div>
            <div class="summary-card">
                <div class="label">Total Errors</div>
                <div class="value">{total_errors:,}</div>
            </div>
            <div class="summary-card">
                <div class="label">Total Warnings</div>
                <div class="value">{total_warnings:,}</div>
            </div>
        </div>

        <h3>Column Headers</h3>
        <p>{", ".join(f"<code>{self._escape_html(h)}</code>" for h in file.header)}</p>
"""

    def _generate_errors_warnings(self) -> str:
        """Generate errors and warnings section."""
        html = ""

        if self.profile.errors:
            html += """
        <h2>Errors</h2>
"""
            for error in self.profile.errors:
                html += f"""
        <div class="alert alert-error">
            <strong>{self._escape_html(error.code)}</strong>: {self._escape_html(error.message)}
            <span style="float: right;">{error.count:,} occurrences</span>
        </div>
"""

        if self.profile.warnings:
            html += """
        <h2>Warnings</h2>
"""
            for warning in self.profile.warnings:
                html += f"""
        <div class="alert alert-warning">
            <strong>{self._escape_html(warning.code)}</strong>: {self._escape_html(warning.message)}
            <span style="float: right;">{warning.count:,} occurrences</span>
        </div>
"""

        if not self.profile.errors and not self.profile.warnings:
            html += """
        <div class="alert alert-success">
            No errors or warnings detected during profiling.
        </div>
"""

        return html

    def _generate_candidate_keys(self) -> str:
        """Generate candidate keys section."""
        if not self.profile.candidate_keys:
            return """
        <h2>Candidate Keys</h2>
        <p>No high-quality candidate keys identified (requiring 90%+ distinct ratio with minimal nulls).</p>
"""

        html = """
        <h2>Candidate Keys</h2>
        <p>Columns with high cardinality that may serve as unique identifiers:</p>
        <table>
            <thead>
                <tr>
                    <th>Column(s)</th>
                    <th>Distinct Ratio</th>
                    <th>Null Ratio</th>
                    <th>Quality Score</th>
                </tr>
            </thead>
            <tbody>
"""

        for key in self.profile.candidate_keys:
            columns_str = ", ".join(self._escape_html(c) for c in key.columns)
            html += f"""
                <tr>
                    <td><code>{columns_str}</code></td>
                    <td>{key.distinct_ratio * 100:.2f}%</td>
                    <td>{key.null_ratio_sum * 100:.2f}%</td>
                    <td>{key.score:.3f}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>
"""
        return html

    def _generate_column_profiles(self) -> str:
        """Generate detailed column profiles section."""
        html = """
        <h2>Column Profiles</h2>
"""

        for col in self.profile.columns:
            html += self._generate_column_detail(col)

        return html

    def _generate_column_detail(self, col: ColumnProfileResponse) -> str:
        """Generate detailed profile for a single column."""
        type_class = f"type-{col.type}"

        html = f"""
        <div class="column-section">
            <h3>{self._escape_html(col.name)} <span class="type-badge {type_class}">{col.type}</span></h3>

            <div class="stats-row">
                <div class="stat-item">
                    <div class="stat-label">Null Count</div>
                    <div class="stat-value">{col.null_count:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Distinct Count</div>
                    <div class="stat-value">{col.distinct_count:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Distinct %</div>
                    <div class="stat-value">{col.distinct_pct:.2f}%</div>
                </div>
"""

        # Type-specific stats
        if col.type == "numeric":
            html += self._generate_numeric_stats(col)
        elif col.type in ["alpha", "varchar", "code", "mixed", "unknown"]:
            html += self._generate_string_stats(col)
        elif col.type == "date":
            html += self._generate_date_stats(col)
        elif col.type == "money":
            html += self._generate_money_stats(col)

        html += """
            </div>
"""

        # Top values (available for all types)
        if col.top_values:
            html += """
            <h4>Top Values</h4>
            <div class="top-values">
"""
            for top_val in col.top_values[:10]:
                value = top_val.get("value", "")
                count = top_val.get("count", 0)
                html += f"""
                <div class="top-value-item">
                    <span><code>{self._escape_html(str(value))}</code></span>
                    <span><strong>{count:,}</strong> occurrences</span>
                </div>
"""
            html += """
            </div>
"""

        html += """
        </div>
"""
        return html

    def _generate_numeric_stats(self, col: ColumnProfileResponse) -> str:
        """Generate numeric-specific statistics."""
        html = ""

        if col.min is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Min</div>
                    <div class="stat-value">{col.min:.4f}</div>
                </div>
"""

        if col.max is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Max</div>
                    <div class="stat-value">{col.max:.4f}</div>
                </div>
"""

        if col.mean is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Mean</div>
                    <div class="stat-value">{col.mean:.4f}</div>
                </div>
"""

        if col.median is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Median</div>
                    <div class="stat-value">{col.median:.4f}</div>
                </div>
"""

        if col.stddev is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Std Dev</div>
                    <div class="stat-value">{col.stddev:.4f}</div>
                </div>
"""

        if col.gaussian_pvalue is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Normality p-value</div>
                    <div class="stat-value">{col.gaussian_pvalue:.4f}</div>
                </div>
"""

        return html

    def _generate_string_stats(self, col: ColumnProfileResponse) -> str:
        """Generate string-specific statistics."""
        html = ""

        if col.min_length is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Min Length</div>
                    <div class="stat-value">{col.min_length}</div>
                </div>
"""

        if col.max_length is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Max Length</div>
                    <div class="stat-value">{col.max_length}</div>
                </div>
"""

        if col.avg_length is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Avg Length</div>
                    <div class="stat-value">{col.avg_length:.1f}</div>
                </div>
"""

        if col.has_non_ascii is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Non-ASCII</div>
                    <div class="stat-value">{"Yes" if col.has_non_ascii else "No"}</div>
                </div>
"""

        if col.cardinality_ratio is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Cardinality Ratio</div>
                    <div class="stat-value">{col.cardinality_ratio:.3f}</div>
                </div>
"""

        return html

    def _generate_date_stats(self, col: ColumnProfileResponse) -> str:
        """Generate date-specific statistics."""
        html = ""

        if col.valid_count is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Valid Dates</div>
                    <div class="stat-value">{col.valid_count:,}</div>
                </div>
"""

        if col.invalid_count is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Invalid Dates</div>
                    <div class="stat-value">{col.invalid_count:,}</div>
                </div>
"""

        if col.detected_format:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Format</div>
                    <div class="stat-value"><code>{self._escape_html(col.detected_format)}</code></div>
                </div>
"""

        if col.min_date:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Min Date</div>
                    <div class="stat-value">{self._escape_html(col.min_date)}</div>
                </div>
"""

        if col.max_date:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Max Date</div>
                    <div class="stat-value">{self._escape_html(col.max_date)}</div>
                </div>
"""

        if col.span_days is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Span (days)</div>
                    <div class="stat-value">{col.span_days:,}</div>
                </div>
"""

        return html

    def _generate_money_stats(self, col: ColumnProfileResponse) -> str:
        """Generate money-specific statistics."""
        html = ""

        if col.valid_count is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Valid</div>
                    <div class="stat-value">{col.valid_count:,}</div>
                </div>
"""

        if col.invalid_count is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Invalid</div>
                    <div class="stat-value">{col.invalid_count:,}</div>
                </div>
"""

        if col.min_value is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Min Value</div>
                    <div class="stat-value">${col.min_value:.2f}</div>
                </div>
"""

        if col.max_value is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Max Value</div>
                    <div class="stat-value">${col.max_value:.2f}</div>
                </div>
"""

        if col.two_decimal_ok is not None:
            html += f"""
                <div class="stat-item">
                    <div class="stat-label">Two Decimal OK</div>
                    <div class="stat-value">{"Yes" if col.two_decimal_ok else "No"}</div>
                </div>
"""

        return html

    def _generate_footer(self) -> str:
        """Generate HTML footer."""
        return """
        <div class="footer">
            <p>Generated by Data Profiler API</p>
        </div>
    </div>
</body>
</html>
"""

    @staticmethod
    def _escape_html(text: str) -> str:
        """
        Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            HTML-safe text
        """
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )


def save_html_report(profile: ProfileResponse, output_path: Path) -> None:
    """
    Generate and save HTML report to file.

    Args:
        profile: Complete profile response data
        output_path: Path where HTML file should be saved
    """
    generator = HTMLReportGenerator(profile)
    html_content = generator.generate()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
