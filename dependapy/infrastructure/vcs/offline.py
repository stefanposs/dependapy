"""
Offline Patch Adapter — Implementiert VCSPort für Offline-Patches.

Erstellt Git-Patches statt PRs. Nützlich für Organisationen die
keinen direkten API-Zugriff erlauben.
"""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Sequence
from pathlib import Path

from dependapy.domain.errors import VCSError
from dependapy.domain.result import Err, Ok, Result
from dependapy.domain.vcs_types import PRRequest, PRResult, RepoInfo
from dependapy.infrastructure.vcs.git_client import GitClient

logger = logging.getLogger("dependapy.infrastructure.vcs.offline")


class OfflinePatchAdapter:
    """Offline VCS Adapter — erstellt Git-Patches statt PRs.

    Implementiert das VCSPort Protocol.
    """

    def __init__(self, git_client: GitClient, output_dir: Path | None = None) -> None:
        self._git = git_client
        self._output_dir = output_dir or Path(tempfile.gettempdir()) / "dependapy-patches"

    def create_branch(self, repo_path: Path, branch_name: str) -> Result[None, VCSError]:
        """Erstellt einen lokalen Branch."""
        return self._git.checkout(repo_path, branch_name, create=True)

    def commit_changes(
        self, repo_path: Path, files: Sequence[Path], message: str
    ) -> Result[str, VCSError]:
        """Staged und committed Änderungen."""
        match self._git.add(repo_path, files):
            case Err(e):
                return Err(e)
            case Ok(_):
                pass
        return self._git.commit(repo_path, message)

    def push_changes(
        self,
        repo_path: Path,
        branch: str,  # noqa: ARG002
    ) -> Result[None, VCSError]:
        """Erstellt einen Patch statt zu pushen."""
        self._output_dir.mkdir(parents=True, exist_ok=True)

        match self._git.format_patch(repo_path, self._output_dir):
            case Ok(output):
                logger.info("Patch erstellt: %s", output)
                return Ok(None)
            case Err(e):
                return Err(e)

    def create_pull_request(
        self,
        request: PRRequest,  # noqa: ARG002
    ) -> Result[PRResult, VCSError]:
        """Gibt den Patch-Pfad als 'PR' zurück."""
        patch_path = str(self._output_dir)
        logger.info("Offline PR: Patches gespeichert in %s", patch_path)
        return Ok(
            PRResult(
                url=f"file://{patch_path}",
                number=0,
                provider="offline",
            )
        )

    def get_repo_info(self, repo_path: Path) -> Result[RepoInfo, VCSError]:
        """Gibt lokale Repository-Info zurück."""
        name = repo_path.name
        return Ok(
            RepoInfo(
                owner="local",
                name=name,
                default_branch="main",
                provider="offline",
            )
        )
