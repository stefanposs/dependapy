# Configuration

dependapy reads configuration from **environment variables** (prefix `DEPENDAPY_`)
or a `.env` file in the project root.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DEPENDAPY_VCS_TOKEN` | — | GitHub / GitLab token for API access |
| `DEPENDAPY_VCS_PROVIDER` | `offline` | VCS provider: `github` or `offline` |
| `DEPENDAPY_VCS_BASE_BRANCH` | `main` | Target branch for pull requests |
| `DEPENDAPY_BRANCH_PREFIX` | `dependapy/` | Prefix for update branches |
| `DEPENDAPY_API_TIMEOUT` | `10` | HTTP timeout in seconds |
| `DEPENDAPY_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DEPENDAPY_PYPI_BASE_URL` | `https://pypi.org/pypi/{package_name}/json` | PyPI API endpoint |
| `DEPENDAPY_PYTHON_EOL_API_URL` | `https://endoflife.date/api/python.json` | Python EOL API endpoint |
| `DEPENDAPY_NUM_LATEST_PYTHON_VERSIONS` | `3` | Number of latest Python versions to validate |

## Example `.env` File

```bash
# .env
DEPENDAPY_VCS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
DEPENDAPY_VCS_PROVIDER=github
DEPENDAPY_VCS_BASE_BRANCH=main
DEPENDAPY_LOG_LEVEL=INFO
DEPENDAPY_API_TIMEOUT=15
```

## Configuration via `pydantic-settings`

Under the hood, dependapy uses [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
for configuration management. This gives you:

- **Type validation** — invalid values are caught at startup
- **Environment variable parsing** — automatic `DEPENDAPY_` prefix stripping
- **`.env` file support** — loads from `.env` if present
- **Default values** — sensible defaults for everything except the VCS token

### Programmatic Configuration

```python
from dependapy.application.config import AppConfig
from dependapy.bootstrap import bootstrap

config = AppConfig(
    vcs_token="ghp_xxx",
    vcs_provider="github",
    api_timeout=15,
)

app = bootstrap(config)
result = app.analyze.execute(Path("."))
```

## VCS Providers

### GitHub (`github`)

Requires `DEPENDAPY_VCS_TOKEN`. Creates branches, commits, and pull requests
via the GitHub API. Automatically detects the repository's default branch.

```bash
export DEPENDAPY_VCS_PROVIDER=github
export DEPENDAPY_VCS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

### Offline (`offline`)

No token required. Generates `git format-patch` files that can be applied
manually on a machine with repository access.

```bash
export DEPENDAPY_VCS_PROVIDER=offline
dependapy --patch-output updates.patch
```

!!! info "Default provider is `offline`"
    dependapy defaults to offline mode so it works on any machine
    without external API access — including air-gapped CI runners.
