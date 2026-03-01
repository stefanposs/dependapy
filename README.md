# DEPENDAPY

[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/stefanposs/dependapy/qa.yml?branch=main&label=CI)](https://github.com/stefanposs/dependapy/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/dependapy.svg)](https://pypi.org/project/dependapy/)
[![Website](https://img.shields.io/badge/website-stefanposs.com-blue)](https://stefanposs.com)

> **v0.2.0** — Rewritten with a clean Onion Architecture for extensibility and testability.

## Features

- 🔍 **Scan & Analyze**: Recursively scans repositories for `pyproject.toml` files and identifies outdated dependencies
- 🔄 **Python Version Check**: Ensures compatibility with the three latest Python 3 minor versions via endoflife.date
- 🔀 **Smart PR Handling**: Creates new pull requests or generates offline Git patches
- 🛠️ **uv Compatible**: Works seamlessly with the modern `uv` package manager from astral.sh
- 🤖 **GitHub Action**: Runs automatically on a schedule via GitHub Actions
- 🏗️ **Onion Architecture**: Clean domain model — no GitHub-specific logic inside the core
- 🧪 **Result Pattern**: Explicit `Ok[T] | Err[E]` error handling throughout (no exceptions for control flow)

## Architecture

dependapy v0.2.0 is built on a strict **Onion Architecture** with four layers:

```
┌──────────────────────────────────────────────┐
│             Presentation (CLI)               │
├──────────────────────────────────────────────┤
│          Application (Use Cases)             │
├──────────────────────────────────────────────┤
│  Infrastructure (PyPI, GitHub, Filesystem)   │
├──────────────────────────────────────────────┤
│          Domain (Entities, Ports)            │
└──────────────────────────────────────────────┘
```

The **Domain layer** defines the core business logic and abstract `Protocol` interfaces (Ports).  
Infrastructure adapters implement those protocols — the domain never imports from infrastructure.

### Key Concepts

| Concept | Description |
|---|---|
| `Result[T, E]` | `Ok(value)` or `Err(error)` — replaces sentinel values and bare exceptions |
| `Version` | Wraps `packaging.version.Version`, immutable value object |
| `PackageRegistry` | Port (Protocol) for fetching latest package versions |
| `ProjectRepository` | Port for loading/saving `pyproject.toml` files |
| `VCSPort` | Port for branch, commit, push, PR operations |
| `PyPIAdapter` | Implements `PackageRegistry` with caching and parallel batch queries |
| `FileSystemProjectRepository` | Implements `ProjectRepository` for pyproject.toml |
| `GitHubVCSAdapter` | Implements `VCSPort` via PyGithub |
| `OfflinePatchAdapter` | Implements `VCSPort` via `git format-patch` |
| `Application` | Frozen dataclass — composition root wired in `bootstrap.py` |

## Installation

### From PyPI (recommended)

```bash
# With uv
uv add dependapy
```

```bash
# With pip
pip install dependapy
```

### From Source (for development)

```bash
git clone https://github.com/stefanposs/dependapy.git
cd dependapy

# Install in development mode with uv
uv sync --group dev
```

## Configuration

dependapy reads configuration from environment variables (prefix `DEPENDAPY_`) or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `DEPENDAPY_VCS_TOKEN` | — | GitHub / GitLab token |
| `DEPENDAPY_VCS_PROVIDER` | `offline` | `github` or `offline` |
| `DEPENDAPY_VCS_BASE_BRANCH` | `main` | Target branch for PRs |
| `DEPENDAPY_BRANCH_PREFIX` | `dependapy/` | Prefix for update branches |
| `DEPENDAPY_API_TIMEOUT` | `10` | HTTP timeout in seconds |
| `DEPENDAPY_LOG_LEVEL` | `INFO` | Logging level |
| `DEPENDAPY_PYPI_BASE_URL` | `https://pypi.org/pypi/{package_name}/json` | PyPI API base URL |
| `DEPENDAPY_PYTHON_EOL_API_URL` | `https://endoflife.date/api/python.json` | Python EOL API |
| `DEPENDAPY_NUM_LATEST_PYTHON_VERSIONS` | `3` | Number of latest Python versions to check |

## Usage

### Running Locally

```bash
# Set your GitHub token
export DEPENDAPY_VCS_TOKEN=your_github_token

# Run dependapy (analyzes current directory, creates PR)
dependapy

# Dry run — no changes made
dependapy --dry-run

# Skip PR creation, only update files locally
dependapy --no-pr

# Use offline patch instead of GitHub API
dependapy --provider offline --patch-output updates.patch
```

### Command Line Options

```
usage: dependapy [-h] [--repo-path PATH] [--token TOKEN] [--provider {github,offline}]
                 [--base-branch BRANCH] [--no-pr] [--offline-pr] [--patch-output PATH]
                 [--dry-run] [--log-level LEVEL]

Analyze and update Python dependencies

options:
  -h, --help              show this help message and exit
  --repo-path PATH        Path to the repository to scan (default: current directory)
  --token TOKEN           VCS token (or set DEPENDAPY_VCS_TOKEN)
  --provider {github,offline}
                          VCS provider to use (default: offline)
  --base-branch BRANCH    Target branch for PRs (default: main)
  --no-pr                 Update files locally without creating a PR
  --offline-pr            Create a Git patch instead of using GitHub API (legacy alias)
  --patch-output PATH     Patch file path when using --provider offline
  --dry-run               Report changes without making them
  --log-level LEVEL       Logging level (default: INFO)
```

### Offline PR Mode

For environments without GitHub API access:

```bash
dependapy --provider offline --patch-output my-updates.patch

# Apply later on a machine with GitHub access
git apply my-updates.patch
git checkout -b dependapy/updates
git commit -am "Apply dependapy updates"
git push origin dependapy/updates
# Then create a PR via the GitHub UI
```

## Setting Up as a GitHub Action

```yaml
name: Dependapy

on:
  schedule:
    - cron: '0 2 * * 0'  # Every Sunday at 02:00 UTC
  workflow_dispatch:

jobs:
  update-dependencies:
    name: Update Dependencies
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependapy
        run: pip install dependapy

      - name: Run dependapy
        env:
          DEPENDAPY_VCS_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: dependapy
```

## Migration from v0.1.x

The CLI interface is fully backward-compatible. The old `--offline-pr` flag maps to `--provider offline`.

The internal Python API has changed. Legacy modules (`analyzer`, `updater`, `github_api`, `offline_pr`) 
are still importable but will be removed in v0.3.0. Please migrate to the new API:

```python
# Old (v0.1.x)
from dependapy.analyzer import analyze_project
from dependapy.github_api import create_pull_request

# New (v0.2.x)
from dependapy.bootstrap import bootstrap
from dependapy.application.config import AppConfig

app = bootstrap(AppConfig.from_env())
result = app.analyze.execute(Path("."))
```

## How It Works

1. **Repository Scanning**: Finds all `pyproject.toml` files recursively
2. **Dependency Analysis**: 
   - Reads `[project]`, `[project.optional-dependencies]`, and `[dependency-groups]` sections
   - Checks PyPI for latest versions (parallel batch queries with caching)
   - Checks endoflife.date for current Python version support
3. **Update Planning**: Generates `UpdatePlan` respecting patch/minor/major limits
4. **File Updates**: Applies version bumps in-place using regex (preserves file formatting)
5. **PR Submission**: Creates branch → commit → push → PR via configured VCS provider

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/

# Run linter
uv run ruff check .
uv run ruff format --check .

# Check import layer contracts
uv run lint-imports

# Type checking
pyright dependapy/

# Full CI pipeline
just ci
```
