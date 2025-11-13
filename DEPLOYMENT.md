# VQ8 Data Profiler - Deployment Guide

## Overview

This document covers deployment, operations, and maintenance of the VQ8 Data Profiler.

## Prerequisites

- Docker 20.10+ and Docker Compose v2.0+
- 50+ GB free disk space
- 4+ GB RAM
- Port 8000 (API) and 4173 (Web) available

## Initial Setup

### 1. Clone and Configure

```bash
# Navigate to project
cd /path/to/data-profiler

# Copy environment configuration
cp .env.example .env

# Edit .env as needed (optional)
nano .env
```

### 2. Initialize Data Directories

```bash
# Using Makefile
make init-data

# Or manually
mkdir -p data/work data/outputs
chmod -R u+rwX data/
```

### 3. Build Images

```bash
# Build production images
make build

# Or with docker-compose
docker-compose build
```

## Deployment Modes

### Development Mode (Hot Reload)

Best for active development with auto-reload on code changes:

```bash
# Start development stack
make dev

# Or explicitly
docker-compose -f docker-compose.dev.yml up

# Access:
# - Web: http://localhost:5173 (Vite dev server)
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

**Features:**
- Hot module reload (HMR) for frontend
- API auto-reload on file changes
- Debug logging enabled
- Source code mounted as volumes

### Production Mode

For stable deployments:

```bash
# Start production stack
make up

# Or explicitly
docker-compose up -d

# Access:
# - Web: http://localhost:4173
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

**Features:**
- Optimized builds
- Multi-stage Docker images
- Health checks enabled
- Info-level logging

## Service Management

### Starting Services

```bash
# Production
make up

# Development
make dev

# Background mode
docker-compose up -d
```

### Stopping Services

```bash
# Production
make down

# Development
make dev-down

# Force stop
docker-compose down --volumes --remove-orphans
```

### Restarting Services

```bash
# Restart all services
make restart

# Restart specific service
docker-compose restart api
docker-compose restart web
```

### Viewing Logs

```bash
# Follow all logs
make logs

# Follow specific service
docker-compose logs -f api
docker-compose logs -f web

# View last N lines
docker-compose logs --tail=100 api
```

### Shell Access

```bash
# API container
make shell-api

# Web container
make shell-web

# Or directly
docker-compose exec api /bin/bash
docker-compose exec web /bin/sh
```

## Health Monitoring

### Health Checks

Both containers have health checks configured:

```bash
# Check container health
docker-compose ps

# Inspect health details
docker inspect vq8-profiler-api | jq '.[0].State.Health'
docker inspect vq8-profiler-web | jq '.[0].State.Health'
```

### API Health Endpoint

```bash
# Check API health
curl http://localhost:8000/healthz

# Expected response:
# {"status": "ok", "service": "vq8-profiler", "version": "1.0.0"}
```

### Web Health Check

```bash
# Check web health
curl -I http://localhost:4173/

# Expected: HTTP 200 OK
```

## Data Management

### Data Directory Structure

```
data/
├── work/                    # Temporary processing files
│   ├── runs/               # Per-run SQLite databases
│   │   └── {run_id}/
│   └── temp/               # Temporary files
└── outputs/                # Final artifacts
    ├── {run_id}/
    │   ├── profile.json    # Full profile
    │   ├── metrics.csv     # Per-column metrics
    │   ├── report.html     # HTML report
    │   └── audit.log.json  # Audit trail
    └── archive/            # Archived runs
```

### Cleanup Old Runs

```bash
# Keep last 10 runs (default)
./scripts/cleanup-old-runs.sh

# Keep last 20 runs
./scripts/cleanup-old-runs.sh 20

# Using Makefile (DANGER: deletes ALL)
make clean-data
```

### Backup Outputs

```bash
# Create timestamped backup
make backup-outputs

# Manual backup
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/outputs/

# Restore from backup
tar -xzf backup_20241113_120000.tar.gz
```

### Disk Space Monitoring

```bash
# Check disk usage
du -sh data/work
du -sh data/outputs

# Detailed breakdown
du -h --max-depth=2 data/

# Set alerts when approaching MAX_SPILL_GB
```

## Environment Variables

Key environment variables in `.env`:

```bash
# Storage
WORK_DIR=/data/work           # Temp files location
OUTPUT_DIR=/data/outputs      # Artifacts location
MAX_SPILL_GB=50              # Disk space limit

# Processing
GAUSSIAN_TEST=dagostino      # Statistical test method
DEFAULT_DELIMITER=|          # Default CSV delimiter
BATCH_SIZE=10000             # Processing batch size

# API
LOG_LEVEL=info               # Logging level
LOG_FORMAT=json              # Log format
CORS_ORIGINS=*               # CORS origins (dev only)

# Build metadata (auto-populated)
GIT_COMMIT=dev
BUILD_DATE=unknown
VERSION=1.0.0
```

## Performance Tuning

### For Large Files (3+ GiB)

