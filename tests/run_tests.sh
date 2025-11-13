#!/bin/bash
# Test runner script for data-profiler
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default options
COVERAGE=true
VERBOSE=true
MARKERS=""
PARALLEL=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --quiet)
            VERBOSE=false
            shift
            ;;
        --unit)
            MARKERS="-m unit"
            shift
            ;;
        --integration)
            MARKERS="-m integration"
            shift
            ;;
        --fast)
            MARKERS="-m 'not slow'"
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        -m)
            MARKERS="-m $2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Starting data-profiler test suite...${NC}"

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo -e "${YELLOW}Consider activating a venv: source .venv/bin/activate${NC}"
fi

# Install dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install -r requirements-test.txt
fi

# Build pytest command
PYTEST_CMD="pytest"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=api --cov-report=term-missing --cov-report=html"
fi

if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD $MARKERS"
fi

# Run tests
echo -e "${GREEN}Running: $PYTEST_CMD${NC}"
$PYTEST_CMD

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    if [ "$COVERAGE" = true ]; then
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
fi
