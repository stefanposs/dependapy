# Policy & Governance

Best practices for managing dependencies across your organization.

## Dependency Management Policy

### Why Have a Policy?

Without a policy, dependency updates become ad-hoc — some projects drift
months behind, others update aggressively and break. A governance policy
ensures consistent, predictable updates across all projects.

### Recommended Cadence

| Update Type | Frequency | Review Required |
|---|---|---|
| **Patch** (2.31.0 → 2.31.1) | Weekly (automated) | Auto-merge if tests pass |
| **Minor** (2.31.0 → 2.32.0) | Weekly | Team review |
| **Major** (2.x → 3.x) | On release | Senior engineer review + migration plan |

### Automation with dependapy

```yaml
# .github/workflows/dependapy.yml
name: Dependapy
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday
  workflow_dispatch:
```

### Python Version Support

dependapy checks that your `requires-python` constraint covers the
**three latest Python 3 minor versions** (currently 3.11, 3.12, 3.13).

This ensures:
- New language features and performance improvements are available
- Security patches are applied (end-of-life versions don't get patches)
- CI matrices stay manageable

## Team Workflow

### Pull Request Process

1. dependapy creates a PR with all dependency updates
2. CI runs full test suite against the updated versions
3. At least one team member reviews the changes
4. Focus review on:
    - **Major version bumps** — read the changelog
    - **New transitive dependencies** — security surface
    - **Python version constraint changes** — verify CI matrix
5. Merge when tests pass and review is approved

### Handling Breaking Changes

When a major version bump breaks your code:

1. Pin the dependency to the current major: `requests>=2.31,<3`
2. Create a separate issue for the migration
3. dependapy will continue updating within the pinned range
4. Migrate to the new major version when ready

## Best Practices

!!! tip "Pin with lower bounds"
    Use `>=2.31` instead of `==2.31.0`. This allows dependapy to update
    within compatible ranges while preventing downgrades.

!!! tip "Test matrix"
    Run your tests against all supported Python versions in CI. dependapy
    checks `requires-python` but can't verify runtime compatibility.

!!! tip "Review changelogs"
    For minor and major bumps, check the package's changelog before merging.
    dependapy reports the version change but doesn't analyze the changelog.

!!! warning "Don't ignore security updates"
    Patch updates often contain security fixes. Delaying them increases
    your attack surface. Set up auto-merge for patches when tests pass.
