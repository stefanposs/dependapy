# Testing

dependapy has a comprehensive test suite built with pytest.

## Overview

<div class="stat-grid" markdown>

<div class="stat" markdown>
<span class="number">178</span>
<span class="label">Tests</span>
</div>

<div class="stat" markdown>
<span class="number">91%</span>
<span class="label">Coverage</span>
</div>

<div class="stat" markdown>
<span class="number">3/3</span>
<span class="label">Import Contracts</span>
</div>

</div>

## Running Tests

```bash
# Quick run — stop on first failure
just test

# With coverage report
just coverage

# Run a specific test file
uv run pytest tests/test_models.py -v

# Run a specific test
uv run pytest tests/test_models.py::test_update_plan_approve -v
```

## Test Structure

```
tests/
├── conftest.py                      # Fixtures
├── factories.py                     # Test helpers (make_version, make_dep, ...)
├── test_models.py                   # Domain entity tests
├── test_value_objects.py            # Value object tests
├── test_services.py                 # Domain service tests
├── test_use_cases.py                # Application use case tests
├── test_result.py                   # Result pattern tests (if present)
└── infrastructure/
    ├── test_filesystem_adapter.py   # FileSystem adapter tests
    ├── test_http_client.py          # HttpClient tests
    └── test_endoflife_adapter.py    # EndOfLife adapter tests
```

## Test Factories

Use `tests/factories.py` to create test objects consistently:

```python
from tests.factories import make_version, make_spec, make_dep, make_project

# Create a Version
v = make_version("2.31.0")

# Create a PackageSpec
spec = make_spec("requests", ">=2.31")

# Create a Dependency
dep = make_dep("requests", ">=2.31", latest="2.32.3")

# Create a Project
project = make_project("my-project", deps=[dep])
```

## Testing Patterns

### Domain Tests

Test entities and value objects in isolation:

```python
def test_update_plan_state_transitions():
    plan = UpdatePlan(project=project, updates=[dep])
    assert plan.status == PlanStatus.DRAFT

    plan.approve()
    assert plan.status == PlanStatus.APPROVED

    plan.mark_applied()
    assert plan.status == PlanStatus.APPLIED
```

### Use Case Tests

Mock ports and verify orchestration:

```python
def test_analyze_finds_outdated_deps(mock_repo, mock_registry):
    mock_repo.find_project_files.return_value = Ok([Path("pyproject.toml")])
    mock_repo.load_project.return_value = Ok(project)
    mock_registry.get_latest_versions_batch.return_value = {
        "requests": Ok(make_version("2.32.3")),
    }

    uc = AnalyzeDependencies(mock_repo, mock_registry, mock_eol)
    result = uc.execute(Path("."))

    assert isinstance(result, Ok)
```

### Infrastructure Tests

Test adapters with mocked HTTP responses:

```python
def test_pypi_adapter_returns_latest_version(responses):
    responses.get(
        "https://pypi.org/pypi/requests/json",
        json={"info": {"version": "2.32.3"}},
    )
    adapter = PyPIAdapter(HttpClient(), "https://pypi.org/pypi/{package_name}/json")
    result = adapter.get_latest_version("requests")
    assert isinstance(result, Ok)
    assert str(result.value) == "2.32.3"
```

## Coverage

Coverage is configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--cov=dependapy --cov-report=term-missing --cov-fail-under=80"
```

Excluded from coverage (wiring / external API code):

- `main.py`, `bootstrap.py`, `cli.py`
- VCS adapters (`github.py`, `offline.py`, `git_client.py`)
- Policy loader

## Import Contract Tests

```bash
just lint-imports
```

Verifies 3 contracts:

1. Domain does not import from Application, Infrastructure, or Presentation
2. Application does not import from Infrastructure or Presentation
3. Infrastructure does not import from Presentation
