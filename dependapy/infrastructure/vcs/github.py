"""
GitHub VCS Adapter — Implementiert VCSPort für GitHub.

Nutzt GitClient für lokale Git-Operationen und PyGithub für API-Calls.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from pathlib import Path

from dependapy.domain.errors import PRCreationError, VCSError
from dependapy.domain.result import Err, Ok, Result
from dependapy.domain.vcs_types import PRRequest, PRResult, RepoInfo
from dependapy.infrastructure.vcs.git_client import GitClient

logger = logging.getLogger("dependapy.infrastructure.vcs.github")


class GitHubVCSAdapter:
    """GitHub VCS Adapter.

    Implementiert das VCSPort Protocol für GitHub-Repositories.
    """

    def __init__(self, token: str, git_client: GitClient) -> None:
        self._token = token
        self._git = git_client

    def create_branch(self, repo_path: Path, branch_name: str) -> Result[None, VCSError]:
        """Erstellt einen neuen lokalen Branch."""
        return self._git.checkout(repo_path, branch_name, create=True)

    def commit_changes(
        self, repo_path: Path, files: Sequence[Path], message: str
    ) -> Result[str, VCSError]:
        """Staged Dateien und erstellt einen Commit."""
        match self._git.add(repo_path, files):
            case Err(e):
                return Err(e)
            case Ok(_):
                pass

        return self._git.commit(repo_path, message)

    def push_changes(self, repo_path: Path, branch: str) -> Result[None, VCSError]:
        """Pusht den Branch zum GitHub Remote."""
        return self._git.push(repo_path, branch=branch)

    def create_pull_request(self, request: PRRequest) -> Result[PRResult, VCSError]:
        """Erstellt einen Pull Request via GitHub API (PyGithub)."""
        try:
            from github import Github  # type: ignore[attr-defined]

            gh = Github(self._token)
            repo = gh.get_repo(f"{request.repo_owner}/{request.repo_name}")
            pr = repo.create_pull(
                title=request.title,
                body=request.body,
                head=request.head_branch,
                base=request.base_branch,
            )
            logger.info("PR erstellt: %s", pr.html_url)
            return Ok(
                PRResult(
                    url=pr.html_url,
                    number=pr.number,
                    provider="github",
                )
            )
        except ImportError:
            return Err(
                PRCreationError(
                    "PyGithub ist nicht installiert. Installiere mit: pip install dependapy[github]"
                )
            )
        except Exception as e:
            return Err(PRCreationError(f"GitHub PR-Erstellung fehlgeschlagen: {e}"))

    def get_repo_info(self, repo_path: Path) -> Result[RepoInfo, VCSError]:
        """Extrahiert Repository-Info aus der Git Remote URL."""
        match self._git.get_remote_url(repo_path):
            case Ok(url):
                owner, name = self._parse_github_url(url)
                if owner and name:
                    default_branch = self._get_default_branch(owner, name)
                    return Ok(
                        RepoInfo(
                            owner=owner,
                            name=name,
                            default_branch=default_branch,
                            provider="github",
                        )
                    )
                return Err(VCSError(f"Konnte GitHub-URL nicht parsen: {url}"))
            case Err(e):
                return Err(e)

    def _get_default_branch(self, owner: str, name: str) -> str:
        """Fragt den Default Branch via GitHub API ab. Fallback: 'main'."""
        try:
            from github import Github  # type: ignore[attr-defined]

            gh = Github(self._token)
            repo = gh.get_repo(f"{owner}/{name}")
            return repo.default_branch  # type: ignore[no-any-return]
        except Exception:
            logger.debug("Default Branch konnte nicht ermittelt werden, nutze 'main'")
            return "main"

    @staticmethod
    def _parse_github_url(url: str) -> tuple[str | None, str | None]:
        """Parst eine GitHub-URL in Owner und Repo-Name."""
        # HTTPS: https://github.com/owner/repo.git
        # SSH: git@github.com:owner/repo.git
        patterns = [
            r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)
        return None, None
