#!/usr/bin/env python3
"""
Test Failure Analysis Script
Analyzes pytest output to identify patterns and root causes
"""

import subprocess  # nosec B404 - Safe utility script for test analysis
import sys
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


class TestFailureAnalyzer:
    """Analyzes test failures and categorizes them by root cause"""

    def __init__(self):
        self.api_dir = Path(__file__).parent
        self.failures = defaultdict(list)
        self.errors = defaultdict(list)
        self.error_patterns = {
            "AttributeError: 'TypeInferrer' object has no attribute 'infer_type'": "TypeInferrer API",
            "TypeError: CSVParser.__init__() got an unexpected keyword argument": "CSVParser API",
            "AttributeError: 'DistinctCounter' object has no attribute": "DistinctCounter API",
            "ModuleNotFoundError: No module named 'services.pipeline'": "Missing Module",
            "assert 500 == 201": "API 500 Error",
            "KeyError: 'run_id'": "Missing run_id",
            "AttributeError: 'DistinctCountResult' object has no attribute": "DistinctCountResult API",
        }

    def run_tests_verbose(self) -> str:
        """Run tests with verbose output for analysis"""
        print("Running tests with verbose output...")
        print("-" * 80)

        cmd = [
            "pytest",
            "tests/",
            "--ignore=tests/performance",
            "-v",
            "--tb=short",
            "--no-header",
            "-ra"
        ]

        try:
            result = subprocess.run(  # nosec B603 - Trusted static pytest command
                cmd,
                cwd=self.api_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.stdout + "\n" + result.stderr
        except Exception as e:
            print(f"Error running tests: {e}")
            return ""

    def parse_failures(self, output: str):
        """Parse test output to extract failure information"""
        current_test = None
        current_error = []
        in_error_block = False

        for line in output.split('\n'):
            # Detect test failure line
            if 'FAILED' in line and '::' in line:
                if current_test and current_error:
                    self._categorize_failure(current_test, current_error)

                # Extract test name
                match = re.search(r'FAILED (.*?) -', line)
                if match:
                    current_test = match.group(1)
                else:
                    current_test = line.split('FAILED')[1].split('-')[0].strip()

                current_error = []
                in_error_block = True

            # Detect ERROR in collection
            elif 'ERROR' in line and '::' in line:
                if current_test and current_error:
                    self._categorize_error(current_test, current_error)

                match = re.search(r'ERROR (.*?) -', line)
                if match:
                    current_test = match.group(1)
                else:
                    current_test = line.split('ERROR')[1].split('-')[0].strip()

                current_error = []
                in_error_block = True

            # Collect error details
            elif in_error_block:
                if line.strip().startswith('='):
                    in_error_block = False
                    if current_test and current_error:
                        self._categorize_failure(current_test, current_error)
                    current_test = None
                    current_error = []
                elif line.strip():
                    current_error.append(line.strip())

        # Handle last error
        if current_test and current_error:
            self._categorize_failure(current_test, current_error)

    def _categorize_failure(self, test_name: str, error_lines: List[str]):
        """Categorize failure by error pattern"""
        error_text = '\n'.join(error_lines)

        # Try to match against known patterns
        category = "Unknown"
        for pattern, cat in self.error_patterns.items():
            if pattern in error_text:
                category = cat
                break

        self.failures[category].append({
            "test": test_name,
            "error": error_text[:500]  # Truncate long errors
        })

    def _categorize_error(self, test_name: str, error_lines: List[str]):
        """Categorize collection errors"""
        error_text = '\n'.join(error_lines)

        category = "Collection Error"
        for pattern, cat in self.error_patterns.items():
            if pattern in error_text:
                category = cat
                break

        self.errors[category].append({
            "test": test_name,
            "error": error_text[:500]
        })

    def generate_analysis_report(self) -> str:
        """Generate analysis report"""
        report = []
        report.append("")
        report.append("=" * 80)
        report.append("TEST FAILURE ANALYSIS")
        report.append("=" * 80)
        report.append("")

        # Summary
        total_failures = sum(len(v) for v in self.failures.values())
        total_errors = sum(len(v) for v in self.errors.values())

        report.append(f"Total Failures: {total_failures}")
        report.append(f"Total Errors:   {total_errors}")
        report.append("")

        # Failures by category
        if self.failures:
            report.append("FAILURES BY CATEGORY")
            report.append("-" * 80)

            for category, items in sorted(
                self.failures.items(),
                key=lambda x: len(x[1]),
                reverse=True
            ):
                report.append(f"\n{category} ({len(items)} failures)")
                report.append("-" * 40)

                for item in items[:5]:  # Show first 5
                    report.append(f"  • {item['test']}")

                if len(items) > 5:
                    report.append(f"  ... and {len(items) - 5} more")

        # Errors
        if self.errors:
            report.append("")
            report.append("COLLECTION ERRORS")
            report.append("-" * 80)

            for category, items in self.errors.items():
                report.append(f"\n{category} ({len(items)} errors)")
                report.append("-" * 40)

                for item in items[:3]:
                    report.append(f"  • {item['test']}")

        # Recommendations
        report.append("")
        report.append("RECOMMENDED FIXES (Priority Order)")
        report.append("-" * 80)

        priority_fixes = []

        if "TypeInferrer API" in self.failures:
            count = len(self.failures["TypeInferrer API"])
            priority_fixes.append(
                f"1. Fix TypeInferrer API ({count} tests)\n"
                f"   - Check services/types.py for correct method names\n"
                f"   - Update tests/test_type_inference.py"
            )

        if "CSVParser API" in self.failures:
            count = len(self.failures["CSVParser API"])
            priority_fixes.append(
                f"2. Fix CSVParser API ({count} tests)\n"
                f"   - Update tests to use ParserConfig object\n"
                f"   - Modify tests/test_csv_parser.py"
            )

        if "API 500 Error" in self.failures or "Missing run_id" in self.failures:
            count = len(self.failures.get("API 500 Error", [])) + \
                   len(self.failures.get("Missing run_id", []))
            priority_fixes.append(
                f"3. Fix API/Database Issues ({count} tests)\n"
                f"   - Debug database initialization\n"
                f"   - Check tests/conftest.py setup"
            )

        if "Missing Module" in self.failures:
            count = len(self.failures["Missing Module"])
            priority_fixes.append(
                f"4. Fix Missing Module ({count} tests)\n"
                f"   - Create services/pipeline.py or fix imports"
            )

        if "DistinctCounter API" in self.failures:
            count = len(self.failures["DistinctCounter API"])
            priority_fixes.append(
                f"5. Fix DistinctCounter API ({count} tests)\n"
                f"   - Add missing methods to services/distincts.py"
            )

        for fix in priority_fixes:
            report.append(fix)
            report.append("")

        report.append("=" * 80)
        report.append("")

        return '\n'.join(report)

    def analyze(self) -> str:
        """Run complete analysis"""
        output = self.run_tests_verbose()
        self.parse_failures(output)
        return self.generate_analysis_report()


def main():
    """Main entry point"""
    analyzer = TestFailureAnalyzer()
    report = analyzer.analyze()
    print(report)

    # Save to file
    output_file = Path(__file__).parent / "test_failure_analysis.txt"
    with open(output_file, 'w') as f:
        f.write(report)

    print(f"Analysis saved to: {output_file}")


if __name__ == "__main__":
    main()
