#!/bin/bash
# Cleanup old profiling runs from VQ8 Data Profiler
# Keeps the N most recent runs and removes the rest

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default: keep last 10 runs
KEEP_COUNT=${1:-10}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load environment or use defaults
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
fi

WORK_DIR="${WORK_DIR:-$PROJECT_ROOT/data/work}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/data/outputs}"

echo -e "${BLUE}VQ8 Data Profiler - Run Cleanup${NC}"
echo "================================="
echo ""

# Check if directories exist
if [ ! -d "$WORK_DIR/runs" ]; then
    echo -e "${YELLOW}Warning: Work directory not found: $WORK_DIR/runs${NC}"
    exit 0
fi

if [ ! -d "$OUTPUT_DIR" ]; then
    echo -e "${YELLOW}Warning: Output directory not found: $OUTPUT_DIR${NC}"
    exit 0
fi

# Count runs
TOTAL_RUNS=$(find "$WORK_DIR/runs" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')

echo "Total runs found: $TOTAL_RUNS"
echo "Keeping most recent: $KEEP_COUNT"
echo ""

if [ "$TOTAL_RUNS" -le "$KEEP_COUNT" ]; then
    echo -e "${GREEN}✓${NC} No cleanup needed. Current runs ($TOTAL_RUNS) <= keep count ($KEEP_COUNT)"
    exit 0
fi

RUNS_TO_DELETE=$((TOTAL_RUNS - KEEP_COUNT))

echo -e "${YELLOW}⚠ Will delete $RUNS_TO_DELETE old run(s)${NC}"
echo ""

# List runs by modification time (oldest first)
echo "Identifying runs to delete..."
RUNS_TO_REMOVE=$(find "$WORK_DIR/runs" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -n | head -n "$RUNS_TO_DELETE" | cut -d' ' -f2-)

# Show runs to be deleted
echo ""
echo "Runs to be deleted:"
echo "-------------------"
for run in $RUNS_TO_REMOVE; do
    run_id=$(basename "$run")
    modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$run" 2>/dev/null || stat -c "%y" "$run" 2>/dev/null | cut -d'.' -f1)
    echo "  - $run_id (modified: $modified)"
done
echo ""

# Confirm deletion
read -p "$(echo -e "${RED}Are you sure you want to delete these runs? [y/N]${NC} ")" -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Cancelled.${NC}"
    exit 0
fi

echo ""
echo "Deleting old runs..."

DELETED_COUNT=0
FAILED_COUNT=0

for run in $RUNS_TO_REMOVE; do
    run_id=$(basename "$run")

    # Delete from work directory
    if rm -rf "$run"; then
        echo -e "${GREEN}✓${NC} Deleted work: $run_id"
    else
        echo -e "${RED}✗${NC} Failed to delete work: $run_id"
        ((FAILED_COUNT++))
        continue
    fi

    # Delete from output directory if exists
    if [ -d "$OUTPUT_DIR/$run_id" ]; then
        if rm -rf "$OUTPUT_DIR/$run_id"; then
            echo -e "${GREEN}✓${NC} Deleted output: $run_id"
        else
            echo -e "${RED}✗${NC} Failed to delete output: $run_id"
            ((FAILED_COUNT++))
            continue
        fi
    fi

    ((DELETED_COUNT++))
done

echo ""
echo "========================================="
echo "Cleanup Summary:"
echo "  - Deleted: $DELETED_COUNT run(s)"
echo "  - Failed: $FAILED_COUNT run(s)"
echo "  - Remaining: $((TOTAL_RUNS - DELETED_COUNT)) run(s)"
echo "========================================="
echo ""

if [ "$FAILED_COUNT" -gt 0 ]; then
    echo -e "${RED}⚠ Some deletions failed. Check permissions.${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Cleanup completed successfully!${NC}"
fi
