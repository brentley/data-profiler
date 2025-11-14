# CI/CD Architecture Diagram

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GitHub Repository                                  │
│                         data-profiler (main/develop)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │   Git Push / Pull Request         │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GitHub Actions Workflow Trigger                        │
│                           (.github/workflows/ci.yml)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
    ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
    │   Test: API     │   │   Test: Web     │   │   Security      │
    │   (Parallel)    │   │   (Parallel)    │   │   (Parallel)    │
    └─────────────────┘   └─────────────────┘   └─────────────────┘
              │                       │                       │
              │                       │                       │
    ┌─────────▼─────────┐   ┌────────▼────────┐ ┌──────────▼──────────┐
    │ Python 3.10       │   │ npm install     │ │ Bandit              │
    │ Python 3.11       │   │ npm run build   │ │ Safety              │
    │ Python 3.12       │   │ npm run lint    │ │ pip-audit           │
    │                   │   │                 │ │ Semgrep             │
    │ pytest (unit)     │   │ Vite build      │ │ Trivy               │
    │ pytest (integ)    │   │ validation      │ │                     │
    │ Coverage upload   │   │                 │ │ SARIF → GitHub      │
    └───────────────────┘   └─────────────────┘ └─────────────────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │
                          ┌───────────▼───────────┐
                          │   All Tests Passed?   │
                          └───────────┬───────────┘
                                      │ Yes (on push only)
                                      ▼
                          ┌───────────────────────┐
                          │   Build: Docker       │
                          │   Multi-Architecture  │
                          └───────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
        ┌───────────────────────┐         ┌───────────────────────┐
        │  Build API Image      │         │  Build Web Image      │
        │  - linux/amd64        │         │  - linux/amd64        │
        │  - linux/arm64        │         │  - linux/arm64        │
        │                       │         │                       │
        │  Docker Buildx        │         │  Docker Buildx        │
        │  BuildKit Caching     │         │  BuildKit Caching     │
        │  Metadata Injection   │         │  Metadata Injection   │
        └───────────────────────┘         └───────────────────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
                          ┌───────────────────────┐
                          │  Push to GHCR         │
                          │  ghcr.io/ORG/...      │
                          │                       │
                          │  Tags:                │
                          │  - branch name        │
                          │  - sha-COMMIT         │
                          │  - latest (main only) │
                          └───────────────────────┘
                                      │
                                      ▼
                          ┌───────────────────────┐
                          │  Image Available for  │
                          │  Deployment           │
                          │  (Manual or Auto)     │
                          └───────────────────────┘
```

## Runner Architecture

### Option A: GitHub-Hosted Runners (Default)

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Infrastructure                         │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │  Runner 1  │  │  Runner 2  │  │  Runner 3  │  ...          │
│  │  (Ubuntu)  │  │  (Ubuntu)  │  │  (Ubuntu)  │               │
│  │            │  │            │  │            │               │
│  │  2 CPU     │  │  2 CPU     │  │  2 CPU     │               │
│  │  7 GB RAM  │  │  7 GB RAM  │  │  7 GB RAM  │               │
│  │  14 GB SSD │  │  14 GB SSD │  │  14 GB SSD │               │
│  └────────────┘  └────────────┘  └────────────┘               │
│                                                                  │
│  Automatically assigned based on availability                    │
│  Fresh VM for each job                                          │
│  Auto-scaling, no queue management needed                       │
└─────────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- ✅ Zero setup, managed by GitHub
- ✅ Automatic scaling
- ⚠️ Limited resources (2 CPU, 7 GB RAM)
- ⚠️ Costs minutes for private repos
- ⚠️ Slower multi-arch builds (QEMU emulation)

### Option B: Self-Hosted Runners

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Infrastructure                           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Runner 1 (Linux x64)                                  │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  GitHub Actions Runner Service                   │  │    │
│  │  │  - Polls GitHub for jobs                         │  │    │
│  │  │  - Executes workflow steps                       │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Docker Engine                                   │  │    │
│  │  │  - BuildKit enabled                              │  │    │
│  │  │  - Buildx multi-arch support                     │  │    │
│  │  │  - Persistent layer cache                        │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Dependencies Pre-installed                      │  │    │
│  │  │  - Python 3.10, 3.11, 3.12                       │  │    │
│  │  │  - Node.js 20                                    │  │    │
│  │  │  - Security tools (bandit, safety, etc.)         │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  │  Resources: 4-8 CPU, 8-16 GB RAM, 100+ GB SSD          │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Optional: Runner 2 (macOS ARM64) for native ARM builds         │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Apple Silicon Mac (M1/M2/M3)                          │    │
│  │  - Native ARM64 builds (5-10x faster than QEMU)        │    │
│  │  - Docker Desktop with Rosetta 2                       │    │
│  │  - Can also build x64 via Rosetta                      │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- ✅ Better performance (4-8 CPU, 8-16 GB RAM)
- ✅ Persistent cache (faster subsequent builds)
- ✅ Full control over environment
- ✅ Free GitHub Actions minutes
- ⚠️ Requires setup and maintenance
- ⚠️ Your responsibility for uptime/security

### Hybrid Approach (Recommended for Production)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Workflow Job Distribution                   │
│                                                                  │
│  Simple Jobs          │  Heavy Jobs                              │
│  (GitHub-Hosted)      │  (Self-Hosted)                          │
│  ─────────────────────┼─────────────────────────────────────    │
│                       │                                          │
│  • Linting            │  • Docker builds (multi-arch)           │
│  • Security scans     │  • Integration tests                    │
│  • Simple tests       │  • Large file processing                │
│  • PR validation      │  • Performance tests                    │
│                       │                                          │
│  Benefits:            │  Benefits:                               │
│  - Free/cheap         │  - Fast (native builds)                 │
│  - No maintenance     │  - Persistent cache                     │
│  - Always available   │  - Custom environment                   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Push to Deploy

```
Developer                GitHub                  CI/CD                 Registry
    │                       │                       │                      │
    │  git push             │                       │                      │
    ├──────────────────────►│                       │                      │
    │                       │  Trigger workflow     │                      │
    │                       ├──────────────────────►│                      │
    │                       │                       │                      │
    │                       │                       │ Run tests            │
    │                       │                       ├──────────┐           │
    │                       │                       │          │           │
    │                       │                       │◄─────────┘           │
    │                       │                       │ Tests passed         │
    │                       │                       │                      │
    │                       │                       │ Build images         │
    │                       │                       ├──────────┐           │
    │                       │                       │          │           │
    │                       │                       │◄─────────┘           │
    │                       │                       │ Images built         │
    │                       │                       │                      │
    │                       │                       │ Push to GHCR         │
    │                       │                       ├─────────────────────►│
    │                       │                       │                      │
    │                       │  Workflow complete    │                      │
    │                       │◄──────────────────────┤                      │
    │  Notification         │                       │                      │
    │◄──────────────────────┤                       │                      │
    │                       │                       │                      │
    │                       │                       │                      │
    │  (Optional: Watchtower auto-deploy)          │                      │
    │                       │                       │                      │
    │                       │                       │  Pull new image      │
    │                       │                       │◄─────────────────────┤
    │                       │                       │                      │
    │                       │                       │ Deploy containers    │
    │                       │                       ├──────────┐           │
    │                       │                       │          │           │
    │                       │                       │◄─────────┘           │
    │                       │                       │                      │
    ▼                       ▼                       ▼                      ▼
