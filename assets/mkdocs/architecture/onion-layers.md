# Onion Layers

The four layers of dependapy's Onion Architecture, from innermost to outermost.

## Domain Layer — The Core

The domain is the heart of dependapy. It defines **what** the system does,
not **how** it interacts with external systems.

### Entities

```python
@dataclass
class Dependency:
    name: str
    current_spec: PackageSpec
    latest_version: Version | None = None

@dataclass
class Project:
    name: str
    path: Path
    dependencies: list[Dependency]
    python_constraint: VersionConstraint | None = None

@dataclass
class UpdatePlan:
    project: Project
    updates: list[Dependency]
    status: PlanStatus = PlanStatus.DRAFT
```

### Value Objects

Immutable, equality-by-value types:

- `Version` — Wraps `packaging.version.Version` with comparison operators
- `PackageSpec` — Package name + version constraint (`requests>=2.31`)
- `VersionConstraint` — Parsed version range with operator
- `UpdateType` — Enum: `PATCH`, `MINOR`, `MAJOR`

### Domain Services

- `VersionResolver` — Given a dependency and a registry, determine if it's outdated
- `UpdatePlanner` — Generate an `UpdatePlan` from a project's dependencies

### Ports (Protocols)

```python
@runtime_checkable
class PackageRegistry(Protocol):
    def get_latest_version(self, name: str) -> Result[Version, str]: ...
    def get_latest_versions_batch(self, names: list[str]) -> dict[str, Result[Version, str]]: ...

@runtime_checkable
class ProjectRepository(Protocol):
    def find_project_files(self, root: Path) -> Result[list[Path], str]: ...
    def load_project(self, path: Path) -> Result[Project, str]: ...
    def save_project(self, project: Project) -> Result[None, str]: ...

@runtime_checkable
class VCSPort(Protocol):
    def create_branch(self, name: str) -> Result[None, str]: ...
    def commit_and_push(self, message: str, files: list[Path]) -> Result[None, str]: ...
    def create_pull_request(self, title: str, body: str, branch: str) -> Result[str, str]: ...
```

!!! info "Dependency rule"
    The domain layer only imports from `stdlib` and `packaging`.
    This is enforced by import-linter contracts in `pyproject.toml`.

---

## Application Layer — Use Cases

The application layer orchestrates domain logic. Each use case is a
single class with an `execute()` method.

### AnalyzeDependencies

```python
class AnalyzeDependencies:
    def __init__(self, repo: ProjectRepository, registry: PackageRegistry, ...):
        ...

    def execute(self, root: Path) -> Result[list[AnalysisResult], str]:
        # 1. Find pyproject.toml files
        # 2. Load each project
        # 3. Resolve latest versions (batch)
        # 4. Check Python version support
        # 5. Return analysis results
```

### ApplyUpdates

Updates `pyproject.toml` files in place based on an `UpdatePlan`.

### SubmitChanges

Creates a branch, commits the changes, and opens a PR (or generates a patch).

---

## Infrastructure Layer — Adapters

Infrastructure adapters implement domain ports using concrete technologies.

| Adapter | Implements | Technology |
|---|---|---|
| `PyPIAdapter` | `PackageRegistry` | `requests` + JSON API |
| `FileSystemProjectRepository` | `ProjectRepository` | `tomllib` + file I/O |
| `EndOfLifeAdapter` | `PythonVersionRegistry` | endoflife.date API |
| `GitHubVCSAdapter` | `VCSPort` | PyGithub |
| `OfflinePatchAdapter` | `VCSPort` | `git format-patch` |
| `HttpClient` | — | `requests.Session` with retry/timeout |

---

## Presentation Layer — CLI

The thinnest layer. Parses arguments, wires the application via `bootstrap()`,
and calls use cases.

```python
def cli_main() -> None:
    args = parse_args()
    config = AppConfig(...)
    with bootstrap(config) as app:
        result = app.analyze.execute(Path(args.repo_path))
        # ... handle result
```

---

## Import-Linter Contracts

Three contracts enforce the layer boundaries:

```toml
[[tool.importlinter.contracts]]
name = "Domain layer must not import from other layers"
type = "forbidden"
source_modules = ["dependapy.domain"]
forbidden_modules = [
    "dependapy.application",
    "dependapy.infrastructure",
    "dependapy.presentation",
    "requests", "github", "pydantic_settings",
]
```

Run `just lint-imports` to verify all contracts pass.
