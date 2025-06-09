# Dependency Management Policy

This policy describes how we maintain our Python dependencies up-to-date using dependapy.

## Overview

- We use `dependapy` as an alternative to Dependabot
- Dependencies are automatically checked once a week
- Updates are proposed as pull requests
- We use `uv` as our modern package manager

## Automatic Updates

The `dependapy` process runs every Sunday at 02:00 UTC and:

1. Scans the repository for `pyproject.toml` files
2. Identifies outdated dependencies and Python version requirements
3. Creates a pull request with all necessary changes

## Handling Pull Requests

When a dependapy pull request is created:

1. The PR should be reviewed by at least one team member
2. Tests should pass successfully
3. After approval, the PR can be merged

## Manual Usage

To run dependapy manually (e.g. for urgent updates):

```bash
# Trigger GitHub Actions
gh workflow run dependapy.yml

# Or run locally
export GITHUB_TOKEN=your_token
python -m dependapy.main
```

## Best Practices

1. **Pinning**: Essential dependencies should be specified with `>=` and a minimum version
2. **Python versions**: We support the three latest Python 3 minor versions
3. **Review**: Dependency updates should be carefully reviewed, especially for major version changes

## Integration with uv

We recommend using `uv` for local development environments:

```bash
# uv installieren
curl -LsSf https://astral.sh/uv/install.sh | sh

# Projekt-Abhängigkeiten installieren
uv pip install -e .
```
