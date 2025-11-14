#!/bin/bash
# Live test progress monitor
# Shows real-time test execution status

API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$API_DIR"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

clear

echo "=================================================="
echo "TEST PROGRESS MONITOR"
echo "=================================================="
echo "Monitoring test execution in real-time..."
echo "Press Ctrl+C to stop"
echo "=================================================="
echo ""

# Run tests with live output
pytest tests/ --ignore=tests/performance -v --tb=line 2>&1 | while IFS= read -r line; do
    # Colorize output
    if [[ "$line" == *"PASSED"* ]]; then
        echo -e "\033[0;32m$line\033[0m"  # Green for passed
    elif [[ "$line" == *"FAILED"* ]]; then
        echo -e "\033[0;31m$line\033[0m"  # Red for failed
    elif [[ "$line" == *"ERROR"* ]]; then
        echo -e "\033[0;33m$line\033[0m"  # Yellow for errors
    elif [[ "$line" == *"passed"* ]] || [[ "$line" == *"failed"* ]]; then
        echo -e "\033[1;36m$line\033[0m"  # Cyan for summary
    else
        echo "$line"
    fi
done

echo ""
echo "=================================================="
echo "Monitoring complete"
echo "=================================================="
