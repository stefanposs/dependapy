# Working with dependapy and UV

This guide explains how to effectively use dependapy with [uv](https://github.com/astral-sh/uv), the fast Python package installer and resolver.

## What is uv?

`uv` is a modern alternative to tools like `pip`, `virtualenv`, and others, combining:
- Fast package installation
- Quick environment creation
- Reliable dependency resolution

## Setting Up Your Environment with uv

### Installation

Install uv if you haven't already:

```bash
# Install uv using the official script
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Create Virtual Environment

```bash
# Navigate to your project
cd your-project

# Create a virtual environment and install dependencies with one command
make setup-dev

# Or manually:
uv venv
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### Install dependapy

```bash
# Install dependapy with uv
uv pip install git+https://github.com/username/dependapy.git

# Or for development (using make):
git clone https://github.com/username/dependapy.git
cd dependapy
make install-dev

# Or manually:
uv pip install -e ".[dev]"
```

## Using dependapy with uv-managed Projects

dependapy works with any project using standard `pyproject.toml` files, including those managed with `uv`.

### Example Workflow

1. **Initial Setup**:
   ```bash
   # Create your project
   mkdir my-project && cd my-project
   
   # Set up virtual environment with uv
   uv venv
   source .venv/bin/activate  # Or appropriate activation command for your OS
   
   # Create initial pyproject.toml
   cat > pyproject.toml << EOF
   [build-system]
   requires = ["setuptools>=61.0"]
   build-backend = "setuptools.build_meta"
   
   [project]
   name = "my-project"
   version = "0.1.0"
   requires-python = ">=3.8"
   dependencies = [
       "requests>=2.25.0",
   ]
   EOF
   
   # Install dependencies
   uv pip install -e .
   ```

2. **Run dependapy**:
   ```bash
   # For manual checks without creating PRs
   python -m dependapy.main --no-pr
   ```

3. **Incorporate Updates**:
   After dependapy identifies updates, you can use `uv` to install the updated dependencies:
   ```bash
   # After updating pyproject.toml, reinstall with uv
   uv pip install -e .
   ```

## Advantages of Using uv with dependapy

1. **Speed**: `uv` is significantly faster than pip for installing packages
2. **Reliability**: More reliable dependency resolution
3. **Consistency**: Works well with modern Python packaging standards

## Additional uv Commands

- `uv pip list`: List installed packages
- `uv pip freeze`: Output installed packages in requirements format
- `uv pip install -r requirements.txt`: Install from requirements file

For more information, see the [uv documentation](https://github.com/astral-sh/uv).

## Running Tests with uv

When testing dependapy itself:

```bash
# Using make commands
make test          # Run basic tests
make coverage      # Run tests with coverage
make qa            # Run full quality assurance suite

# Or manually
uv run pytest
uv run pytest --cov=dependapy --cov-report=term-missing
```
