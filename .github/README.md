# GitHub Actions Configuration

This directory contains CI/CD workflows for the VQ8 Data Profiler project.

## Workflows

### ci.yml - Main CI/CD Pipeline

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` branch

**Jobs**:

#### 1. test-api
- Runs on Python 3.10, 3.11, 3.12
- Executes unit and integration tests
- Uploads coverage to Codecov
- Supports both GitHub-hosted and self-hosted runners

#### 2. test-web
- Builds React/Vite web application
- Runs linting (non-blocking)
- Verifies production build succeeds

#### 3. security
- Bandit (Python security analysis)
- Safety (dependency vulnerability scanning)
- pip-audit (PyPI package auditing)
- Semgrep (static analysis)
- Trivy (container vulnerability scanning)
- Uploads results to GitHub Security

#### 4. build
- Builds multi-architecture Docker images (amd64 + arm64)
- Pushes to GitHub Container Registry (GHCR)
- Tags: branch name, SHA, latest (for default branch)
- Uses BuildKit caching for faster builds

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REGISTRY` | `ghcr.io` | Container registry |
| `PYTHON_VERSION` | `3.11` | Primary Python version |
| `NODE_VERSION` | `20` | Node.js version |

### Secrets Required

| Secret | Purpose | Required |
|--------|---------|----------|
| `GITHUB_TOKEN` | Auto-provided for GHCR push | Yes |
| `CODECOV_TOKEN` | Upload coverage reports | Optional |

### Runner Configuration

**Default**: GitHub-hosted runners (`ubuntu-latest`)

**Self-hosted**: Update `runs-on` in workflow:
```yaml
runs-on: [self-hosted, linux, x64, docker]
```

See [docs/GITHUB_RUNNER_SETUP.md](../docs/GITHUB_RUNNER_SETUP.md) for setup instructions.

## Usage

### Automatic Triggers

Workflows run automatically on:
```bash
# Push to main/develop
git push origin main

# Create pull request
gh pr create
```

### Manual Triggers

```bash
# Via GitHub UI
# Go to Actions → Select workflow → Run workflow

# Via GitHub CLI
gh workflow run ci.yml
```

### Skip CI

```bash
git commit -m "docs: update README [skip ci]"
```

## Workflow Customization

### Run Only on Specific Paths

```yaml
on:
  push:
    paths:
      - 'api/**'
      - 'web/**'
      - '.github/workflows/**'
```

### Add New Test Matrix

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12', '3.13']  # Add new version
```

### Disable Specific Jobs

```yaml
jobs:
  security:
    if: github.event_name == 'push'  # Only on push, not PRs
```

## Monitoring

### View Workflow Runs
1. Repository → Actions tab
2. Click workflow name
3. View run details, logs, and artifacts

### Runner Status
1. Settings → Actions → Runners
2. View online/offline status
3. Monitor queue and active jobs

### Notifications
1. Watch repository
2. Custom → Workflows
3. Configure email/Slack notifications

## Troubleshooting

### Build Failures

**Check logs**:
1. Actions → Failed workflow
2. Click on failed job
3. Expand failed step

**Debug locally**:
```bash
# Run tests locally
cd api && pytest -v

# Build Docker image locally
docker build -f Dockerfile.api -t test .
```

### Security Scan False Positives

Edit workflow to skip specific checks:
```yaml
- name: Run Bandit
  run: bandit -r . --skip B101  # Skip assert_used check
```

### Multi-Arch Build Issues

Ensure runner has:
- Docker Buildx installed
- QEMU configured for cross-platform builds
- Sufficient disk space (100GB+)

See troubleshooting section in [GITHUB_RUNNER_SETUP.md](../docs/GITHUB_RUNNER_SETUP.md)

## Performance Optimization

### Current Optimizations
- ✅ Docker layer caching (GitHub Actions cache)
- ✅ Python/Node dependency caching
- ✅ Multi-stage Docker builds
- ✅ Parallel test execution
- ✅ BuildKit for faster builds

### Additional Optimizations

**Concurrency limits** (cancel old runs):
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

**Cache pip/npm globally**:
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      ~/.npm
    key: ${{ runner.os }}-deps-${{ hashFiles('**/requirements.txt', '**/package-lock.json') }}
```

## Security Considerations

### Self-Hosted Runners
- ⚠️ Never use for public repositories or untrusted code
- ✅ Use dedicated runners per repository
- ✅ Network isolation and firewall rules
- ✅ Regular OS and runner updates
- ✅ Monitor runner activity logs

### Secrets Management
- ✅ Use GitHub Secrets (never environment variables)
- ✅ Minimum required permissions for GITHUB_TOKEN
- ✅ Rotate tokens regularly
- ✅ Audit secret usage in workflow runs

### Image Security
- ✅ Trivy scans on every build
- ✅ Multi-stage builds (minimal attack surface)
- ✅ Non-root users in containers
- ✅ Signed commits (recommended)

## Maintenance

### Updating Actions

Check for updates regularly:
```yaml
# Update from v3 to v4
- uses: actions/checkout@v3  # Old
- uses: actions/checkout@v4  # New
```

Monitor Dependabot PRs for action updates.

### Updating Runner Software

Self-hosted runners auto-update by default. To update manually:
```bash
cd ~/actions-runner
./config.sh remove
# Download new version
./config.sh --url ... --token ...
```

### Workflow Deprecation Warnings

View warnings in Actions → Workflow run → Annotations

Common warnings:
- Deprecated Node.js versions
- Outdated action versions
- Deprecated workflow commands

## Best Practices

### Workflow Design
- ✅ Fail fast (run cheap jobs first)
- ✅ Parallel execution where possible
- ✅ Clear job and step names
- ✅ Comprehensive error messages
- ✅ Artifacts for debugging

### Testing
- ✅ Test locally before pushing
- ✅ Use matrix for multiple versions
- ✅ Integration tests in separate job
- ✅ Upload test artifacts on failure

### Docker
- ✅ Multi-stage builds
- ✅ Layer caching
- ✅ Multi-arch support
- ✅ Minimal base images
- ✅ Health checks

### Security
- ✅ Run security scans on every PR
- ✅ Upload SARIF to GitHub Security
- ✅ Non-blocking for minor issues
- ✅ Regular dependency updates

## Quick Links

- **Workflow Syntax**: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- **Self-Hosted Runners**: [../docs/GITHUB_RUNNER_SETUP.md](../docs/GITHUB_RUNNER_SETUP.md)
- **Quick Start**: [../docs/CICD_QUICK_START.md](../docs/CICD_QUICK_START.md)
- **Deployment Guide**: [../DEPLOYMENT.md](../DEPLOYMENT.md)

## Support

For issues or questions:
1. Check documentation in `/docs` directory
2. Review GitHub Actions logs
3. Check runner status and logs
4. Create issue with workflow run link

---

**Last Updated**: 2024-11-13
**Workflow Version**: 1.0.0