```

## Security Scanning Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Security Scan Pipeline                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │  Source Code Ready    │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│    Bandit     │     │    Safety     │     │  pip-audit    │
│  (Python AST  │     │ (Dependencies)│     │ (PyPI vulns)  │
│   Security)   │     │               │     │               │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌───────────────┐
                    │   Semgrep     │
                    │ (Code patterns)│
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │     Trivy     │
                    │  (Container   │
                    │ Vulnerabilities)│
                    └───────┬───────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  Generate SARIF       │
                │  (Standard format)    │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  Upload to GitHub     │
                │  Security Tab         │
                └───────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  Viewable in UI       │
                │  - Code scanning      │
                │  - Alerts             │
                │  - Remediation        │
                └───────────────────────┘
```

## Docker Multi-Architecture Build Process

```
┌─────────────────────────────────────────────────────────────────┐
│                     Multi-Arch Build Process                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Docker Buildx       │
                    │   (Builder instance)  │
                    └───────────┬───────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌───────────────────┐         ┌───────────────────┐
    │  Build for amd64  │         │  Build for arm64  │
    │                   │         │                   │
    │  Native (x64)     │         │  QEMU Emulation   │
    │  or               │         │  or               │
    │  QEMU (on ARM)    │         │  Native (ARM)     │
    └─────────┬─────────┘         └─────────┬─────────┘
              │                             │
              │   Layer Cache (from GHA)    │
              ├─────────────────────────────┤
              │                             │
              ▼                             ▼
    ┌───────────────────┐         ┌───────────────────┐
    │  API Image        │         │  API Image        │
    │  linux/amd64      │         │  linux/arm64      │
    │  tag: sha-xxx     │         │  tag: sha-xxx     │
    └─────────┬─────────┘         └─────────┬─────────┘
              │                             │
              └─────────────┬───────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  Create Manifest      │
                │  (Multi-arch index)   │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  Push to GHCR         │
                │  ghcr.io/org/app:tag  │
                │                       │
                │  Platforms:           │
                │  - linux/amd64        │
                │  - linux/arm64        │
                └───────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  Docker Pull          │
                │  Auto-selects         │
                │  correct arch         │
                └───────────────────────┘
```

**Performance Comparison:**

| Build Method | amd64 | arm64 | Total |
|--------------|-------|-------|-------|
| **GitHub-Hosted (x64)** | 5 min (native) | 20 min (QEMU) | 25 min |
| **Self-Hosted (x64)** | 2 min (native) | 12 min (QEMU) | 14 min |
| **Self-Hosted (ARM64)** | 5 min (QEMU) | 2 min (native) | 7 min |
| **Hybrid (x64 + ARM64)** | 2 min (native) | 2 min (native) | 4 min |

