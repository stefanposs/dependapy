# UV Integration

dependapy works seamlessly with [uv](https://docs.astral.sh/uv/),
the fast Python package manager from Astral.

## Why uv?

| Feature | pip | uv |
|---|---|---|
| Speed | ~30s for typical install | ~2s (10–100x faster) |
| Lock files | Not built-in | `uv.lock` — deterministic |
| Virtual envs | `python -m venv` | `uv venv` (instant) |
| Workspace support | No | Yes |

## Installation

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependapy
uv add dependapy

# Or in dev mode
uv pip install -e ".[dev]"
```

## Development Workflow

### Setup

```bash
git clone https://github.com/stefanposs/dependapy.git
cd dependapy
uv sync --group dev
```

### Running Tests

```bash
# Via Justfile (recommended)
just test

# Or directly
uv run pytest tests/
```

### Full CI Pipeline

```bash
just ci
```

This runs: format → analyze → typecheck → test → coverage → security →
import contracts → dependency check → statistics.

### Common Commands

| Command | Description |
|---|---|
| `just format` | Format code with ruff |
| `just analyze` | Lint with ruff |
| `just test` | Run pytest |
| `just coverage` | Test coverage report |
| `just typecheck` | Static type checking (pyright) |
| `just security` | Security scan (bandit) |
| `just lint-imports` | Verify onion architecture contracts |
| `just dependency` | Show outdated packages |
| `just statistics` | Code metrics (LoC, complexity, maintainability) |

## uv + dependapy in CI

dependapy analyses `pyproject.toml` files — it reads the same
dependency specifications that `uv` uses. No special configuration
needed.

```yaml
# GitHub Actions
- name: Install uv
  uses: astral-sh/setup-uv@v5

- name: Install dependapy
  run: uv pip install dependapy

- name: Run
  run: uv run dependapy --dry-run
```

!!! tip "uv is not required"
    dependapy works with any Python package manager. `uv` is recommended
    for development speed, but `pip` works equally well.
