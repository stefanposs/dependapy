# justfile for Python project tasks
#
# This justfile automates all essential tasks for a modern Python project.
# It is optimized for teamwork, CI/CD, and developer experience.
#
# Notes:
# - Temporary files are removed after use.
# - Recipe names are clear and commented.
# - The default task runs a full QA check (ideal for pre-commit or CI).
 
set shell := ["bash", "-cu"]
 
 
SRC_DIR := "src"
TEST_DIR := "test"
 
# Default: Run all checks (QA/CI)
_:
    @just ci
 
# ----------- Lint & Format -----------
# Analyze and lint code with ruff (auto-fix enabled)
analyze:
    @uv add ruff --dev
    ruff check {{SRC_DIR}} {{TEST_DIR}} --fix
    @echo ""
    @echo "See https://docs.astral.sh/ruff/ for details."
 
# Format code with ruff (PEP8)
format:
    @uv add ruff --dev
    ruff format {{SRC_DIR}} {{TEST_DIR}}
    @echo ""
    @echo "See https://docs.astral.sh/ruff/ for details."
 
# ---------- Coverage -----------
# Run tests with coverage analysis
coverage:
    @uv add coverage --dev
    @uv run coverage run -m unittest discover -s {{TEST_DIR}} -p "*test*.py"
    @uv run coverage report --omit="{{TEST_DIR}}/*"
 
# ----------- Dependency Checks -----------
# Show all outdated packages from pyproject.toml (incl. dev, sorted alphabetically)
dependency:
    @uv add pip --dev
    @uv run python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); deps = d['project']['dependencies'] if 'dependencies' in d.get('project', {}) else []; dev_deps = d.get('dependency-groups', {}).get('dev', []); all_deps = deps + dev_deps; pkgs = sorted(set([dep.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].replace('_','-').strip() for dep in all_deps if dep.strip() and not dep.strip().startswith('--')])); f=open('requirements.txt','w'); [f.write(pkg+'\n') for pkg in pkgs if pkg]; f.close()"
    @echo "| Package                        | Current      | Latest       |"
    @echo "|--------------------------------|--------------|--------------|"
    @uv run pip list --outdated --format=columns | awk 'NR>2{printf "| %-30s | %-12s | %-12s |\n", $1, $2, $3}' | grep -F -f requirements.txt || (echo "No outdated packages from pyproject.toml (incl. dev) found.")
    @rm -f requirements.txt
    @echo ""
    @echo "See https://pip.pypa.io/en/stable/cli/pip_list/ for details."
 
# ----------- Unused Dependency Check -----------
# Find unused dependencies in src and test directories
dependency-unused:
    @uv add deptry --dev
    @uv run deptry {{SRC_DIR}} {{TEST_DIR}} || (echo "Unused dependencies found. See above for details.")
    @echo ""
    @echo "See https://github.com/fpgmaas/deptry for details."
 
# ----------- Export/Freeze -----------
# Export requirements.txt from pyproject.toml (incl. extra index-url)
freeze:
    echo "Generate requirements.txt ..."
    @uv run python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); urls=['--extra-index-url https://europe-west6-python.pkg.dev/axach-inetbuildingzonereg-ibz/python-virtual-pyrepo/simple']; deps = d['project']['dependencies'] if 'dependencies' in d.get('project', {}) else []; f=open('requirements.txt','w'); [f.write(u+'\n') for u in urls]; [f.write(dep+'\n') for dep in deps]; f.close()"
    echo "... done"
    @echo ""
    @echo "See https://pip.pypa.io/en/stable/cli/pip_freeze/ for details."
 
# ----------- QA/CI -----------
# Run all checks in a logical order (ideal for CI/CD or pre-commit)
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
    just coverage
    @echo ""
    @echo "############### SECURITY ###############"
    @just security
    @echo ""
    @echo "############### DEPENDENCY ###############"
    @just dependency
    @just dependency-unused
    #    @echo "############### FREEZE ###############"
    #    @just freeze
    @echo ""
    @echo "############### STATISTICS ###############"
    @just statistics
 
# ----------- Security -----------
# Security analysis with bandit
security:
    @uv add bandit --dev
    bandit -r {{SRC_DIR}}
    @echo ""
    @echo "See https://bandit.readthedocs.io/en/latest/ for details."
 
# ----------- Statistics -----------
# Show code statistics and quality metrics
statistics:
    @uv add radon --dev
    @echo "### Lines of Code (LoC) total:"
    @uv run radon raw {{SRC_DIR}} | grep "LOC:" | awk '{s+=$2} END {print s " LoC"}'
    @echo ""
    @echo "### Cyclomatic Complexity (total):"
    @uv run radon cc {{SRC_DIR}} -a -s | grep "Average complexity" || true
    @echo ""
    @echo "### Maintainability Index (average):"
    @uv run radon mi -s {{SRC_DIR}} | awk -F'[()]' '/ - [A-D] / {gsub(/ /,"",$2); sum+=($2+0); n++} END {if(n>0){avg=sum/n; grade=(avg>=80?"A":(avg>=70?"B":(avg>=60?"C":"D"))); printf "Average MI: %s (%.2f)\n", grade, avg} else {print "No MI data found."}}'
    @echo ""
    @echo "Legend:"
    @echo "- Cyclomatic Complexity (CC): Measures the number of independent paths through your code. Lower is better. Grades: A (simple, easy to maintain) ... F (very complex, hard to maintain)."
    @echo "- Maintainability Index (MI): Estimates how easy it is to maintain your code. Higher is better. A (>80, very maintainable), B (70-80, maintainable), C (60-70, moderate), D (<60, hard to maintain)."
    @echo ""
    @echo "See https://radon.readthedocs.io/en/latest/ for details."
 
# ----------- Test -----------
# Run all unittests
# (kept for compatibility with ci)
test:
    uv run python -m unittest discover -b -s {{TEST_DIR}} -p "*test*.py" -v
 
# ----------- Typecheck -----------
# Static type checking with pyright
# (alias for compatibility with ci)
typecheck:
    @uv add pyright --dev
    uv run pyright {{SRC_DIR}} {{TEST_DIR}}
    @echo ""
    @echo "See https://github.com/microsoft/pyright for details."
 
# ----------- Help -----------
# List all available justfile commands
help:
    just --list
 