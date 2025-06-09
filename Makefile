# Variables for reusable values
PACKAGE := dependapy
TEST_DIR := tests
PYTHON_DIRS := $(PACKAGE) $(TEST_DIR)

# Default target and help
.DEFAULT_GOAL := .PHONY

help:
	@echo "Available commands:"
	@echo "  analyze         : Run code analysis with ruff"
	@echo "  build           : Run QA and prepare build"
	@echo "  clean           : Remove temporary files"
	@echo "  coverage        : Check test coverage"
	@echo "  demo            : Run example usage demonstration"
	@echo "  format          : Format code with ruff"
	@echo "  install         : Install package in development mode"
	@echo "  lock            : Lock dependencies with uv"
	@echo "  pre-commit      : Run pre-commit hooks on all files"
	@echo "  pre-commit-install : Install pre-commit hooks"
	@echo "  qa              : Run all quality assurance checks (analysis, type checking, security, tests)"
	@echo "  security        : Run security checks with bandit"
	@echo "  setup-dev       : Set up a development environment"
	@echo "  test            : Run tests"
	@echo "  typecheck       : Run pyright type checking"
	@echo "  venv            : Create virtual environment with uv"

analyze:
	echo "############## Running Code Analysis ##############"
	echo "Running code analysis..."
	@uv run ruff check $(PYTHON_DIRS)

build: qa clean
	@echo "Build prepared."

clean:
	echo "############## Cleaning Up ##############"
	@echo "Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.pyd" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@find . -type d -name "*.egg" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@rm -rf build/ dist/ .coverage htmlcov/

coverage:
	echo "############## Checking Test Coverage ##############"
	@echo "Checking test coverage..."
	@uv run pytest --cov=$(PACKAGE) --cov-report=term-missing $(TEST_DIR)

format:
	echo "############## Formatting Code ##############"
	@echo "Formatting code..."
	@uv run ruff format $(PYTHON_DIRS)

qa: analyze typecheck security test

security:
	echo "############## Running Security Checks ##############"
	@echo "Running security checks..."
	@uv run bandit -r $(PACKAGE) -c pyproject.toml

setup-dev: venv install-dev pre-commit-install
	@echo "Development environment set up."

test:
	echo "############## Running Tests ##############"
	@echo "Running tests..."
	@uv run pytest --maxfail=1

test-verbose:
	echo "############## Running Tests with Verbose Output ##############"
	@echo "Running tests with verbose output..."
	@uv run pytest -v

typecheck:
	echo "############## Running Type Checking ##############"
	@echo "Running type checking..."
	@uv run pyright $(PACKAGE)

example:
	echo "############## Creating Example Project ##############"
	@echo "Creating example project..."
	@python -m scripts.setup_uv_environment

.PHONY: analyze build clean coverage demo format help install install-dev lock qa security setup-dev test test-verbose typecheck venv example pre-commit pre-commit-install ci