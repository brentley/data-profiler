# Operations Guide

This guide covers deployment, monitoring, maintenance, and troubleshooting of the VQ8 Data Profiler in production and development environments.

## Table of Contents

1. [Deployment](#deployment)
2. [Configuration](#configuration)
3. [Monitoring](#monitoring)
4. [Log Management](#log-management)
5. [Data Management](#data-management)
6. [Backup and Recovery](#backup-and-recovery)
7. [Performance Tuning](#performance-tuning)
8. [Security](#security)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance Tasks](#maintenance-tasks)

## Deployment

### Local Development Deployment

For local development and testing:

```bash
# Start services
docker compose up -d

# Verify health
curl http://localhost:8000/healthz

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Production Deployment (Future)

For production deployment with cloud infrastructure:

#### Requirements

- Kubernetes cluster or Docker Swarm
- Load balancer
- Persistent storage (NFS, EBS, Azure Disk)
- Monitoring stack (Prometheus, Grafana)
- Log aggregation (ELK, Splunk, CloudWatch)

#### Docker Compose Production

**`docker-compose.prod.yml`**:
```yaml
version: '3.8'

services:
  api:
    image: ghcr.io/visiquate/data-profiler-api:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - data-work:/data/work
      - data-outputs:/data/outputs
    environment:
      - WORK_DIR=/data/work
      - OUTPUT_DIR=/data/outputs
      - MAX_SPILL_GB=100
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
        reservations:
          cpus: '2'
          memory: 8G

  web:
    image: ghcr.io/visiquate/data-profiler-web:latest
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      - API_URL=http://api:8000
    depends_on:
      - api

volumes:
  data-work:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/data/work
  data-outputs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/data/outputs
```

#### Kubernetes Deployment

**`k8s/deployment.yaml`**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-profiler-api
  labels:
    app: data-profiler
    component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-profiler
      component: api
  template:
    metadata:
      labels:
        app: data-profiler
        component: api
    spec:
      containers:
      - name: api
        image: ghcr.io/visiquate/data-profiler-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: WORK_DIR
          value: "/data/work"
        - name: OUTPUT_DIR
          value: "/data/outputs"
        - name: MAX_SPILL_GB
          value: "100"
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
          limits:
            memory: "16Gi"
            cpu: "4"
        volumeMounts:
        - name: data-work
          mountPath: /data/work
        - name: data-outputs
          mountPath: /data/outputs
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: data-work
        persistentVolumeClaim:
          claimName: data-work-pvc
      - name: data-outputs
        persistentVolumeClaim:
          claimName: data-outputs-pvc
```

## Configuration

### Environment Variables

#### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API server bind address |
| `API_PORT` | `8000` | API server port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `WORKERS` | `4` | Number of Uvicorn workers |

#### Storage Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WORK_DIR` | `/data/work` | Temporary workspace directory |
| `OUTPUT_DIR` | `/data/outputs` | Final artifacts directory |
| `MAX_SPILL_GB` | `50` | Maximum disk space for temp files (GB) |

#### Processing Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BATCH_SIZE` | `10000` | Rows per batch for streaming |
| `GAUSSIAN_TEST` | `dagostino` | Statistical test for normality |
| `MAX_TOP_VALUES` | `10` | Number of top values to track |

#### Security Configuration (v2+)

| Variable | Default | Description |
|----------|---------|-------------|
| `OIDC_ISSUER` | - | OIDC provider URL |
| `OIDC_CLIENT_ID` | - | OAuth2 client ID |
| `OIDC_CLIENT_SECRET` | - | OAuth2 client secret |
| `JWT_SECRET` | - | JWT signing secret |

### Configuration Files

#### `.env` Example

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
WORKERS=4

# Storage Configuration
WORK_DIR=/data/work
OUTPUT_DIR=/data/outputs
MAX_SPILL_GB=50

# Processing Configuration
BATCH_SIZE=10000
GAUSSIAN_TEST=dagostino
MAX_TOP_VALUES=10

# Monitoring (optional)
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
```

## Monitoring

### Health Checks

#### API Health Endpoint

```bash
# Basic health check
curl http://localhost:8000/healthz

# Response:
{
  "status": "ok",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

#### Docker Health Check

```bash
# Check container health
docker ps

# Inspect health status
docker inspect data-profiler_api_1 | jq '.[0].State.Health'
```

### Metrics Collection

#### Prometheus Integration (Future)

**Metrics to Track**:

**Application Metrics**:
- `profiler_runs_total{status="completed|failed"}` - Total runs by status
- `profiler_processing_duration_seconds` - Processing time histogram
- `profiler_file_size_bytes` - Input file size histogram
- `profiler_rows_processed_total` - Total rows processed
- `profiler_errors_total{code="E_*"}` - Errors by code

**System Metrics**:
- `process_cpu_seconds_total` - CPU usage
- `process_resident_memory_bytes` - Memory usage
- `process_open_fds` - Open file descriptors
- `disk_usage_bytes{path="/data/work"}` - Disk usage

**Example Prometheus Config**:
```yaml
scrape_configs:
  - job_name: 'data-profiler'
    static_configs:
      - targets: ['api:9090']
    scrape_interval: 15s
```

### Grafana Dashboards

**Key Visualizations**:

1. **Processing Performance**:
   - Processing time by file size
   - Throughput (rows/sec)
   - Success/failure rate

2. **System Health**:
   - CPU and memory usage
   - Disk I/O
   - Network throughput

3. **Error Tracking**:
   - Errors by code (stacked bar chart)
   - Error rate over time
   - Top 10 error codes

## Log Management

### Log Levels

| Level | Use Case |
|-------|----------|
| DEBUG | Detailed diagnostic information |
| INFO | General informational messages |
| WARNING | Warning messages (recoverable issues) |
| ERROR | Error messages (processing issues) |
| CRITICAL | Critical errors (system failures) |

### Log Format

All logs use structured JSON format:

```json
{
  "timestamp": "2025-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "services.ingest",
  "message": "Processing started",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_size_bytes": 1073741824,
  "columns": 50
}
```

### Log Locations

#### Docker Logs

```bash
# View API logs
docker compose logs api -f

# View web logs
docker compose logs web -f

# View last 100 lines
docker compose logs api --tail=100

# Save logs to file
docker compose logs api > api.log
```

#### Application Logs

**Location**: `/data/outputs/{run_id}/audit.log.json`

**Contents**:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-01-15T10:30:00Z",
  "input_file_hash": "sha256:abc123...",
  "byte_count": 1073741824,
  "row_count": 500000,
  "column_count": 50,
  "delimiter": "|",
  "utf8_valid": true,
  "processing_time_seconds": 127.5,
  "errors": {
    "E_NUMERIC_FORMAT": 42,
    "W_DATE_RANGE": 7
  }
}
```

### Log Aggregation

#### ELK Stack Setup

**Filebeat Config** (`filebeat.yml`):
```yaml
filebeat.inputs:
- type: container
  paths:
    - '/var/lib/docker/containers/*/*.log'
  processors:
    - add_docker_metadata:
        host: "unix:///var/run/docker.sock"

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

#### CloudWatch Logs (AWS)

```bash
# Install CloudWatch agent
docker run \
  --name cloudwatch-agent \
  -v /var/run/docker.sock:/var/run/docker.sock \
  amazon/cloudwatch-agent:latest
```

### Log Rotation

```bash
# Configure Docker log rotation
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  }
}

# Restart Docker
sudo systemctl restart docker
```

## Data Management

### Storage Structure

```
/data/
├── work/                          # Temporary workspace
│   └── runs/
│       └── {run_id}/
│           ├── run.sqlite         # 10-100 MB
│           ├── temp_upload.csv    # Original size
│           └── spill_*.tmp        # Variable
│
└── outputs/                       # Final artifacts
    └── {run_id}/
        ├── profile.json           # 100 KB - 5 MB
        ├── metrics.csv            # 10 KB - 500 KB
        ├── report.html            # 200 KB - 2 MB
        └── audit.log.json         # 5 KB - 50 KB
```

### Disk Space Management

#### Monitoring Disk Usage

```bash
# Check overall disk usage
df -h /data

# Check workspace size
du -sh /data/work

# Check outputs size
du -sh /data/outputs

# Find large files
find /data/work -type f -size +1G -exec ls -lh {} \;
```

#### Cleanup Strategies

**Automatic Cleanup** (Cron Job):
```bash
# /etc/cron.daily/cleanup-data-profiler
#!/bin/bash

# Remove runs older than 30 days
find /data/work/runs -type d -mtime +30 -exec rm -rf {} \;
find /data/outputs -type d -mtime +30 -exec rm -rf {} \;

# Log cleanup
echo "Cleanup completed at $(date)" >> /var/log/data-profiler-cleanup.log
```

**Manual Cleanup**:
```bash
# Remove specific run
rm -rf /data/work/runs/{run_id}
rm -rf /data/outputs/{run_id}

# Keep only last 100 runs
cd /data/work/runs
ls -t | tail -n +101 | xargs rm -rf
```

**Cleanup Script** (`scripts/cleanup.sh`):
```bash
#!/bin/bash

# Remove completed runs older than specified days
DAYS_OLD=${1:-30}

echo "Removing runs older than $DAYS_OLD days..."

WORK_DIR="/data/work/runs"
OUTPUT_DIR="/data/outputs"

# Find and remove old work directories
find "$WORK_DIR" -maxdepth 1 -type d -mtime +$DAYS_OLD -print0 | \
  xargs -0 -I {} rm -rf {}

# Find and remove old output directories
find "$OUTPUT_DIR" -maxdepth 1 -type d -mtime +$DAYS_OLD -print0 | \
  xargs -0 -I {} rm -rf {}

echo "Cleanup complete"

# Show remaining disk space
df -h /data
```

### Data Retention Policy

**Recommended Policies**:

1. **Hot Storage** (Fast access, 7 days):
   - Recent runs in `/data/outputs`
   - Keep all artifacts

2. **Warm Storage** (Archive, 30 days):
   - Compress and move to archive location
   - Keep only `profile.json` and `audit.log.json`

3. **Cold Storage** (Long-term, 1+ year):
   - Move to S3/Glacier
   - Keep only `audit.log.json` for compliance

**Implementation**:
```bash
#!/bin/bash

# Hot to Warm (after 7 days)
find /data/outputs -type d -mtime +7 -mtime -30 | while read dir; do
  # Keep only essential files
  cd "$dir"
  rm -f metrics.csv report.html
  gzip profile.json
done

# Warm to Cold (after 30 days)
find /data/outputs -type d -mtime +30 | while read dir; do
  RUN_ID=$(basename "$dir")

  # Upload to S3
  aws s3 cp "$dir/audit.log.json" \
    s3://data-profiler-archive/$RUN_ID/

  # Remove local copy
  rm -rf "$dir"
done
```

## Backup and Recovery

### Backup Strategy

#### What to Back Up

1. **Critical**:
   - Audit logs (`/data/outputs/*/audit.log.json`)
   - Database schemas and migrations

2. **Important**:
   - Profile outputs (`/data/outputs/*/profile.json`)
   - Configuration files (`.env`, `docker-compose.yml`)

3. **Optional**:
   - Full artifacts (CSV, HTML reports)
   - Temporary work files (generally not needed)

#### Backup Script

```bash
#!/bin/bash

BACKUP_DIR="/backups/data-profiler"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"

mkdir -p "$BACKUP_PATH"

# Backup audit logs
echo "Backing up audit logs..."
find /data/outputs -name "audit.log.json" -exec cp {} "$BACKUP_PATH/" \;

# Backup profiles
echo "Backing up profiles..."
find /data/outputs -name "profile.json" -exec cp {} "$BACKUP_PATH/" \;

# Compress backup
echo "Compressing backup..."
tar -czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_DIR" "backup_$TIMESTAMP"
rm -rf "$BACKUP_PATH"

# Upload to S3 (optional)
aws s3 cp "$BACKUP_PATH.tar.gz" s3://backups/data-profiler/

echo "Backup complete: $BACKUP_PATH.tar.gz"
```

#### Automated Backups

**Cron Job** (`/etc/cron.d/data-profiler-backup`):
```
# Daily backup at 2 AM
0 2 * * * root /opt/data-profiler/scripts/backup.sh >> /var/log/backup.log 2>&1

# Weekly full backup on Sundays
0 3 * * 0 root /opt/data-profiler/scripts/full-backup.sh >> /var/log/backup.log 2>&1
```

### Disaster Recovery

#### Recovery Time Objective (RTO)

Target: 4 hours

#### Recovery Point Objective (RPO)

Target: 24 hours (daily backups)

#### Recovery Procedure

1. **Restore Infrastructure**:
```bash
# Restore Docker Compose setup
docker compose up -d

# Verify services
curl http://localhost:8000/healthz
```

2. **Restore Data**:
```bash
# Download backup from S3
aws s3 cp s3://backups/data-profiler/latest.tar.gz /tmp/

# Extract backup
tar -xzf /tmp/latest.tar.gz -C /data/outputs/

# Verify restoration
ls -la /data/outputs/
```

3. **Verify Application**:
```bash
# Test API
curl http://localhost:8000/runs

# Test profile retrieval
curl http://localhost:8000/runs/{run_id}/profile
```

## Performance Tuning

### System-Level Optimization

#### Docker Resource Limits

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
        reservations:
          cpus: '2'
          memory: 8G
```

#### Disk I/O Optimization

```bash
# Use SSD for /data mount
# Configure I/O scheduler
echo deadline > /sys/block/sda/queue/scheduler

# Increase read-ahead
blockdev --setra 4096 /dev/sda
```

#### Network Optimization

```bash
# Increase TCP buffer sizes
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"
```

### Application-Level Optimization

#### Batch Size Tuning

Test different batch sizes:

```python
# Small batches (memory-constrained)
BATCH_SIZE = 5000

# Medium batches (balanced)
BATCH_SIZE = 10000

# Large batches (fast I/O)
BATCH_SIZE = 50000
```

#### SQLite Optimization

```python
# Pragma settings for performance
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA cache_size=-64000")  # 64 MB cache
conn.execute("PRAGMA temp_store=MEMORY")
```

#### Worker Configuration

```bash
# More workers for I/O-bound workload
WORKERS=8

# Fewer workers for CPU-bound workload
WORKERS=2
```

### Benchmarking

```bash
# Benchmark file processing
time curl -X POST http://localhost:8000/runs/{run_id}/upload \
  -F "file=@large_file.csv"

# Monitor resource usage
docker stats data-profiler_api_1

# Profile with py-spy
py-spy record -o profile.svg -- python app.py
```

## Security

### Network Security

#### Firewall Rules

```bash
# Allow only necessary ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 8000/tcp  # Block direct API access

# Enable firewall
ufw enable
```

#### TLS Configuration (v2+)

```nginx
# /etc/nginx/conf.d/data-profiler.conf
server {
    listen 443 ssl http2;
    server_name profiler.example.com;

    ssl_certificate /etc/ssl/certs/profiler.crt;
    ssl_certificate_key /etc/ssl/private/profiler.key;

    ssl_protocols TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://localhost:5173;
    }

    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

### Access Control (v2+)

```python
# RBAC implementation
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def require_role(role: str):
    async def verify(token: str = Depends(oauth2_scheme)):
        user = verify_token(token)
        if role not in user.roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return verify

@app.post("/runs")
async def create_run(user = Depends(require_role("profiler"))):
    # Only users with "profiler" role can create runs
    pass
```

### Secret Management

```bash
# Use environment variables
export DB_PASSWORD=$(cat /run/secrets/db_password)

# Use Docker secrets
docker secret create db_password ./db_password.txt

# Use secrets in compose
services:
  api:
    secrets:
      - db_password
```

## Troubleshooting

### Common Issues

#### Issue: Out of Disk Space

**Symptoms**:
- Processing fails with "No space left on device"
- Disk usage at 100%

**Solution**:
```bash
# Check disk usage
df -h /data

# Find large files
du -sh /data/work/* | sort -h | tail -10

# Clean old runs
./scripts/cleanup.sh 7  # Remove runs older than 7 days

# Increase MAX_SPILL_GB limit
export MAX_SPILL_GB=100
```

#### Issue: High Memory Usage

**Symptoms**:
- Container OOMKilled
- Slow processing
- Swap usage high

**Solution**:
```bash
# Increase Docker memory limit
docker update --memory 16g data-profiler_api_1

# Reduce batch size
export BATCH_SIZE=5000

# Monitor memory
docker stats data-profiler_api_1
```

#### Issue: Slow Processing

**Symptoms**:
- Processing takes much longer than expected
- High CPU usage
- High disk I/O

**Solution**:
```bash
# Check system resources
top
iostat -x 1

# Optimize SQLite
# In app: conn.execute("PRAGMA journal_mode=WAL")

# Use SSD for /data
# Move /data to SSD mount point

# Increase workers (if I/O-bound)
export WORKERS=8
```

### Debug Mode

Enable debug logging:

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Restart service
docker compose restart api

# View detailed logs
docker compose logs api -f | grep DEBUG
```

### Health Check Failures

```bash
# Check service status
docker compose ps

# Check health endpoint
curl -v http://localhost:8000/healthz

# Check container logs
docker compose logs api --tail=50

# Restart unhealthy service
docker compose restart api
```

## Maintenance Tasks

### Daily

- [ ] Check disk space usage
- [ ] Review error logs
- [ ] Monitor processing queue
- [ ] Verify backups completed

### Weekly

- [ ] Review performance metrics
- [ ] Clean up old runs (> 7 days)
- [ ] Update dependencies (if needed)
- [ ] Test disaster recovery procedure

### Monthly

- [ ] Security updates
- [ ] Performance review
- [ ] Capacity planning
- [ ] Documentation updates

### Quarterly

- [ ] Full system backup
- [ ] Load testing
- [ ] Security audit
- [ ] Disaster recovery drill

### Maintenance Windows

**Planned Maintenance**:
1. Notify users 48 hours in advance
2. Schedule during low-usage period
3. Deploy updates with rollback plan
4. Verify all services after update
5. Monitor for issues post-deployment

---

For additional support:
- [Architecture Documentation](ARCHITECTURE.md)
- [API Documentation](API.md)
- [User Guide](USER_GUIDE.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
