# GitHub Action

Run dependapy automatically on a schedule to keep dependencies current.

## Basic Workflow

Create `.github/workflows/dependapy.yml`:

```yaml
name: Dependapy

on:
  schedule:
    - cron: '0 2 * * 0'  # Every Sunday at 02:00 UTC
  workflow_dispatch:       # Manual trigger

jobs:
  update-dependencies:
    name: Update Dependencies
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependapy
        run: pip install dependapy

      - name: Run dependapy
        env:
          DEPENDAPY_VCS_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DEPENDAPY_VCS_PROVIDER: github
        run: dependapy
```

## Advanced: Dry-Run + PR

Separate analysis from PR creation for better visibility:

```yaml
name: Dependapy (Advanced)

on:
  schedule:
    - cron: '0 2 * * 0'
  workflow_dispatch:

jobs:
  analyze:
    name: Analyze Dependencies
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install dependapy
      - name: Dry Run
        run: dependapy --dry-run

  update:
    name: Create Update PR
    needs: analyze
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install dependapy
      - name: Run dependapy
        env:
          DEPENDAPY_VCS_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DEPENDAPY_VCS_PROVIDER: github
        run: dependapy
```

## Offline Mode on CI

For runners without GitHub API access (e.g., self-hosted, air-gapped):

```yaml
- name: Generate patch
  run: dependapy --provider offline --patch-output updates.patch

- name: Upload patch as artifact
  uses: actions/upload-artifact@v4
  with:
    name: dependency-updates
    path: updates.patch
```

## Tips

!!! tip "Use `workflow_dispatch` for testing"
    Add `workflow_dispatch` to your triggers so you can manually run the
    workflow from the GitHub Actions tab during setup.

!!! tip "Pin the Python version"
    Always pin `python-version: '3.13'` (or your target) to ensure
    consistent behavior across runs.

!!! note "Permissions"
    The workflow needs `contents: write` and `pull-requests: write` to
    create branches and open PRs. `GITHUB_TOKEN` provides these
    automatically when the permissions are declared.
