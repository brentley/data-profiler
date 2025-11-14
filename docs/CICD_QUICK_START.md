# CI/CD Quick Start Guide

## Overview

Quick reference for setting up and using the CI/CD pipeline for VQ8 Data Profiler.

## Pipeline Overview

The CI/CD pipeline includes:
- **Test**: Python (3.10, 3.11, 3.12) and Node.js tests
- **Security**: Bandit, Safety, Semgrep, Trivy scans
- **Build**: Multi-arch Docker images (amd64 + arm64)
- **Deploy**: Automatic via Watchtower (when configured)

## Quickest Path: GitHub-Hosted Runners

If you just want to get started quickly without managing infrastructure:

### 1. Use Default Configuration
The workflows in `.github/workflows/ci.yml` are already configured to work with GitHub-hosted runners by default.

### 2. Enable GitHub Actions
```bash
# No setup required! Just push code:
git add .
git commit -m "feat: add new feature"
git push origin main
```

### 3. View Results
- Go to repository → Actions tab
- Click on your workflow run
- View test results and build logs

**Cost**: Free for public repositories, uses GitHub Actions minutes for private repos.

## Best Path: Self-Hosted Runners

For better performance, cost savings, and multi-arch builds:

### 1. Install Runner (5 minutes)

**Linux/macOS**:
```bash
# Create directory
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download runner (check latest version at https://github.com/actions/runner/releases)
# For Linux x64:
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# For macOS ARM64 (Apple Silicon):
curl -o actions-runner-osx-arm64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-osx-arm64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-*.tar.gz
```

### 2. Get Registration Token

1. Go to: `https://github.com/YOUR_ORG/data-profiler/settings/actions/runners/new`
2. Copy the token from the configuration command shown

### 3. Configure Runner

```bash
./config.sh \
  --url https://github.com/YOUR_ORG/data-profiler \
  --token YOUR_TOKEN_HERE \
  --name "my-runner" \
  --labels self-hosted,linux,x64,docker \
  --unattended
```

### 4. Install Dependencies

```bash
# Python (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y python3.10 python3.11 python3.12 python3-pip

# Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Docker (if not installed)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Docker Buildx for multi-arch
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap
```

### 5. Start Runner

```bash
# Install as service (recommended)
sudo ./svc.sh install
sudo ./svc.sh start

# OR run in foreground (for testing)
./run.sh
```

### 6. Update Workflow

Edit `.github/workflows/ci.yml`:

```yaml
jobs:
  test-api:
    runs-on: self-hosted  # Change from ubuntu-latest
```

### 7. Test It

```bash
# Push a change to trigger the workflow
git commit --allow-empty -m "test: trigger CI"
git push
```

## Configuration Matrix

| Runner Type | Setup Time | Cost | Performance | Multi-Arch | Maintenance |
|-------------|------------|------|-------------|------------|-------------|
| **GitHub-Hosted** | 0 min | Minutes used | Standard | Emulated only | None |
| **Self-Hosted (Linux)** | 5-10 min | Free | Fast | Native | Low |
| **Self-Hosted (macOS)** | 5-10 min | Free | Fast | Native ARM64 | Low |
| **Docker Container** | 2 min | Free | Fast | Via QEMU | Medium |
| **Kubernetes** | 30+ min | Free | Very Fast | Native | High |

## Workflow Customization

### Run Specific Jobs Only

```yaml
# In .github/workflows/ci.yml
on:
  push:
    branches: [main]
    paths:
      - 'api/**'  # Only run on API changes
```

### Skip CI for Commits

```bash
git commit -m "docs: update README [skip ci]"
```

### Run Workflows Manually

1. Go to Actions tab
2. Select workflow
3. Click "Run workflow"
4. Choose branch and parameters

## Secrets Configuration

### Required Secrets

| Secret | Purpose | Required For |
|--------|---------|--------------|
| `GITHUB_TOKEN` | Auto-provided | Image push to GHCR |
| `CODECOV_TOKEN` | Coverage upload | Test coverage (optional) |

### Add Secrets

1. Go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add name and value
4. Click "Add secret"

## Common Tasks

### Run Tests Locally (Before Pushing)

```bash
# API tests
cd api
pytest -v

# Web build
cd web
npm run build
```

