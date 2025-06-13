# Makefile for Python project tasks

PACKAGE := dependapy
TEST_DIR := tests
PYTHON_DIRS := $(PACKAGE) $(TEST_DIR)

_DEFAULT: ci

ci: format analyze typecheck test coverage security dependency dependency-unused statistics
.PHONY: analyze format dependency dependency-unused security typecheck coverage statistics test ci help

# ----------- Lint & Format -----------
# Analyze and lint code with ruff (auto-fix enabled)
analyze:
	@echo "############## Running Code Analysis ##############"
	@echo "Running code analysis..."
	@uv run ruff check $(PYTHON_DIRS)
	@echo ""
	@echo "See https://docs.astral.sh/ruff/ for details."
	@echo ""

# Format code with ruff (PEP8)
format:
	@echo "############## Formatting Code ##############"
	@echo "Formatting code..."
	@uv run ruff format $(PYTHON_DIRS)
	@echo ""
	@echo "See https://docs.astral.sh/ruff/ for details."
	@echo ""

# ---------- Coverage -----------
# Run tests with coverage analysis
coverage:
	@echo "############## Checking Test Coverage ##############"
	@echo "Checking test coverage..."
	@uv run pytest --cov=$(PACKAGE) --cov-report=term-missing $(TEST_DIR)
	@echo ""

# ----------- Dependency Checks -----------
# Show all outdated packages from pyproject.toml (incl. dev, sorted alphabetically)
dependency:
	@echo "############## Checking Dependencies ##############"
	@echo "Checking for outdated dependencies..."
	@uv add pip --dev
	@uv run python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); deps = d['project']['dependencies'] if 'dependencies' in d.get('project', {}) else []; dev_deps = d.get('dependency-groups', {}).get('dev', []); all_deps = deps + dev_deps; pkgs = sorted(set([dep.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].replace('_','-').strip() for dep in all_deps if dep.strip() and not dep.strip().startswith('--')])); f=open('requirements.txt','w'); [f.write(pkg+'\n') for pkg in pkgs if pkg]; f.close()"
	@echo "| Package                        | Current      | Latest       |"
	@echo "|--------------------------------|--------------|--------------|"
	@uv run pip list --outdated --format=columns | awk 'NR>2{printf "| %-30s | %-12s | %-12s |\n", $$1, $$2, $$3}' | grep -F -f requirements.txt || (echo "No outdated packages from pyproject.toml (incl. dev) found.")
	@rm -f requirements.txt
	@echo ""
	@echo "See https://pip.pypa.io/en/stable/cli/pip_list/ for details."
	@echo ""

# ----------- Unused Dependency Check -----------
# Find unused dependencies in src and test directories
dependency-unused:
	@echo "############## Checking Unused Dependencies ##############"
	@echo "Checking for unused dependencies..."
	@uv add deptry --dev
	@uv run deptry $(PACKAGE) $(TEST_DIR) || (echo "Unused dependencies found. See above for details.")
	@echo ""
	@echo "See https://github.com/fpgmaas/deptry for details."
	@echo ""

# ----------- Export/Freeze -----------
# Export requirements.txt from pyproject.toml (incl. extra index-url)
freeze:
	@echo "############## Generating requirements.txt ##############"
	@echo "Generating requirements.txt..."
	@uv run python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); urls=['--extra-index-url https://europe-west6-python.pkg.dev/axach-inetbuildingzonereg-ibz/python-virtual-pyrepo/simple']; deps = d['project']['dependencies'] if 'dependencies' in d.get('project', {}) else []; f=open('requirements.txt','w'); [f.write(u+'\n') for u in urls]; [f.write(dep+'\n') for dep in deps]; f.close()"
	@echo "... done"
	@echo ""
	@echo "See https://pip.pypa.io/en/stable/cli/pip_freeze/ for details."
	@echo ""

# ----------- Security -----------
# Security analysis with bandit
security:
	@echo "############## Running Security Checks ##############"
	@echo "Running security checks..."
	@uv add bandit --dev
	@uv run bandit -r $(PACKAGE) -c pyproject.toml
	@echo ""
	@echo "See https://bandit.readthedocs.io/en/latest/ for details."
	@echo ""

# ----------- Statistics -----------
# Show code statistics and quality metrics
statistics:
	@echo "############## Code Statistics ##############"
	@echo "Generating code statistics..."
	@uv add radon --dev
	@echo "### Lines of Code (LoC) total:"
	@uv run radon raw $(PACKAGE) | grep "LOC:" | awk '{sum += $$2} END {print sum " LoC"}'
	@echo ""
	@echo "### Cyclomatic Complexity (total):"
	@uv run radon cc $(PACKAGE) -a -s | grep "Average complexity" || true
	@echo ""
	@echo "### Maintainability Index (average):"
	@uv run radon mi -s $(PACKAGE) | awk -F'[()]' '/ - [A-D] / {gsub(/ /,"",$$2); sum+=($$2+0); n++} END {if(n>0){avg=sum/n; grade=(avg>=80?"A":(avg>=70?"B":(avg>=60?"C":"D"))); printf "Average MI: %s (%.2f)\n", grade, avg} else {print "No MI data found."}}'
	@echo ""
	@echo "Legend:"
	@echo "- Cyclomatic Complexity (CC): Measures the number of independent paths through your code. Lower is better. Grades: A (simple, easy to maintain) ... F (very complex, hard to maintain)."
	@echo "- Maintainability Index (MI): Estimates how easy it is to maintain your code. Higher is better. A (>80, very maintainable), B (70-80, maintainable), C (60-70, moderate), D (<60, hard to maintain)."
	@echo ""
	@echo "See https://radon.readthedocs.io/en/latest/ for details."
	@echo ""

# ----------- Test -----------
# Run all tests
test:
	@echo "############## Running Tests ##############"
	@echo "Running tests..."
	@uv run pytest --maxfail=1 $(TEST_DIR)
	@echo ""

# ----------- Typecheck -----------
# Static type checking with pyright
typecheck:
	@echo "############## Running Type Checking ##############"
	@echo "Running type checking..."
	@uv add pyright --dev
	@uv run pyright $(PACKAGE)
	@echo ""
	@echo "See https://github.com/microsoft/pyright for details."
	@echo ""
