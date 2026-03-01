# Result Pattern

dependapy uses an explicit `Result[T, E]` pattern for error handling.
Every operation that can fail returns `Ok[T] | Err[E]` instead of
raising exceptions.

## Why Result Instead of Exceptions?

| Approach | Problem |
|---|---|
| Return `None` on failure | Caller forgets to check — `NoneType` errors at runtime |
| Return sentinel values | `"FAILED"` strings leak into business logic |
| Raise exceptions | Control flow via exceptions is implicit and hard to trace |
| **Result pattern** | **Type-safe, explicit, composable** |

## Implementation

```python
# dependapy/domain/result.py

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

type Result[T, E] = Ok[T] | Err[E]
```

## Usage Patterns

### Pattern Matching

```python
result = registry.get_latest_version("requests")
match result:
    case Ok(version):
        print(f"Latest: {version}")
    case Err(error):
        logger.warning(f"Failed to fetch: {error}")
```

### isinstance Checks

```python
result = repo.load_project(path)
if isinstance(result, Err):
    return result  # propagate error
project = result.value
```

### In Use Cases

```python
class AnalyzeDependencies:
    def execute(self, root: Path) -> Result[list[AnalysisResult], str]:
        files_result = self.repo.find_project_files(root)
        if isinstance(files_result, Err):
            return files_result

        results = []
        for path in files_result.value:
            project_result = self.repo.load_project(path)
            if isinstance(project_result, Err):
                logger.warning(f"Skipping {path}: {project_result.error}")
                continue
            # ... analyze project
        return Ok(results)
```

## Rules

1. **Never raise exceptions for expected failures** — use `Err(message)`
2. **Domain ports return `Result`** — callers always handle both paths
3. **Narrowed exceptions in adapters** — catch specific exceptions
   (`OSError`, `ValueError`, `KeyError`) and convert to `Err`
4. **No bare `except Exception:`** — every catch is narrowed to specific types

## Benefits

- **Explicit error paths** — every caller sees the `Result` type signature
- **No silent failures** — `Err` values propagate naturally
- **Composable** — chain operations with early returns on `Err`
- **Testable** — assert `isinstance(result, Ok)` or `isinstance(result, Err)`
- **Type-safe** — pyright/mypy catch missing `Err` handling

## When Exceptions Are Still Used

Exceptions are reserved for **programmer errors** — bugs that should crash:

- `StateTransitionError` — calling `approve()` on an already-applied plan
- `AssertionError` — invariant violations in domain logic
- `TypeError` — wrong argument types

These are not caught or converted to `Result` because they indicate bugs,
not expected operational failures.
