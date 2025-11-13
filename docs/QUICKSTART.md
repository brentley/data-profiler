# Quickstart Guide

Get up and running with the VQ8 Data Profiler in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- 8 GB RAM minimum
- 10 GB free disk space

## Installation

### 1. Start the Application

```bash
# Clone repository (if not already)
cd data-profiler

# Start services
docker compose up -d

# Wait for services to start (15-30 seconds)
docker compose ps
```

Expected output:
```
NAME                    STATUS
data-profiler-api-1     Up (healthy)
data-profiler-web-1     Up
```

### 2. Verify Installation

```bash
# Check API health
curl http://localhost:8000/healthz

# Expected response:
# {"status":"ok","timestamp":"2025-01-15T10:30:00Z","version":"1.0.0"}
```

### 3. Access Web UI

Open your browser to: **http://localhost:5173**

You should see the upload page.

## Your First Profile

Let's profile a sample file step by step.

### Prepare Sample Data

Create a sample CSV file:

```bash
cat > sample.csv << 'EOF'
id,name,age,amount,purchase_date
1,John Smith,30,1234.56,20250115
2,Jane Doe,25,5678.90,20250114
3,Bob Johnson,45,9012.34,20250113
4,Alice Williams,35,3456.78,20250112
5,Charlie Brown,28,7890.12,20250111
EOF
```

### Upload and Profile

#### Option 1: Web UI

1. Go to **http://localhost:5173**
2. Click **"Choose File"** and select `sample.csv`
3. Select delimiter: **Comma (`,`)**
4. Click **"Upload and Profile"**
5. Wait for processing (should take < 5 seconds)
6. View results dashboard

#### Option 2: API (curl)

```bash
# Create run
RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"delimiter":",","quoted":true}' \
  | jq -r '.run_id')

echo "Run ID: $RUN_ID"

# Upload file
curl -X POST http://localhost:8000/runs/$RUN_ID/upload \
  -F "file=@sample.csv"

# Check status
curl http://localhost:8000/runs/$RUN_ID/status | jq '.state'

# Get profile (once completed)
curl http://localhost:8000/runs/$RUN_ID/profile | jq '.'
```

#### Option 3: Python

```python
import requests
import time

# Create run
response = requests.post("http://localhost:8000/runs", json={
    "delimiter": ",",
    "quoted": True
})
run_id = response.json()["run_id"]
print(f"Run ID: {run_id}")

# Upload file
with open("sample.csv", "rb") as f:
    requests.post(
        f"http://localhost:8000/runs/{run_id}/upload",
        files={"file": f}
    )

# Poll status
while True:
    response = requests.get(f"http://localhost:8000/runs/{run_id}/status")
    status = response.json()

    if status["state"] == "completed":
        break

    print(f"Progress: {status['progress_pct']:.1f}%")
    time.sleep(1)

# Get profile
profile = requests.get(f"http://localhost:8000/runs/{run_id}/profile").json()

print(f"\nProfile Results:")
print(f"Rows: {profile['file']['rows']}")
print(f"Columns: {profile['file']['columns']}")

for col in profile['columns']:
    print(f"- {col['name']}: {col['inferred_type']} ({col['null_pct']:.1f}% null)")
```

### Understanding the Results

You should see:

**File Summary**:
- Rows: 5
- Columns: 5
- Delimiter: Comma (`,`)

**Column Profiles**:

| Column | Type | Null % | Distinct | Notes |
|--------|------|--------|----------|-------|
| id | numeric | 0% | 5 | High uniqueness (candidate key) |
| name | alpha | 0% | 5 | String values |
| age | numeric | 0% | 5 | Numbers |
| amount | money | 0% | 5 | Exactly 2 decimals |
| purchase_date | date | 0% | 5 | YYYYMMDD format |

**Candidate Keys**:
- Single: `id` (score: 1.0)

### Download Reports

```bash
# JSON profile
curl http://localhost:8000/runs/$RUN_ID/profile > profile.json

# CSV metrics
curl http://localhost:8000/runs/$RUN_ID/metrics.csv > metrics.csv

# HTML report
curl http://localhost:8000/runs/$RUN_ID/report.html > report.html

# Open HTML report
open report.html  # macOS
xdg-open report.html  # Linux
start report.html  # Windows
```

## Common Use Cases

### Profiling a Large File

For files 100 MB+:

```bash
# Upload large file (streaming)
curl -X POST http://localhost:8000/runs/$RUN_ID/upload \
  -F "file=@large_file.csv" \
  --max-time 600  # 10 minute timeout

# Monitor progress
watch -n 2 'curl -s http://localhost:8000/runs/$RUN_ID/status | jq ".progress_pct"'
```

Expected processing times:
- 100 MB: ~5-10 seconds
- 1 GB: ~30-60 seconds
- 3 GB: ~2-4 minutes
- 10 GB: ~8-15 minutes

### Profiling Pipe-Delimited File

```bash
# Create pipe-delimited sample
cat > sample_pipe.txt << 'EOF'
id|name|age|city
1|John Smith|30|New York
2|Jane Doe|25|Los Angeles
3|Bob Johnson|45|Chicago
EOF

# Create run with pipe delimiter
RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"delimiter":"|","quoted":false}' \
  | jq -r '.run_id')

# Upload and profile
curl -X POST http://localhost:8000/runs/$RUN_ID/upload \
  -F "file=@sample_pipe.txt"
```

### Profiling Gzipped File

```bash
# Compress file
gzip -c large_file.csv > large_file.csv.gz

# Upload (automatically decompressed)
curl -X POST http://localhost:8000/runs/$RUN_ID/upload \
  -F "file=@large_file.csv.gz"
```

### Finding Duplicates

