#!/usr/bin/env python3
"""
Test Verification Script for VQ8 Data Profiler
Comprehensive test suite runner with detailed reporting
"""

import subprocess  # nosec B404 - Safe utility script for test verification
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class TestVerifier:
    """Verifies complete test suite and generates comprehensive reports"""

    def __init__(self):
        self.api_dir = Path(__file__).parent
        self.expected_total = 450
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "duration": 0,
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "pass_rate": 0.0,
            "failures_by_category": {},
            "critical_paths_ok": False
        }

    def run_full_suite(self) -> bool:
        """Run complete test suite and capture results"""
        print("=" * 80)
        print("VQ8 DATA PROFILER - TEST VERIFICATION")
        print("=" * 80)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Expected Tests: {self.expected_total}")
        print("=" * 80)
        print()

        start_time = time.time()

        # Run pytest with verbose output
        cmd = [
            "pytest",
            "tests/",
            "--ignore=tests/performance",
            "-v",
            "--tb=short",
            "--no-header",
            "--color=yes",
            "-ra"  # Show summary of all test results
        ]

        print(f"Running command: {' '.join(cmd)}")
        print("-" * 80)
        print()

        try:
            result = subprocess.run(  # nosec B603 - Trusted static pytest command
                cmd,
                cwd=self.api_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            self.results["duration"] = time.time() - start_time

            # Parse output
            output = result.stdout + result.stderr
            self._parse_pytest_output(output)

            # Print full output
            print(output)
            print()

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(" TIMEOUT: Test suite exceeded 5 minutes")
            return False
        except Exception as e:
            print(f" ERROR: Failed to run tests: {e}")
            return False

    def _parse_pytest_output(self, output: str):
        """Parse pytest output to extract test metrics"""
        lines = output.split('\n')

        for line in lines:
            # Look for summary line like: "=== 338 passed, 112 failed in 7.55s ==="
            if 'passed' in line and 'failed' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed,' and i > 0:
                        try:
                            self.results["passed"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                    elif part == 'failed' and i > 0:
                        try:
                            self.results["failed"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                    elif part == 'error' and i > 0:
                        try:
                            self.results["errors"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass

            # Look for summary line with just passed: "=== 450 passed in 7.55s ==="
            elif 'passed in' in line and 'failed' not in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        try:
                            self.results["passed"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass

        # Calculate totals
        self.results["tests_run"] = (
            self.results["passed"] +
            self.results["failed"] +
            self.results["errors"]
        )

        if self.results["tests_run"] > 0:
            self.results["pass_rate"] = (
                self.results["passed"] / self.results["tests_run"] * 100
            )

    def verify_critical_paths(self) -> bool:
        """Run quick sanity checks on critical functionality"""
        print("=" * 80)
        print("CRITICAL PATH VERIFICATION")
        print("=" * 80)
        print()

        critical_tests = [
            ("Audit Logging", "tests/test_audit.py"),
            ("Candidate Keys", "tests/test_candidate_keys.py"),
            ("Date Validation", "tests/test_date.py"),
            ("Money Validation", "tests/test_money.py"),
            ("API Health", "tests/unit/test_api.py::test_health_check"),
        ]

        all_passed = True

        for name, test_path in critical_tests:
            cmd = ["pytest", test_path, "-v", "--tb=line", "-q"]

            try:
                result = subprocess.run(  # nosec B603 - Trusted static pytest command
                    cmd,
                    cwd=self.api_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                passed = result.returncode == 0
                status = "PASS" if passed else "FAIL"
                symbol = "✓" if passed else "✗"

                print(f"{symbol} {name:<20} {status}")

                if not passed:
                    all_passed = False
                    print(f"  Output: {result.stdout[:200]}")

            except Exception as e:
                print(f"✗ {name:<20} ERROR: {e}")
                all_passed = False

        print()
        self.results["critical_paths_ok"] = all_passed
        return all_passed

    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("")
        report.append("=" * 80)
        report.append("TEST VERIFICATION REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Timestamp:       {self.results['timestamp']}")
        report.append(f"Duration:        {self.results['duration']:.2f} seconds")
        report.append("")
        report.append("TEST RESULTS")
        report.append("-" * 80)
        report.append(f"Tests Run:       {self.results['tests_run']}")
        report.append(f"Expected:        {self.expected_total}")
        report.append(f"Passed:          {self.results['passed']}")
        report.append(f"Failed:          {self.results['failed']}")
        report.append(f"Errors:          {self.results['errors']}")
        report.append(f"Pass Rate:       {self.results['pass_rate']:.1f}%")
        report.append("")

        # Success criteria
        report.append("SUCCESS CRITERIA")
        report.append("-" * 80)

        target_achieved = self.results["tests_run"] == self.expected_total
        all_passed = self.results["passed"] == self.expected_total
        critical_ok = self.results["critical_paths_ok"]

        report.append(f"✓ Target test count:  {target_achieved}  "
                     f"({self.results['tests_run']}/{self.expected_total})")
        report.append(f"{'✓' if all_passed else '✗'} All tests passing:  "
                     f"{all_passed}  ({self.results['passed']}/{self.expected_total})")
        report.append(f"{'✓' if critical_ok else '✗'} Critical paths:     "
                     f"{critical_ok}")
        report.append("")

        # Final status
        if all_passed and target_achieved and critical_ok:
            report.append("FINAL STATUS: ✓ SUCCESS - READY FOR CI/CD")
            report.append("")
            report.append("All 450 tests passing with 100% pass rate.")
            report.append("Critical paths verified successfully.")
            report.append("Test suite is production-ready.")
        elif self.results["pass_rate"] >= 95:
            report.append("FINAL STATUS: ⚠ PARTIAL SUCCESS")
            report.append("")
            report.append(f"Pass rate: {self.results['pass_rate']:.1f}% (>= 95% threshold)")
            report.append(f"Remaining failures: {self.results['failed']}")
            report.append("Manual review recommended before CI/CD deployment.")
        else:
            report.append("FINAL STATUS: ✗ NEEDS WORK")
            report.append("")
            report.append(f"Pass rate: {self.results['pass_rate']:.1f}% (< 95% threshold)")
            report.append(f"Failed tests: {self.results['failed']}")
            report.append(f"Error count: {self.results['errors']}")
            report.append("Additional fixes required.")

        report.append("")
        report.append("=" * 80)
        report.append("")

        return '\n'.join(report)

    def save_results(self):
        """Save results to JSON file"""
        output_file = self.api_dir / "test_verification_results.json"

        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"Results saved to: {output_file}")

    def run_verification(self) -> bool:
        """Run complete verification workflow"""
        # Step 1: Run full test suite
        suite_passed = self.run_full_suite()

        # Step 2: Verify critical paths
        critical_passed = self.verify_critical_paths()

        # Step 3: Generate report
        report = self.generate_report()
        print(report)

        # Step 4: Save results
        self.save_results()

        # Return success if all tests pass
        return suite_passed and critical_passed and self.results["pass_rate"] == 100.0


def main():
    """Main entry point"""
    verifier = TestVerifier()
    success = verifier.run_verification()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
