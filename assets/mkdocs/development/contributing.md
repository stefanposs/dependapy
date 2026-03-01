# Contributing

Contributions to dependapy are welcome! This guide covers the development
workflow.

## Setup

```bash
# Clone the repository
git clone https://github.com/stefanposs/dependapy.git
cd dependapy

# Install dependencies (requires uv)
uv sync --group dev

# Verify setup
just ci
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature
```

### 2. Make Changes

Follow the architecture:

- **Domain changes** → `dependapy/domain/`
- **New adapters** → `dependapy/infrastructure/`
- **Use case changes** → `dependapy/application/`
- **CLI changes** → `dependapy/presentation/`

### 3. Run Quality Checks

```bash
# Full CI pipeline
just ci

# Or individual checks:
just format       # Format code
just analyze      # Lint with ruff
just typecheck    # Static type checking
just test         # Run tests
just lint-imports # Verify layer contracts
```

### 4. Write Tests

- Use `tests/factories.py` helpers: `make_version`, `make_spec`, `make_dep`, `make_project`
- Follow existing patterns in `tests/`
- Aim for >80% coverage (currently 91%)

### 5. Submit a PR

```bash
git push origin feature/your-feature
# Create PR on GitHub
```

## Architecture Rules

!!! warning "Layer violations break CI"

    The import-linter contracts in `pyproject.toml` enforce strict layer
    boundaries. If you import `requests` in the domain layer, CI will fail.

1. **Domain** may only import from `stdlib` and `packaging`
2. **Application** may only import from Domain
3. **Infrastructure** may not import from Presentation
4. **Use `Result[T, E]`** for all fallible operations — no exceptions for control flow
5. **Protocol ports** in domain — implementations in infrastructure

## Justfile Recipes

| Recipe | Description |
|---|---|
| `just ci` | Full CI pipeline |
| `just test` | Run pytest |
| `just coverage` | Coverage report |
| `just format` | Format with ruff |
| `just analyze` | Lint with ruff |
| `just fix` | Auto-fix lint issues |
| `just typecheck` | Pyright type checking |
| `just security` | Bandit security scan |
| `just lint-imports` | Import contract checks |
| `just dependency` | Show outdated packages |
| `just dependency-unused` | Find unused dependencies |
| `just statistics` | Code metrics |
| `just help` | List all recipes |

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add GitLab VCS adapter
fix: correct upper bound parsing for >=3.11,<4.0
test: add EndOfLifeAdapter cache tests
docs: update architecture overview
refactor: narrow exceptions in filesystem adapter
```
