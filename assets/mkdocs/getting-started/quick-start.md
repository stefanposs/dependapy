# Quick Start

Get dependapy running in under 2 minutes.

## 1. Install

```bash
pip install dependapy
# or: uv add dependapy
```

## 2. Run a Dry Run

The safest way to start — see what would change without modifying anything:

```bash
cd your-python-project
dependapy --dry-run
```

**Example output:**

```
INFO  Scanning repository at /path/to/project
INFO  Found 1 pyproject.toml file(s)
INFO  Analyzing: my-project (3 dependencies, 2 dev dependencies)
INFO  requests: 2.31.0 → 2.32.3 (minor)
INFO  ruff: 0.4.0 → 0.11.13 (minor)
INFO  Python version: requires-python = ">=3.10" — 3.11, 3.12, 3.13 supported ✓
INFO  Dry run — no changes applied.
```

## 3. Apply Updates Locally

Update `pyproject.toml` files in place (without creating a PR):

```bash
dependapy --no-pr
```

This bumps version strings directly in your `pyproject.toml` files.

## 4. Create a Pull Request

With a GitHub token, dependapy creates a branch, commits, and opens a PR:

```bash
export DEPENDAPY_VCS_TOKEN=your_github_token
dependapy
```

Or use offline mode if you don't have API access:

```bash
dependapy --provider offline --patch-output updates.patch
```

## Command Line Reference

```
usage: dependapy [-h] [--repo-path PATH] [--token TOKEN]
                 [--provider {github,offline}] [--base-branch BRANCH]
                 [--no-pr] [--offline-pr] [--patch-output PATH]
                 [--dry-run] [--log-level LEVEL]
```

| Option | Description |
|---|---|
| `--repo-path PATH` | Path to the repository to scan (default: current directory) |
| `--token TOKEN` | VCS token (or set `DEPENDAPY_VCS_TOKEN`) |
| `--provider {github,offline}` | VCS provider (default: `offline`) |
| `--base-branch BRANCH` | Target branch for PRs (default: `main`) |
| `--no-pr` | Update files locally without creating a PR |
| `--offline-pr` | Legacy alias for `--provider offline` |
| `--patch-output PATH` | Patch file path (offline mode) |
| `--dry-run` | Report changes without making them |
| `--log-level LEVEL` | Logging level (default: `INFO`) |

## Next Steps

- [Configuration](configuration.md) — Fine-tune behavior via environment variables
- [Offline Mode](../guide/offline-mode.md) — Work without GitHub API access
- [GitHub Action](github-action.md) — Automate weekly runs