## File and Directory Structure

```
data-profiler/
│
├── .github/
│   ├── workflows/
│   │   └── ci.yml                    # Main CI/CD pipeline (251 lines)
│   └── README.md                      # Workflow documentation
│
├── docs/
│   ├── GITHUB_RUNNER_SETUP.md        # Detailed setup (869 lines)
│   ├── CICD_QUICK_START.md           # Quick reference (389 lines)
│   ├── RUNNER_COMPARISON.md          # Analysis (489 lines)
│   ├── CICD_IMPLEMENTATION_SUMMARY.md # This summary (550+ lines)
│   └── CICD_ARCHITECTURE.md          # Architecture diagrams (this file)
│
├── api/
│   ├── Dockerfile.api                # Multi-stage Python build
│   ├── requirements.txt              # Runtime dependencies
│   ├── requirements-dev.txt          # Development tools
│   ├── requirements-test.txt         # Testing tools
│   └── tests/                        # Test suite
│
├── web/
│   ├── Dockerfile.web                # Multi-stage Node build
│   ├── package.json                  # Dependencies
│   └── src/                          # Source code
│
├── docker-compose.yml                # Production deployment
├── docker-compose.dev.yml            # Development with hot-reload
├── Makefile                          # Build automation
└── DEPLOYMENT.md                     # Deployment guide (with CI/CD section)
```

## Workflow Execution Timeline

```
Time    GitHub-Hosted Runner          Self-Hosted Runner (warm cache)
────────────────────────────────────────────────────────────────────
0:00    ├─ Checkout code              ├─ Checkout code
0:30    ├─ Setup Python 3.10          ├─ Setup Python 3.10 (cached)
1:00    ├─ Install dependencies       ├─ Install dependencies (cached)
2:00    ├─ Run unit tests             ├─ Run unit tests
        │  (Parallel with 3.11, 3.12) │  (Parallel with 3.11, 3.12)
4:00    ├─ Run integration tests      ├─ Run integration tests
6:00    ├─ Upload coverage            ├─ Upload coverage
        │                             │
        ├─ Setup Node.js              ├─ Setup Node.js (cached)
7:00    ├─ npm install                ├─ npm install (cached)
9:00    ├─ npm run build              ├─ npm run build
        │                             │
        ├─ Security scans             ├─ Security scans
12:00   ├─ Bandit, Safety, etc.       ├─ Bandit, Safety, etc.
        │                             │
        ├─ Docker build (amd64)       ├─ Docker build (amd64, cached)
17:00   ├─ Docker build (arm64, QEMU) ├─ Docker build (arm64, QEMU)
        │  ⚠️ SLOW                    │  (or native on ARM runner)
        │                             │
30:00   └─ Complete ✓                 └─ Complete ✓ (at ~12 minutes)
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Integrations                         │
└─────────────────────────────────────────────────────────────────┘

GitHub Container Registry (GHCR)
    │
    ├─ Image Storage
    │  └─ ghcr.io/ORG/data-profiler/api:latest
    │     ghcr.io/ORG/data-profiler/web:latest
    │
    └─ Authentication
       └─ GITHUB_TOKEN (automatic)

Codecov (Optional)
    │
    └─ Coverage Reports
       ├─ API Coverage (Python)
       ├─ Coverage Trends
       └─ PR Comments

GitHub Security
    │
    ├─ Code Scanning
    │  ├─ SARIF uploads from Trivy
    │  ├─ Vulnerability alerts
    │  └─ Dependency graph
    │
    └─ Dependabot
       └─ Automated dependency updates

Docker Hub (Optional)
    │
    └─ Public images (if needed)
       └─ ORG/data-profiler:latest
```

## Decision Tree: Which Runner to Use?

```
                        Start
                          │
                          ▼
                   Is this a public
                    repository?
                    ┌────┴────┐
                  Yes        No
                   │          │
                   ▼          ▼
            GitHub-Hosted  How many builds/day?
                 (FREE)      ┌────┴────┐
                           <25       >25
                            │          │
                            ▼          ▼
                     GitHub-Hosted  Self-Hosted
                      ($50/mo)     (Cost effective)
                                        │
                                        ▼
                                 Need multi-arch
                                   native speed?
                                   ┌────┴────┐
                                 Yes        No
                                  │          │
                                  ▼          ▼
                            2 Runners    1 Runner
                            (x64+ARM)     (x64)
                              (4 min)    (14 min)
```

## Summary

This architecture provides:

✅ **Flexible Runner Options**: GitHub-hosted, self-hosted, or hybrid
✅ **Comprehensive Testing**: Unit, integration, and security scans
✅ **Multi-Arch Support**: Native amd64 and arm64 builds
✅ **Efficient Caching**: Docker layers, dependencies, build artifacts
✅ **Security First**: Multiple scanning tools with SARIF integration
✅ **Production Ready**: Follows best practices and VisiQuate standards

**Total Documentation**: ~2,000 lines of workflows and ~2,500 lines of guides

---

**Document Version**: 1.0.0
**Last Updated**: 2024-11-13
