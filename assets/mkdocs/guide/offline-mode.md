# Offline Mode

dependapy works fully offline — no GitHub token, no API access required.

## When to Use Offline Mode

- **Air-gapped environments** — CI runners without internet access to GitHub API
- **Self-hosted runners** — behind firewalls that block GitHub API endpoints
- **Local development** — review changes before pushing
- **Auditing** — generate a patch for compliance review before applying

## Usage

### Generate a Patch

```bash
dependapy --provider offline --patch-output updates.patch
```

This creates a `git format-patch` file with all dependency updates.

### Apply the Patch

On a machine with repository access:

```bash
git apply updates.patch
git checkout -b dependapy/updates
git commit -am "Apply dependapy updates"
git push origin dependapy/updates
# Then create a PR via the GitHub UI
```

### Dry Run (No Output File)

```bash
dependapy --provider offline --dry-run
```

See what would change without generating any files.

## How It Works

The `OfflinePatchAdapter` implements the same `VCSPort` protocol as the
GitHub adapter. Instead of calling the GitHub API, it:

1. Creates a temporary Git branch locally
2. Commits the changes
3. Runs `git format-patch` to generate a portable patch file
4. Cleans up the temporary branch

```mermaid
graph LR
    A["dependapy --provider offline"] --> B["OfflinePatchAdapter"]
    B --> C["Create temp branch"]
    C --> D["Commit changes"]
    D --> E["git format-patch"]
    E --> F["updates.patch"]
```

## CI Integration

For CI runners that can only upload artifacts:

```yaml
- name: Generate patch
  run: dependapy --provider offline --patch-output updates.patch

- name: Upload patch
  uses: actions/upload-artifact@v4
  with:
    name: dependency-updates
    path: updates.patch
    retention-days: 7
```

!!! info "Default provider"
    dependapy defaults to `offline` mode. You only need to set
    `--provider github` or `DEPENDAPY_VCS_PROVIDER=github` when you
    want to create PRs via the API.
