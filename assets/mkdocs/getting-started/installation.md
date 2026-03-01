# Installation

## Requirements

- **Python 3.12+** (3.13 recommended)
- **pip** or **uv** package manager

## Install from PyPI

=== "uv (recommended)"

    ```bash
    uv add dependapy
    ```

=== "pip"

    ```bash
    pip install dependapy
    ```

## Install from Source

For development or to run the latest version:

```bash
git clone https://github.com/stefanposs/dependapy.git
cd dependapy

# Install with dev dependencies
uv pip install -e ".[dev]"
```

## Verify Installation

```bash
dependapy --help
```

You should see the CLI help output:

```
usage: dependapy [-h] [--repo-path PATH] [--token TOKEN]
                 [--provider {github,offline}] [--base-branch BRANCH]
                 [--no-pr] [--offline-pr] [--patch-output PATH]
                 [--dry-run] [--log-level LEVEL]

Analyze and update Python dependencies
```

## Optional: GitHub Integration

To create pull requests automatically, you need a GitHub token:

```bash
export DEPENDAPY_VCS_TOKEN=your_github_token
```

!!! tip "Offline mode works without any token"
    If you don't have a GitHub token, use `--provider offline` to generate
    Git patches instead. See [Offline Mode](../guide/offline-mode.md).

## Next Steps

- [Quick Start](quick-start.md) — Run your first analysis
- [Configuration](configuration.md) — Customize behavior via environment variables
- [GitHub Action](github-action.md) — Automate with CI/CD
