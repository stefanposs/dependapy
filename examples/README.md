# dependapy Examples

Practical examples showing how to use dependapy as a **CLI tool** and as a **Python library**.

## Quick Start

```bash
# Analyze the example project (dry-run)
dependapy examples/example_py_project --dry-run

# Analyze and apply updates (no PR)
dependapy examples/example_py_project --no-pr

# Generate offline patches
dependapy examples/example_py_project --offline-pr
```

## Example Scripts

| Script | Description |
|--------|-------------|
| `analyze_project.py` | Analyze dependencies using the Python API |
| `domain_services.py` | Use domain services for version comparison & update planning |
| `custom_pipeline.py` | Build a custom analyze → apply → report pipeline |

Run any script from the repository root:

```bash
uv run python examples/analyze_project.py
uv run python examples/domain_services.py
uv run python examples/custom_pipeline.py
```

## Example Project

`example_py_project/` contains a minimal Python project with intentionally
outdated dependencies — use it as a target for dependapy analysis.

## GitHub Action

`example_dependapy.yml` is a ready-to-use GitHub Actions workflow that runs
dependapy on a weekly schedule.
