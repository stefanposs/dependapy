# justfile for dependapy
#
# All dev tools are declared in [dependency-groups] dev in pyproject.toml.
# Install once with: uv sync --group dev
#
# Default recipe runs full CI pipeline.

set shell := ["bash", "-cu"]

PACKAGE := "dependapy"
TEST_DIR := "tests"
PYTHON_DIRS := PACKAGE + " " + TEST_DIR

# Default: run full CI pipeline
_default:
    @just ci

# ----------- Lint & Format -----------

# Format code with ruff
format:
    @echo "############## Formatting Code ##############"
    uv run ruff format {{PYTHON_DIRS}}

# Analyze and lint code with ruff
analyze:
    @echo "############## Running Code Analysis ##############"
    uv run ruff check {{PYTHON_DIRS}}

# Auto-fix lint issues
fix:
    uv run ruff check {{PYTHON_DIRS}} --fix

# ----------- Test -----------

# Run all tests with pytest
test:
    @echo "############## Running Tests ##############"
    uv run pytest --maxfail=1 {{TEST_DIR}}

# Run tests with coverage report
coverage:
    @echo "############## Checking Test Coverage ##############"
    uv run pytest --cov={{PACKAGE}} --cov-report=term-missing {{TEST_DIR}}

# ----------- Type Checking -----------

# Static type checking with pyright
typecheck:
    @echo "############## Running Type Checking ##############"
    uv run pyright {{PACKAGE}}

# ----------- Security -----------

# Security analysis with bandit
security:
    @echo "############## Running Security Checks ##############"
    uv run bandit -r {{PACKAGE}} -c pyproject.toml

# ----------- Architecture -----------

# Verify import layer contracts (onion architecture)
lint-imports:
    @echo "############## Checking Import Contracts ##############"
    uv run lint-imports

# ----------- Dependency Checks -----------

# Show outdated packages from pyproject.toml
dependency:
    @echo "############## Checking Dependencies ##############"
    @uv run python -c "\
        import tomllib; \
        d = tomllib.load(open('pyproject.toml', 'rb')); \
        deps = d.get('project', {}).get('dependencies', []); \
        dev_deps = d.get('dependency-groups', {}).get('dev', []); \
        all_deps = deps + dev_deps; \
        pkgs = sorted(set([ \
            dep.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0] \
            .replace('_', '-').strip() \
            for dep in all_deps if dep.strip() and not dep.strip().startswith('--') \
        ])); \
        f = open('.outdated-filter.txt', 'w'); \
        [f.write(pkg + '\n') for pkg in pkgs if pkg]; \
        f.close()"
    @echo "| Package                        | Current      | Latest       |"
    @echo "|--------------------------------|--------------|--------------|"
    @uv run pip list --outdated --format=columns \
        | awk 'NR>2{printf "| %-30s | %-12s | %-12s |\n", $1, $2, $3}' \
        | grep -F -f .outdated-filter.txt \
        || echo "All packages up to date."
    @rm -f .outdated-filter.txt

# Find unused dependencies
dependency-unused:
    @echo "############## Checking Unused Dependencies ##############"
    uv run deptry {{PACKAGE}} {{TEST_DIR}} || echo "Unused dependencies found. See above."

# ----------- Statistics -----------

# Show code statistics and quality metrics
statistics:
    @echo "############## Code Statistics ##############"
    @echo "### Lines of Code (LoC) total:"
    @uv run radon raw {{PACKAGE}} | grep "LOC:" | awk '{s+=$2} END {print s " LoC"}'
    @echo ""
    @echo "### Cyclomatic Complexity (total):"
    @uv run radon cc {{PACKAGE}} -a -s | grep "Average complexity" || true
    @echo ""
    @echo "### Maintainability Index (average):"
    @uv run radon mi -s {{PACKAGE}} \
        | awk -F'[()]' '/ - [A-D] / {gsub(/ /,"",$2); sum+=($2+0); n++} END { \
            if(n>0){avg=sum/n; grade=(avg>=80?"A":(avg>=70?"B":(avg>=60?"C":"D"))); \
            printf "Average MI: %s (%.2f)\n", grade, avg} \
            else {print "No MI data found."}}'

# ----------- Export/Freeze -----------

# Export requirements.txt from pyproject.toml
freeze:
    @echo "############## Generating requirements.txt ##############"
    @uv run python -c "\
        import tomllib; \
        d = tomllib.load(open('pyproject.toml', 'rb')); \
        deps = d.get('project', {}).get('dependencies', []); \
        f = open('requirements.txt', 'w'); \
        [f.write(dep + '\n') for dep in deps]; \
        f.close()"
    @echo "requirements.txt generated."

# ----------- QA/CI -----------

# Run full CI pipeline (format, analyze, typecheck, test, coverage, security, lint-imports, deps, stats)
ci:
    @echo "############### FORMAT ###############"
    @just format
    @echo ""
    @echo "############### ANALYZE ###############"
    @just analyze
    @echo ""
    @echo "############### TYPECHECK ###############"
    @just typecheck
    @echo ""
    @echo "############### TEST ###############"
    @just test
    @echo ""
    @echo "############### COVERAGE ###############"
    @just coverage
    @echo ""
    @echo "############### SECURITY ###############"
    @just security
    @echo ""
    @echo "############### IMPORT CONTRACTS ###############"
    @just lint-imports
    @echo ""
    @echo "############### DEPENDENCY ###############"
    @just dependency
    @just dependency-unused
    @echo ""
    @echo "############### STATISTICS ###############"
    @just statistics

# ----------- Documentation -----------

# Build MkDocs documentation (assets/mkdocs → docs/)
docs:
    @echo "############## Building Documentation ##############"
    NO_MKDOCS_2_WARNING=1 uv run mkdocs build --config-file mkdocs.yml --strict

# Serve documentation locally with live reload
docs-serve:
    @echo "############## Serving Documentation ##############"
    NO_MKDOCS_2_WARNING=1 uv run mkdocs serve --config-file mkdocs.yml

# ----------- Help -----------

# List all available recipes
help:
    @just --list
 