```bash
# Increase spill space
MAX_SPILL_GB=100

# Increase batch size
BATCH_SIZE=20000

# Increase SQLite cache
SQLITE_CACHE_SIZE_MB=512

# Monitor during processing
docker stats vq8-profiler-api
```

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000
lsof -i :4173

# Kill process or change port in docker-compose.yml
```

### Container Won't Start

```bash
# Check logs
docker-compose logs api
docker-compose logs web

# Rebuild containers
make build

# Clean and rebuild
make clean
make build
```

### Permission Errors

```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/
chmod -R u+rwX data/

# Or run init script again
make init-data
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker resources
docker system prune -a

# Clean old runs
./scripts/cleanup-old-runs.sh 5

# Clean temporary files
make clean
```

### Health Check Failing

```bash
# Check container status
docker-compose ps

# Check health details
docker inspect vq8-profiler-api | jq '.[0].State.Health'

# Manual health check
curl http://localhost:8000/healthz

# Restart unhealthy container
docker-compose restart api
```

### API Not Responding

```bash
# Check if container is running
docker-compose ps

# Check logs for errors
docker-compose logs api

# Check if port is accessible
nc -zv localhost 8000

# Restart API
docker-compose restart api
```

## Security Considerations

### PHI Data Protection

- All data treated as HIPAA-scoped PHI
- Never commit `/data` directory
- Audit logs contain PII-redacted information
- Local-only deployment in v1

### Pre-commit Hooks

Prevents accidental commits of sensitive data:

```bash
# Install hooks
make install

# Or manually
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

### Log Redaction

Logs automatically redact PII:

```bash
# View redacted logs
docker-compose logs api | grep "REDACTED"

# Audit logs in outputs
cat data/outputs/{run_id}/audit.log.json
```

## Monitoring and Observability

### Container Metrics

```bash
# Real-time stats
docker stats

# Specific container
docker stats vq8-profiler-api

# Historical data (with monitoring stack)
# TODO: Add Prometheus/Grafana in v2
```

### Application Logs

Structured JSON logs to stdout:

```bash
# View logs
docker-compose logs -f api

# Filter by level
docker-compose logs api | grep '"level":"error"'

# Filter by run_id
docker-compose logs api | grep '"run_id":"abc123"'
```

### Audit Trail

Per-run audit logs in outputs:

```bash
# View audit log
cat data/outputs/{run_id}/audit.log.json | jq .

# Key fields:
# - input_sha256: File hash
# - byte_count: File size
# - utf8_valid: Encoding validation
# - parser_config: Delimiter, quoting
# - metrics_summary: Row counts, errors
```

## Maintenance Tasks

### Regular Maintenance

**Daily:**
- Monitor disk space usage
- Check container health
- Review error logs

**Weekly:**
- Clean old runs (keep last 10-20)
- Backup important outputs
- Review audit logs

**Monthly:**
- Update Docker images
- Security scans
- Performance review

### Maintenance Scripts

```bash
# Weekly cleanup
./scripts/cleanup-old-runs.sh 20

# Monthly backup
make backup-outputs

# Docker cleanup
docker system prune -a
```

## Upgrading

### Version Updates

```bash
# Pull latest code
git pull origin main

# Rebuild images
make build

# Stop old services
make down

# Start new services
make up

# Verify health
curl http://localhost:8000/healthz
```

### Rolling Back

```bash
# Stop current version
make down

# Checkout previous version
git checkout <previous-tag>

# Rebuild and start
make build
make up
```

## CI/CD Integration

### GitHub Actions (Future)

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build images
        run: make build
      - name: Run tests
        run: make test
```

## Support and Documentation

- **API Documentation**: http://localhost:8000/docs
- **README**: See main README.md
- **Error Codes**: See ERROR_CODES.md
- **Development Guide**: See DEVELOPMENT.md

## Appendix

### Complete Makefile Command Reference

```bash
make help              # Display all commands
make install          # Install dependencies
make dev              # Start dev environment
make dev-build        # Build and start dev
make dev-down         # Stop dev environment
make dev-logs         # Follow dev logs
make test             # Run all tests
make test-unit        # Run unit tests
make test-integration # Run integration tests
make test-watch       # Watch mode tests
make lint             # Run linters
make fmt              # Format code
make security         # Security scans
make build            # Build prod images
make up               # Start prod stack
make down             # Stop prod stack
make logs             # Follow prod logs
make restart          # Restart services
make shell-api        # Shell in API
make shell-web        # Shell in Web
make clean            # Clean temp files
make clean-data       # Delete all data
make init-data        # Initialize dirs
make backup-outputs   # Backup outputs
make version          # Show version
```

### Common Environment Configurations

**Development:**
```bash
LOG_LEVEL=debug
CORS_ORIGINS=*
RELOAD=true
DEBUG=true
```

**Production:**
```bash
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:4173
RELOAD=false
DEBUG=false
```

**Performance:**
```bash
MAX_SPILL_GB=100
BATCH_SIZE=20000
SQLITE_CACHE_SIZE_MB=512
PARALLEL_PROFILERS=true
```
