# UV Integration & Usage Guide for dependapy

## Installation with uv

`dependapy` can be easily installed using `uv`:

```bash
# Install from repository
uv pip install git+https://github.com/username/dependapy.git

# Install in development mode from local repo
cd dependapy
uv pip install -e .

# Install with development dependencies
uv pip install -e ".[dev]"

# Or simply use make
make setup-dev
```

## Testing with uv

The project is fully compatible with `uv`. You can run tests using the Makefile:

```bash
# Using make commands
make test        # Run tests
make coverage    # Run tests with coverage report
make qa          # Run all quality checks

# Or directly with uv
uv run pytest
```

## Development Workflow with uv

1. Clone repository
   ```bash
   git clone https://github.com/username/dependapy.git
   cd dependapy
   ```

2. Set up development environment with make
   ```bash
   make setup-dev
   ```
   
   Or manually:
   ```bash
   uv venv
   source .venv/bin/activate  # On Linux/macOS
   # or
   .venv\Scripts\activate     # On Windows
   uv pip install -e ".[dev]"
   ```

3. Format and lint code
   ```bash
   make format    # Format code with ruff
   make analyze   # Analyze code with ruff
   ```

4. Dependency management with uv
   ```bash
   # Lock dependencies
   make lock
   
   # Add new dependency
   uv pip install new_package
   
   # Update dependencies
   uv pip install -U package_name
   ```

5. Common development commands using make
   ```bash
   # Run quality checks
   make qa
   
   # Type checking
   make typecheck
   
   # Security checks
   make security
   
   # Run example demonstration
   make demo
   ```

## Use in CI/CD Workflow

The GitHub Action already integrates `uv`. It performs these steps:

1. Repository checkout 
2. Python installation
3. `uv` installation
4. `dependapy` installation
5. Running the tool to scan and update dependencies

## Advantages of uv Integration

- **Speed**: Package installation is significantly faster
- **Stability**: Improved dependency resolution
- **Compatibility**: Full support for PEP 621 `pyproject.toml`
- **Reproducibility**: Consistent results across environments

## Common uv Commands

```bash
# Show version
uv --version

# Create virtual environment
uv venv

# Install package
uv pip install package_name

# Install package with specific version
uv pip install package_name==1.2.3

# Install dependencies from pyproject.toml
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"

# Update package
uv pip install -U package_name
```

## Development Guidelines

- Use `uv` for all package installations
- Follow PEP 621 for project metadata
- Use the CI scripts in the Makefile for local testing
