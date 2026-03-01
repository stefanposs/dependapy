# Code Quality

dependapy enforces strict code quality standards through automated tooling.

## Tools

| Tool | Purpose | Command |
|---|---|---|
| **ruff** | Linting + formatting | `just analyze` / `just format` |
| **pyright** | Static type checking | `just typecheck` |
| **bandit** | Security analysis | `just security` |
| **import-linter** | Architecture contract enforcement | `just lint-imports` |
| **pytest** | Testing + coverage | `just test` / `just coverage` |
| **deptry** | Unused dependency detection | `just dependency-unused` |
| **radon** | Code metrics (complexity, maintainability) | `just statistics` |

## Ruff Configuration

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "ANN", "ARG", "PTH", "RUF"]
ignore = ["ANN101", "ANN102", "ANN201", "ANN202", "ANN204"]
```

### Enabled Rules

- `E` / `W` — pycodestyle errors and warnings
- `F` — pyflakes (unused imports, undefined names)
- `I` — isort (import ordering)
- `N` — pep8-naming
- `UP` — pyupgrade (modern Python syntax)
- `ANN` — type annotations (with select ignores)
- `ARG` — unused arguments
- `PTH` — pathlib usage
- `RUF` — ruff-specific rules

## Type Checking

Pyright in `basic` mode:

```toml
[tool.pyright]
include = ["dependapy"]
exclude = ["tests"]
typeCheckingMode = "basic"
reportMissingImports = true
```

## Security

Bandit scans for common security issues:

```toml
[tool.bandit]
exclude_dirs = ["tests"]
skips = ["B101", "B404", "B603", "B607"]
```

Skipped rules:

- `B101` — `assert` usage (OK in tests and domain invariants)
- `B404` / `B603` / `B607` — subprocess usage (required by `GitClient`)

## Architecture Enforcement

Three import-linter contracts prevent accidental layer violations:

1. **Domain** cannot import from Application, Infrastructure, Presentation,
   or external packages (`requests`, `github`, `pydantic_settings`)
2. **Application** cannot import from Infrastructure or Presentation
3. **Infrastructure** cannot import from Presentation

```bash
just lint-imports
# Contracts: 3 kept, 0 broken
```

## Code Metrics

```bash
just statistics
```

Reports:

- **Lines of Code** — total LoC across the package
- **Cyclomatic Complexity** — average complexity per function
- **Maintainability Index** — average MI score (A = excellent)

## Full CI Pipeline

Run everything at once:

```bash
just ci
```

Pipeline order: format → analyze → typecheck → test → coverage → security →
lint-imports → dependency → dependency-unused → statistics.