```bash
# Get candidate keys
KEYS=$(curl -s http://localhost:8000/runs/$RUN_ID/candidate-keys | jq -r '.suggestions[0].columns')

# Confirm key for duplicate detection
curl -X POST http://localhost:8000/runs/$RUN_ID/confirm-keys \
  -H "Content-Type: application/json" \
  -d "{\"keys\": [$KEYS]}"

# Wait for duplicate detection to complete
# Then get updated profile with duplicate counts
curl http://localhost:8000/runs/$RUN_ID/profile | jq '.duplicate_count'
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Or change ports in docker-compose.yml
# Then restart:
docker compose down
docker compose up -d
```

### Can't Access Web UI

```bash
# Check if web service is running
docker compose ps

# View web logs
docker compose logs web -f

# Restart web service
docker compose restart web
```

### Upload Fails

```bash
# Check API logs
docker compose logs api -f

# Common causes:
# 1. File not UTF-8 encoded
# 2. Missing header row
# 3. Inconsistent column count

# Validate file before upload:
file -i yourfile.csv  # Should show utf-8
head -5 yourfile.csv  # Check header and format
awk -F'|' '{print NF}' yourfile.csv | sort -u  # Check column count consistency
```

### Out of Memory

```bash
# Increase Docker memory limit
docker update --memory 16g data-profiler_api_1

# Or update docker-compose.yml:
services:
  api:
    deploy:
      resources:
        limits:
          memory: 16G
```

### Slow Processing

```bash
# Check system resources
docker stats

# Common causes:
# 1. HDD instead of SSD for /data
# 2. Insufficient memory
# 3. Many columns (100+)

# Solutions:
# - Move /data to SSD
# - Increase memory
# - Process smaller batches
```

## Next Steps

### Learn More

- **[User Guide](USER_GUIDE.md)**: Comprehensive usage documentation
- **[API Documentation](API.md)**: Complete API reference
- **[Error Codes](ERROR_CODES.md)**: Understanding errors and warnings
- **[Architecture](ARCHITECTURE.md)**: System design and internals

### Advanced Features

1. **Custom Validation**: Add custom type validators
2. **Batch Processing**: Profile multiple files
3. **Automated Pipelines**: Integrate with ETL workflows
4. **Custom Reports**: Generate custom report formats

### Integration Examples

#### CI/CD Pipeline

```yaml
# .github/workflows/data-validation.yml
name: Data Validation

on:
  push:
    paths:
      - 'data/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start profiler
        run: docker compose up -d

      - name: Profile data
        run: |
          RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
            -H "Content-Type: application/json" \
            -d '{"delimiter":"|"}' | jq -r '.run_id')

          curl -X POST http://localhost:8000/runs/$RUN_ID/upload \
            -F "file=@data/latest.csv"

          # Wait and check
          sleep 10
          STATUS=$(curl -s http://localhost:8000/runs/$RUN_ID/status | jq -r '.state')

          if [ "$STATUS" != "completed" ]; then
            echo "Profiling failed"
            exit 1
          fi
```

#### Python ETL Integration

```python
# etl_pipeline.py
import requests
from pathlib import Path

def validate_data_quality(file_path: Path) -> bool:
    """Validate data quality before ETL processing."""

    # Profile file
    response = requests.post("http://localhost:8000/runs", json={
        "delimiter": "|",
        "quoted": True
    })
    run_id = response.json()["run_id"]

    # Upload
    with open(file_path, "rb") as f:
        requests.post(
            f"http://localhost:8000/runs/{run_id}/upload",
            files={"file": f}
        )

    # Wait for completion
    while True:
        status = requests.get(f"http://localhost:8000/runs/{run_id}/status").json()
        if status["state"] == "completed":
            break
        elif status["state"] == "failed":
            return False
        time.sleep(2)

    # Check quality thresholds
    profile = requests.get(f"http://localhost:8000/runs/{run_id}/profile").json()

    # Quality checks
    if len(profile["errors"]) > 0:
        print(f"Found {len(profile['errors'])} error types")
        return False

    for col in profile["columns"]:
        if col["null_pct"] > 10:  # More than 10% nulls
            print(f"Column {col['name']} has {col['null_pct']:.1f}% nulls")
            return False

    return True

# Use in pipeline
if validate_data_quality(Path("data/input.csv")):
    print("Data quality OK, proceeding with ETL")
    run_etl_pipeline()
else:
    print("Data quality issues detected, aborting ETL")
```

## Cleanup

### Remove Sample Data

```bash
rm sample.csv sample_pipe.txt
rm profile.json metrics.csv report.html
```

### Stop Services

```bash
# Stop but keep data
docker compose down

# Stop and remove all data
docker compose down -v
```

### Clean Up Old Runs

```bash
# Remove runs older than 7 days
find /data/work/runs -type d -mtime +7 -exec rm -rf {} \;
find /data/outputs -type d -mtime +7 -exec rm -rf {} \;
```

## Support

Need help?

1. **Check Logs**:
   ```bash
   docker compose logs api -f
   docker compose logs web -f
   ```

2. **Review Documentation**:
   - [User Guide](USER_GUIDE.md)
   - [Error Codes](ERROR_CODES.md)
   - [Troubleshooting](USER_GUIDE.md#troubleshooting)

3. **API Documentation**:
   - Interactive: http://localhost:8000/docs
   - Reference: [API.md](API.md)

4. **GitHub Issues**: Report bugs or request features

---

## Summary

You've learned how to:

- ✅ Install and start the profiler
- ✅ Upload and profile files via Web UI and API
- ✅ View profiling results
- ✅ Download reports in multiple formats
- ✅ Troubleshoot common issues

Ready to profile your data!

For production deployment and advanced features, see the complete documentation in the [docs/](.) directory.
