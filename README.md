# DEPENDAPY

[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/stefanposs/dependapy/qa.yml?branch=main&label=CI)](https://github.com/stefanposs/dependapy/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/dependapy.svg)](https://pypi.org/project/dependapy/)
[![Website](https://img.shields.io/badge/website-stefanposs.com-blue)](https://stefanposs.com)

## Features

- 🔍 **Scan & Analyze**: Recursively scans repositories for `pyproject.toml` files and identifies outdated dependencies
- 🔄 **Python Version Check**: Ensures compatibility with the three latest Python 3 minor versions
- 🔀 **Smart PR Handling**: Creates new PRs or updates existing ones to avoid duplication
- 🛠️ **uv Compatible**: Works seamlessly with the modern `uv` package manager from astral.sh
- 🤖 **GitHub Action**: Runs automatically on a schedule via GitHub Actions

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
# Clone the repository
git clone https://github.com/stefanposs/dependapy.git
cd dependapy

# Install in development mode with uv
uv pip install -e .

# Or with pip
pip install -e .
```

## Usage

### Running Locally

To analyze your current repository and create pull requests for updates:

```bash
# Set your GitHub token for PR creation
export GITHUB_TOKEN=your_github_token

# Run dependapy (if installed from PyPI)
dependapy

# Or run as a module
python -m dependapy.main
```

If you're using `uv`:

```bash
# Set your GitHub token for PR creation
export GITHUB_TOKEN=your_github_token

# Run with uv
uv run python -m dependapy.main
```

To only check for updates without creating pull requests:

```bash
# If installed from PyPI
dependapy --no-pr

# Or run as a module
python -m dependapy.main --no-pr

# With uv
uv run python -m dependapy.main --no-pr
```

### Command Line Options

```
usage: dependapy.main [-h] [--repo-path REPO_PATH] [--token TOKEN] [--no-pr]

Analyze and update Python dependencies

options:
  -h, --help           show this help message and exit
  --repo-path REPO_PATH
                       Path to the repository to scan (default: current directory)
  --token TOKEN        GitHub token (default: from GITHUB_TOKEN environment variable)
  --no-pr              Don't create or update pull requests, just show what would be updated
```

## Setting Up as a GitHub Action

To automatically run dependapy weekly on your repository:

1. Create a file at `.github/workflows/dependapy.yml` with the following content:

```yaml
name: Dependapy

on:
  schedule:
    # Run every Sunday at 02:00 UTC
    - cron: '0 2 * * 0'
  workflow_dispatch:  # Allow manual triggering

jobs:
  update-dependencies:
    name: Update Dependencies
    runs-on: ubuntu-latest

    permissions:
      contents: write  # Needed to push code changes
      pull-requests: write  # Needed to create pull requests

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Fetch all history for git operations

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          
      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: |
          uv add dependapy

      - name: Run dependapy
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m dependapy.main
```

2. Configure the necessary permissions for GitHub Actions in your repository settings.

## How It Works

1. **Repository Scanning**: dependapy recursively finds all `pyproject.toml` files in your repository.
2. **Dependency Analysis**: 
   - Reads dependency information from the `[project]` section (following PEP 621)
   - Checks PyPI for latest available versions
   - Determines if Python version constraint is compatible with the newest Python versions
3. **Smart Updates**: Only creates PRs when actual updates are needed
4. **PR Management**: Creates a branch and PR, or updates an existing one if applicable
