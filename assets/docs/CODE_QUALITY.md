# Code Quality Guidelines

This document outlines the code quality standards and tools used in the dependapy project.

## Code Style and Formatting

We use [ruff](https://github.com/astral-sh/ruff) as our primary tool for code formatting and linting. Ruff is a fast Python linter and formatter, written in Rust.

### Ruff Configuration

Our ruff configuration is defined in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py310"
line-length = 100
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "N",   # pep8-naming
    "SIM", # flake8-simplify
    "A",   # flake8-builtins
]
ignore = ["E203"]
```

### Running Ruff

You can run ruff using the Makefile:

```bash
# Format code
make format

# Check code (without formatting)
make analyze
```

## Type Checking

We use [pyright](https://github.com/microsoft/pyright) for type checking. It's a fast, static type checker for Python, written in TypeScript.

```bash
# Run type checking
make typecheck
```

## Security Checks

[Bandit](https://github.com/PyCQA/bandit) is used to find common security issues in Python code.

```bash
# Run security checks
make security
```

## Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to run checks automatically before each commit. The configuration is in `.pre-commit-config.yaml`.

```bash
# Install pre-commit hooks
make pre-commit-install

# Run pre-commit hooks manually
make pre-commit
```

## Quality Assurance

To run all quality checks at once:

```bash
make qa
```

This runs code analysis, type checking, security checks, and tests.

## CI Pipeline

Our CI pipeline runs these checks for every pull request and on the main branch. The configuration is in `.github/workflows/ci.yml`.

## Best Practices

1. **Always run tests before committing**: Use `make test` to ensure your changes don't break existing functionality.
2. **Format your code**: Use `make format` to ensure consistent code style.
3. **Add type annotations**: Add appropriate type annotations to function arguments and return values.
4. **Use pre-commit hooks**: They catch common issues before they make it into the codebase.
5. **Run full QA before submitting PR**: Use `make qa` to check everything.
