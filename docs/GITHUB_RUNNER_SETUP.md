# GitHub Self-Hosted Runner Setup Guide

## Overview

This guide provides complete instructions for setting up self-hosted GitHub Actions runners for the VQ8 Data Profiler project. Self-hosted runners provide better control over the build environment, faster builds through local caching, and support for multi-architecture Docker builds.

## Table of Contents

- [Why Self-Hosted Runners?](#why-self-hosted-runners)
- [Prerequisites](#prerequisites)
- [Runner Architecture](#runner-architecture)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Docker Support](#docker-support)
- [Multi-Architecture Builds](#multi-architecture-builds)
- [Security Considerations](#security-considerations)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Migration from GitHub-Hosted Runners](#migration-from-github-hosted-runners)

## Why Self-Hosted Runners?

### Benefits
- **Faster builds**: Local caching, no queue time
- **Cost savings**: No GitHub Actions minutes consumed
- **Custom environment**: Full control over installed tools and dependencies
- **Multi-arch builds**: Native ARM64 support for Apple Silicon
- **Persistent cache**: Docker layer caching across builds
- **Network access**: Can access internal resources if needed

### Trade-offs
- **Maintenance**: You manage the infrastructure
- **Security**: Responsible for runner security and isolation
- **Availability**: No automatic scaling like GitHub-hosted runners

## Prerequisites

### Hardware Requirements
- **CPU**: 4+ cores recommended (2 minimum)
- **RAM**: 8GB+ recommended (4GB minimum)
- **Disk**: 100GB+ free space for Docker images and cache
- **Network**: Stable internet connection

### Software Requirements
- **OS**: Ubuntu 22.04 LTS, macOS 12+, or Windows Server 2019+
- **Docker**: 24.0+ with BuildKit support
- **Git**: 2.40+
- **Python**: 3.10+ (for API tests)
- **Node.js**: 20+ (for web tests)

### Supported Platforms
- **Ubuntu/Debian** (x86_64, ARM64)
- **macOS** (Intel, Apple Silicon)
- **Windows Server** (x86_64)

## Runner Architecture

### Components
```
GitHub Repository
    ↓
GitHub Actions Service
    ↓
Self-Hosted Runner (Your Machine)
    ↓
Docker Engine
    ├── Build API Image (multi-arch)
    ├── Build Web Image (multi-arch)
    └── Run Tests (Python, Node)
```

### Runner Types
1. **Repository Runner**: Dedicated to this repository only (recommended)
2. **Organization Runner**: Shared across multiple repositories
3. **Enterprise Runner**: Shared across entire enterprise

## Installation Methods

### Method 1: Linux/macOS (Recommended)

#### Step 1: Create Runner Directory
```bash
# Create dedicated directory for runner
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download the latest runner package
# For Linux x64
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# For macOS x64
curl -o actions-runner-osx-x64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-osx-x64-2.311.0.tar.gz

# For macOS ARM64 (Apple Silicon)
curl -o actions-runner-osx-arm64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-osx-arm64-2.311.0.tar.gz

# Extract the installer
tar xzf ./actions-runner-*.tar.gz
```

#### Step 2: Get Runner Token
1. Go to repository Settings → Actions → Runners
2. Click "New self-hosted runner"
3. Select your OS and architecture
4. Copy the token from the configuration command

#### Step 3: Configure Runner
```bash
# Configure the runner
./config.sh \
  --url https://github.com/YOUR_ORG/data-profiler \
  --token YOUR_RUNNER_TOKEN \
  --name "data-profiler-runner-1" \
  --labels self-hosted,linux,x64,docker \
  --work _work

# Options:
# --name: Unique name for this runner
# --labels: Tags for targeting specific runners
# --work: Working directory for jobs
# --unattended: Skip interactive prompts
# --replace: Replace existing runner with same name
```

#### Step 4: Install Dependencies
```bash
# Install Python 3.10, 3.11, 3.12
sudo apt-get update
sudo apt-get install -y python3.10 python3.11 python3.12 python3-pip

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Buildx for multi-arch builds
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap

# Log out and back in for docker group to take effect
```

#### Step 5: Run as Service (Recommended)
```bash
# Install as systemd service (Linux)
sudo ./svc.sh install

# Start the service
sudo ./svc.sh start

# Check status
sudo ./svc.sh status

# Enable auto-start on boot
sudo systemctl enable actions.runner.*
```

#### Alternative: Run Interactively (Development)
```bash
# Run in foreground (for testing)
./run.sh

# Run in background
nohup ./run.sh &
```

### Method 2: Docker Container Runner

For isolated runner environments, you can run the runner itself in Docker:

```bash
# Create docker-compose.yml for runner
cat > docker-compose.runner.yml <<'EOF'
services:
  runner:
    image: myoung34/github-runner:latest
    environment:
      REPO_URL: https://github.com/YOUR_ORG/data-profiler
      RUNNER_NAME: docker-runner-1
      RUNNER_TOKEN: YOUR_RUNNER_TOKEN
      RUNNER_WORKDIR: /tmp/runner/work
      RUNNER_SCOPE: repo
      LABELS: self-hosted,linux,x64,docker
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./runner-work:/tmp/runner/work
    restart: unless-stopped
    privileged: true  # Required for Docker-in-Docker
EOF

# Start the runner
docker-compose -f docker-compose.runner.yml up -d

# View logs
docker-compose -f docker-compose.runner.yml logs -f
```

**Note**: Docker-in-Docker has security implications. Only use in trusted environments.

### Method 3: Kubernetes (Advanced)

For running multiple runners at scale:

```yaml
# actions-runner-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-runner
spec:
  replicas: 3
  selector:
    matchLabels:
      app: github-runner
  template:
    metadata:
      labels:
        app: github-runner
    spec:
      containers:
      - name: runner
        image: myoung34/github-runner:latest
        env:
        - name: REPO_URL
          value: "https://github.com/YOUR_ORG/data-profiler"
        - name: RUNNER_TOKEN
          valueFrom:
            secretKeyRef:
              name: runner-token
              key: token
        - name: RUNNER_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: LABELS
          value: "self-hosted,kubernetes,x64,docker"
        volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
      volumes:
      - name: docker-sock
        hostPath:
          path: /var/run/docker.sock
```

## Configuration

### Runner Labels

Labels help target specific runners in workflows. Configure during setup:

```bash
# Default labels
--labels self-hosted,linux,x64

# Add custom labels for capabilities
--labels self-hosted,linux,x64,docker,python,node,multiarch

# For macOS Apple Silicon
--labels self-hosted,macos,arm64,docker,python,node
```

### Workflow Configuration

Update `.github/workflows/ci.yml` to use self-hosted runners:

```yaml
jobs:
  test-api:
    runs-on: self-hosted  # Use any self-hosted runner
    # OR
    runs-on: [self-hosted, linux, x64]  # Target specific runner

  build:
    runs-on: [self-hosted, docker, multiarch]  # Requires docker and multi-arch
```

### Environment Variables

Create `.env` file in runner directory:

```bash
# Runner configuration
RUNNER_ALLOW_RUNASROOT=false
RUNNER_WORK_DIRECTORY=_work

# Docker configuration
DOCKER_HOST=unix:///var/run/docker.sock
BUILDKIT_PROGRESS=plain

# Cache configuration
ACTIONS_CACHE_PATH=/tmp/actions-cache
```

## Docker Support

### Enable BuildKit
```bash
# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Add to ~/.bashrc or ~/.zshrc
echo 'export DOCKER_BUILDKIT=1' >> ~/.bashrc
echo 'export COMPOSE_DOCKER_CLI_BUILD=1' >> ~/.bashrc
```

### Configure Buildx for Multi-Arch
```bash
# Create multi-arch builder
docker buildx create --name multiarch \
  --driver docker-container \
  --use \
  --bootstrap

# Verify platforms
docker buildx inspect --bootstrap

# Should show: linux/amd64, linux/arm64, linux/arm/v7, etc.
```

### Docker Layer Caching

The workflow uses GitHub Actions cache for Docker layers:

```yaml
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha  # Pull cache from GitHub
    cache-to: type=gha,mode=max  # Push cache to GitHub
```

For local cache (faster but larger disk usage):

```yaml
cache-from: type=local,src=/tmp/.buildx-cache
cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max
```

## Multi-Architecture Builds

### Setup QEMU (for non-native architectures)
```bash
# Install QEMU for cross-platform builds
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Verify QEMU is installed
docker buildx inspect --bootstrap
```

### Build for Multiple Platforms
```bash
# Build for amd64 and arm64
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag myapp:latest \
  --push \
  .
```

### Platform-Specific Runners (Recommended)

For best performance, use native runners for each platform:

```yaml
jobs:
  build-amd64:
    runs-on: [self-hosted, linux, x64]
    steps:
      - name: Build amd64 image
        run: docker buildx build --platform linux/amd64 ...

  build-arm64:
    runs-on: [self-hosted, linux, arm64]
    steps:
      - name: Build arm64 image
        run: docker buildx build --platform linux/arm64 ...

  manifest:
    needs: [build-amd64, build-arm64]
    runs-on: ubuntu-latest
    steps:
      - name: Create multi-arch manifest
        run: docker manifest create ...
```

## Security Considerations

### Runner Isolation

**CRITICAL**: Self-hosted runners should NEVER be used for public repositories or untrusted code.

#### Best Practices
1. **Dedicated runners per repository** (or trusted repository group)
2. **Network isolation**: Firewall rules to limit outbound access
3. **No sensitive credentials**: Use GitHub Secrets, not runner environment
4. **Regular updates**: Keep runner software and OS patched
5. **Audit logs**: Monitor runner activity via GitHub UI

### Secrets Management

#### GitHub Secrets (Recommended)
```yaml
steps:
  - name: Login to registry
    uses: docker/login-action@v3
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}  # Injected at runtime
```

#### Environment Variables (Avoid)
```bash
# BAD: Don't store secrets in runner environment
export DOCKER_PASSWORD=secret123

# GOOD: Use GitHub Secrets
```

### Filesystem Permissions

```bash
# Runner should NOT run as root
# Create dedicated user
sudo useradd -m -s /bin/bash github-runner

# Set ownership
sudo chown -R github-runner:github-runner ~/actions-runner

# Run as service under github-runner user
sudo ./svc.sh install github-runner
```

### Docker Socket Security

Allowing access to Docker socket is equivalent to root access. Mitigate with:

1. **Run Docker in rootless mode**:
```bash
# Install Docker rootless
curl -fsSL https://get.docker.com/rootless | sh
export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock
```

2. **Use Docker socket proxy** (e.g., tecnativa/docker-socket-proxy)

3. **Limit Docker capabilities** in workflow:
```yaml
container:
  options: --cap-drop=ALL --cap-add=NET_BIND_SERVICE
```

## Maintenance

### Runner Updates

#### Manual Update
```bash
# Stop runner
sudo ./svc.sh stop

# Download new version
cd ~/actions-runner
curl -o actions-runner-linux-x64-2.312.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.312.0/actions-runner-linux-x64-2.312.0.tar.gz

# Backup old version
tar czf backup-$(date +%Y%m%d).tar.gz bin externals

# Extract new version
tar xzf actions-runner-linux-x64-2.312.0.tar.gz

# Start runner
sudo ./svc.sh start
```

#### Automatic Updates
Enable auto-update in runner configuration:

```bash
# During initial config
./config.sh --url ... --token ... --autoupdate

# Or modify .runner file
{
  "autoUpdate": true,
  "checkUpdateInterval": 86400  # 24 hours
}
```

### Disk Space Management

```bash
# Clean Docker cache regularly
docker system prune -af --volumes

# Limit Docker disk usage
docker system df  # Check usage
docker system prune -a --filter "until=168h"  # Remove images older than 7 days

# Set up cron job
crontab -e
# Add: 0 2 * * 0 docker system prune -af > /dev/null 2>&1
```

### Log Rotation

```bash
# Configure log rotation for runner logs
sudo tee /etc/logrotate.d/github-runner <<EOF
/home/github-runner/actions-runner/_diag/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### Monitoring

#### Check Runner Status
```bash
# Via systemd
sudo systemctl status actions.runner.*

# Via GitHub UI
# Go to Settings → Actions → Runners
# Green = online, Gray = offline

# Via API
curl -H "Authorization: token YOUR_PAT" \
  https://api.github.com/repos/YOUR_ORG/data-profiler/actions/runners
```

#### Monitor Resource Usage
```bash
# Install monitoring tools
sudo apt-get install -y htop iotop nethogs

# Watch resources during build
htop  # CPU and memory
iotop  # Disk I/O
docker stats  # Container resources
```

### Health Checks

Create a monitoring script:

```bash
#!/bin/bash
# check-runner-health.sh

# Check if runner service is running
if ! systemctl is-active --quiet actions.runner.*; then
    echo "ERROR: Runner service is not running"
    sudo systemctl start actions.runner.*
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "WARNING: Disk usage is ${DISK_USAGE}%"
    docker system prune -af --volumes
fi

# Check Docker daemon
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running"
    sudo systemctl restart docker
fi

echo "Runner health check passed"
```

Run via cron:
```bash
# Check every 5 minutes
*/5 * * * * /home/github-runner/check-runner-health.sh >> /var/log/runner-health.log 2>&1
```

## Troubleshooting

### Runner Not Appearing in GitHub UI

**Symptoms**: Runner configured but not visible in Settings → Actions → Runners

**Solutions**:
1. Check runner is running:
   ```bash
   sudo systemctl status actions.runner.*
   ```

2. Check network connectivity:
   ```bash
   curl -I https://api.github.com
   ```

3. Review runner logs:
   ```bash
   tail -f ~/actions-runner/_diag/Runner_*.log
   ```

4. Re-register runner:
   ```bash
   ./config.sh remove --token YOUR_REMOVAL_TOKEN
   ./config.sh --url ... --token NEW_TOKEN
   ```

### Docker Build Failures

**Symptoms**: Docker builds fail with "permission denied" or "socket not found"

**Solutions**:
1. Verify Docker is running:
   ```bash
   docker info
   ```

2. Check socket permissions:
   ```bash
   ls -l /var/run/docker.sock
   # Should be: srw-rw---- 1 root docker
   ```

3. Add runner user to docker group:
   ```bash
   sudo usermod -aG docker github-runner
   # Log out and back in
   ```

4. Test Docker access:
   ```bash
   docker run hello-world
   ```

### Multi-Arch Build Failures

**Symptoms**: Builds fail for non-native architectures (e.g., arm64 on x64 host)

**Solutions**:
1. Verify QEMU is installed:
   ```bash
   docker buildx inspect --bootstrap
   # Should show multiple platforms
   ```

2. Re-install QEMU:
   ```bash
   docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
   ```

3. Recreate buildx builder:
   ```bash
   docker buildx rm multiarch
   docker buildx create --name multiarch --use --bootstrap
   ```

4. Check platform support:
   ```bash
   docker buildx ls
   # multiarch should show linux/amd64, linux/arm64, etc.
   ```

### Out of Disk Space

**Symptoms**: Builds fail with "no space left on device"

**Solutions**:
1. Check disk usage:
   ```bash
   df -h
   docker system df
   ```

2. Clean Docker resources:
   ```bash
   docker system prune -af --volumes
   docker builder prune -af
   ```

3. Clean build cache:
   ```bash
   rm -rf ~/actions-runner/_work/_temp/*
   rm -rf /tmp/.buildx-cache
   ```

4. Increase disk space or add cleanup cron job (see Maintenance section)

### Slow Builds

**Symptoms**: Builds take significantly longer than GitHub-hosted runners

**Solutions**:
1. Enable BuildKit:
   ```bash
   export DOCKER_BUILDKIT=1
   ```

2. Use layer caching (see Docker Support section)

3. Parallelize jobs in workflow:
   ```yaml
   jobs:
     test-api:
       # ...
     test-web:
       # Runs in parallel with test-api
   ```

4. Use faster storage (SSD instead of HDD)

5. Increase runner resources (CPU, RAM)

## Migration from GitHub-Hosted Runners

### Current State Assessment

The project currently has NO GitHub Actions workflows configured. This is an opportunity to start directly with self-hosted runners.

### Migration Steps

#### Step 1: Add Self-Hosted Runner
1. Follow installation instructions above
2. Verify runner appears in GitHub UI
3. Test runner with simple workflow

#### Step 2: Update Workflow Files
```yaml
# Change from:
runs-on: ubuntu-latest

# To:
runs-on: self-hosted

# Or with specific labels:
runs-on: [self-hosted, linux, x64, docker]
```

#### Step 3: Test CI/CD Pipeline
1. Create a test branch
2. Push changes to trigger workflow
3. Monitor runner execution
4. Verify builds complete successfully

#### Step 4: Update Documentation
1. Update README.md with runner requirements
2. Document runner setup for team
3. Add troubleshooting guide

#### Step 5: Production Rollout
1. Merge workflow changes to main branch
2. Monitor first few production builds
3. Set up monitoring and alerting

### Hybrid Approach (Recommended)

Use both GitHub-hosted and self-hosted runners based on job requirements:

```yaml
jobs:
  # Use self-hosted for resource-intensive builds
  build:
    runs-on: [self-hosted, docker, multiarch]

  # Use GitHub-hosted for simple tests
  lint:
    runs-on: ubuntu-latest

  # Use matrix for testing across environments
  test:
    strategy:
      matrix:
        runner: [ubuntu-latest, self-hosted]
    runs-on: ${{ matrix.runner }}
```

**Benefits**:
- Fallback if self-hosted runner is offline
- Test across different environments
- Cost optimization (use GitHub-hosted for quick jobs)

## Advanced Configuration

### Multiple Runners per Machine

Run multiple runners on the same machine for parallel jobs:

```bash
# Create separate directories
mkdir -p ~/runner-1 ~/runner-2 ~/runner-3

# Configure each runner
cd ~/runner-1 && ./config.sh --name runner-1 --labels self-hosted,linux,x64,slot-1
cd ~/runner-2 && ./config.sh --name runner-2 --labels self-hosted,linux,x64,slot-2
cd ~/runner-3 && ./config.sh --name runner-3 --labels self-hosted,linux,x64,slot-3

# Install as separate services
cd ~/runner-1 && sudo ./svc.sh install github-runner
cd ~/runner-2 && sudo ./svc.sh install github-runner
cd ~/runner-3 && sudo ./svc.sh install github-runner
```

### Runner Groups (Enterprise)

Organize runners into groups for better access control:

1. Go to Enterprise → Settings → Actions → Runner groups
2. Create group (e.g., "data-profiler-runners")
3. Add runners to group
4. Configure repository access to group

### Custom Docker Images for Runners

Create a custom runner image with pre-installed tools:

```dockerfile
FROM myoung34/github-runner:latest

# Install Python versions
RUN apt-get update && apt-get install -y \
    python3.10 python3.11 python3.12 \
    python3-pip

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Install Docker Buildx
RUN docker buildx create --name multiarch --use

# Install project-specific tools
RUN pip install bandit safety pip-audit semgrep

# Pre-cache common dependencies
COPY api/requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

COPY web/package.json web/package-lock.json /tmp/web/
RUN cd /tmp/web && npm ci
```

## Conclusion

Self-hosted runners provide powerful capabilities for the VQ8 Data Profiler CI/CD pipeline:

- ✅ Multi-architecture Docker builds (amd64 + arm64)
- ✅ Faster builds with local caching
- ✅ Full control over build environment
- ✅ Cost savings (no GitHub Actions minutes)
- ✅ Support for large file processing

Follow this guide to set up and maintain robust, secure self-hosted runners for your development workflow.

For additional help:
- **GitHub Docs**: https://docs.github.com/en/actions/hosting-your-own-runners
- **Runner Releases**: https://github.com/actions/runner/releases
- **Troubleshooting**: https://docs.github.com/en/actions/hosting-your-own-runners/troubleshooting-self-hosted-runners
