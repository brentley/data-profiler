#!/bin/bash
# Quick test status checker
# Usage: ./check_test_status.sh

set -e

API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$API_DIR"

echo "=================================="
echo "QUICK TEST STATUS CHECK"
echo "=================================="
echo "Time: $(date)"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run quick test count
echo "Running quick test check..."
echo ""

# Run pytest with minimal output
pytest tests/ --ignore=tests/performance -q --tb=no --no-header 2>&1 | tail -20

echo ""
echo "=================================="
echo ""

# Check if tests passed
if [ $? -eq 0 ]; then
    echo "✓ STATUS: ALL TESTS PASSING"
else
    echo "✗ STATUS: SOME TESTS FAILING"
    echo ""
    echo "Run './verify_tests.py' for detailed analysis"
fi

echo ""
