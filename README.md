# dependapy

This is a custom `dependabot` alternative which can run without any external service or settings. It's designed to work with Python projects that use `pyproject.toml` and is compatible with the `uv` package manager from astral.sh.

## Features

- 🔍 **Scan & Analyze**: Recursively scans repositories for `pyproject.toml` files and identifies outdated dependencies
- 🔄 **Python Version Check**: Ensures compatibility with the three latest Python 3 minor versions
- 🔀 **Smart PR Handling**: Creates new PRs or updates existing ones to avoid duplication
- 🛠️ **uv Compatible**: Works seamlessly with the modern `uv` package manager from astral.sh
- 🤖 **GitHub Action**: Runs automatically on a schedule via GitHub Actions

## Installation

### With uv (recommended)

```bash
uv pip install git+https://github.com/YOUR_USERNAME/dependapy.git
```

### With pip

```bash
pip install git+https://github.com/YOUR_USERNAME/dependapy.git
```

## Usage

### Running Locally

To analyze your current repository and create pull requests for updates:

```bash
# Set your GitHub token for PR creation
export GITHUB_TOKEN=your_github_token

# Run dependapy
python -m dependapy.main
```

To only check for updates without creating pull requests:

```bash
python -m dependapy.main --no-pr
```

### Command Line Options

```
usage: main.py [-h] [--repo-path REPO_PATH] [--token TOKEN] [--no-pr]

options:
  -h, --help            show this help message and exit
  --repo-path REPO_PATH  Path to the repository to scan (default: current directory)
  --token TOKEN         GitHub token (default: from GITHUB_TOKEN environment variable)
  --no-pr               Don't create or update pull requests, just show what would be updated
```

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
          uv pip install git+https://github.com/YOUR_USERNAME/dependapy.git

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

## Development

### Setup Development Environment

```bash
# Create virtual environment and install dev dependencies 
make setup-dev

# Or manually
uv venv
source .venv/bin/activate  # On macOS/Linux
uv pip install -e ".[dev]"
```

### Available Make Commands

```bash
make help            # Show all available commands
make test            # Run tests
make coverage        # Run tests with coverage report
make format          # Format code with ruff
make analyze         # Run code analysis
make typecheck       # Run type checking
make qa              # Run all quality checks
make pre-commit      # Run pre-commit hooks
make demo            # Run example usage demonstration
```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality. They are installed automatically when running `make setup-dev`, but you can also install them manually:

```bash
make pre-commit-install
```

This will set up the following checks to run automatically before each commit:
- Code formatting with ruff
- Linting with ruff
- Type checking with pyright
- Security checks with bandit
- YAML/TOML validation