### Debug Failed Build

```bash
# View workflow logs in GitHub UI
# OR re-run locally:

# Pull the exact Docker image used
docker pull ghcr.io/YOUR_ORG/data-profiler/api:sha-abc123

# Run tests in container
docker run --rm -it ghcr.io/YOUR_ORG/data-profiler/api:sha-abc123 \
  pytest -v
```

### Update Python/Node Versions

Edit `.github/workflows/ci.yml`:

```yaml
env:
  PYTHON_VERSION: '3.12'  # Update here
  NODE_VERSION: '20'      # Update here

strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']  # And here
```

### Skip Security Scans (Not Recommended)

```yaml
jobs:
  security:
    if: false  # Temporarily disable
```

## Monitoring

### Check Runner Status

**Via GitHub UI**:
1. Settings → Actions → Runners
2. Green dot = online, Gray = offline

**Via CLI**:
```bash
# Check service status
sudo systemctl status actions.runner.*

# View runner logs
tail -f ~/actions-runner/_diag/Runner_*.log
```

### View Build History

1. Actions tab → Workflows
2. Click on workflow name
3. View run history and trends

### Set Up Notifications

1. Watch repository (top right)
2. Custom → Workflows
3. Choose notification method (email, Slack, etc.)

## Troubleshooting

### Build Fails on Self-Hosted Runner

**Check runner logs**:
```bash
tail -f ~/actions-runner/_diag/Runner_*.log
```

**Check Docker**:
```bash
docker info
docker ps
```

**Restart runner**:
```bash
sudo ./svc.sh restart
```

### Out of Disk Space

```bash
# Clean Docker cache
docker system prune -af --volumes

# Check disk usage
df -h
docker system df
```

### Multi-Arch Build Fails

```bash
# Re-install QEMU
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Recreate buildx builder
docker buildx rm multiarch
docker buildx create --name multiarch --use --bootstrap
```

### Security Scan False Positives

Edit `.github/workflows/ci.yml`:

```yaml
- name: Run Bandit
  run: bandit -r . --skip B101,B601  # Skip specific checks
```

## Performance Tips

### Speed Up Builds

1. **Enable BuildKit**:
```bash
export DOCKER_BUILDKIT=1
echo 'export DOCKER_BUILDKIT=1' >> ~/.bashrc
```

2. **Use layer caching** (already configured in workflow)

3. **Parallelize tests**:
```yaml
strategy:
  matrix:
    test-suite: [unit, integration, e2e]
```

4. **Cache dependencies**:
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

### Reduce Redundant Runs

**Run only on specific paths**:
```yaml
on:
  push:
    paths:
      - 'api/**'
      - 'web/**'
      - '.github/workflows/**'
```

**Concurrency limits** (cancel old runs):
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

## Migration Checklist

Moving from GitHub-hosted to self-hosted runners:

- [ ] Install runner on machine
- [ ] Install Python 3.10, 3.11, 3.12
- [ ] Install Node.js 20
- [ ] Install Docker with Buildx
- [ ] Configure QEMU for multi-arch
- [ ] Test runner with hello-world workflow
- [ ] Update workflow files (`runs-on: self-hosted`)
- [ ] Test full CI/CD pipeline
- [ ] Set up monitoring and health checks
- [ ] Configure disk cleanup cron job
- [ ] Document runner setup for team
- [ ] Add runner to disaster recovery plan

## Support Resources

- **Detailed Setup**: [GITHUB_RUNNER_SETUP.md](./GITHUB_RUNNER_SETUP.md)
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Runner Releases**: https://github.com/actions/runner/releases
- **Docker Buildx**: https://docs.docker.com/buildx/working-with-buildx/
- **Troubleshooting**: https://docs.github.com/en/actions/hosting-your-own-runners/troubleshooting-self-hosted-runners

## Next Steps

1. Choose runner type (GitHub-hosted vs self-hosted)
2. Follow setup instructions above
3. Test with a simple commit
4. Monitor first few builds
5. Optimize based on performance metrics

For production deployments, see:
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Full deployment guide
- [DEVOPS_SUMMARY.md](../DEVOPS_SUMMARY.md) - DevOps infrastructure overview
