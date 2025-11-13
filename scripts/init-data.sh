#!/bin/bash
# Initialize data directories for VQ8 Data Profiler

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Initializing VQ8 Data Profiler data directories..."

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load environment or use defaults
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading configuration from .env..."
    source "$PROJECT_ROOT/.env"
else
    echo -e "${YELLOW}Warning: .env file not found. Using defaults.${NC}"
fi

# Set default directories
WORK_DIR="${WORK_DIR:-$PROJECT_ROOT/data/work}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/data/outputs}"

echo "Creating directory structure..."

# Create work directory
if [ ! -d "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
    echo -e "${GREEN}✓${NC} Created: $WORK_DIR"
else
    echo -e "${YELLOW}○${NC} Already exists: $WORK_DIR"
fi

# Create outputs directory
if [ ! -d "$OUTPUT_DIR" ]; then
    mkdir -p "$OUTPUT_DIR"
    echo -e "${GREEN}✓${NC} Created: $OUTPUT_DIR"
else
    echo -e "${YELLOW}○${NC} Already exists: $OUTPUT_DIR"
fi

# Create subdirectories for organization
mkdir -p "$WORK_DIR/runs"
mkdir -p "$WORK_DIR/temp"
mkdir -p "$OUTPUT_DIR/archive"

echo -e "${GREEN}✓${NC} Created subdirectories"

# Create .gitkeep files to preserve directory structure
touch "$WORK_DIR/.gitkeep"
touch "$OUTPUT_DIR/.gitkeep"

# Set permissions (ensure writable)
chmod -R u+rwX "$PROJECT_ROOT/data"

echo -e "${GREEN}✓${NC} Set permissions"

# Create README in data directory
cat > "$PROJECT_ROOT/data/README.md" << 'EOF'
# Data Directory

This directory contains all working files and outputs for the VQ8 Data Profiler.

**WARNING: This directory contains PHI/PII data and must NEVER be committed to git.**

## Structure

- `/work/` - Temporary files, SQLite databases, streaming buffers
  - `/work/runs/{run_id}/` - Per-run SQLite files
  - `/work/temp/` - Temporary processing files

- `/outputs/` - Final artifacts for completed runs
  - `/outputs/{run_id}/` - Run-specific outputs
    - `profile.json` - Complete profile data
    - `metrics.csv` - Per-column metrics
    - `report.html` - HTML report
    - `audit.log.json` - Audit trail (PII-redacted)
  - `/outputs/archive/` - Archived old runs

## Cleanup

Old runs should be periodically cleaned:

```bash
# Manual cleanup
rm -rf data/work/runs/<old-run-id>
rm -rf data/outputs/<old-run-id>

# Using Makefile
make clean-data  # WARNING: Deletes ALL data
```

## Backup

To backup outputs:

```bash
# Using Makefile
make backup-outputs

# Manual backup
tar -czf backup_$(date +%Y%m%d).tar.gz data/outputs/
```

## Security

- All data is treated as PHI
- Never commit this directory
- Logs are PII-aware and redacted
- Audit trails preserved per run
EOF

echo -e "${GREEN}✓${NC} Created data directory README"

# Display summary
echo ""
echo "========================================="
echo "Data directories initialized successfully!"
echo "========================================="
echo ""
echo "Directories created:"
echo "  - $WORK_DIR"
echo "  - $OUTPUT_DIR"
echo ""
echo "You can now start the application with:"
echo "  make dev    # Development mode"
echo "  make up     # Production mode"
echo ""
echo -e "${YELLOW}IMPORTANT SECURITY NOTES:${NC}"
echo "  - All data is treated as PHI"
echo "  - Never commit the /data directory"
echo "  - Use 'make backup-outputs' to backup results"
echo ""
