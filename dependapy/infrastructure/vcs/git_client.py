"""
Git Client — Subprocess-Wrapper für Git-Operationen.

Zentralisiert alle Git-Subprocess-Aufrufe mit Result-basierter Fehlerbehandlung.
Wird von VCS-Adaptern (GitHub, Offline) verwendet.
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Sequence
from pathlib import Path

from dependapy.domain.errors import BranchExistsError, VCSError
from dependapy.domain.result import Err, Ok, Result

logger = logging.getLogger("dependapy.infrastructure.vcs.git_client")


class GitClient:
    """Low-Level Git-Client via subprocess."""

    def run(
        self,
        args: list[str],
        cwd: Path | None = None,
        *,
        check: bool = True,
    ) -> Result[str, VCSError]:
        """Führt einen Git-Befehl aus und gibt stdout zurück."""
        cmd = ["git", *args]
        logger.debug("Git: %s (cwd=%s)", " ".join(cmd), cwd)

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=check,
                timeout=60,
            )
            return Ok(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else str(e)
            logger.warning("Git-Fehler: %s", stderr)
            return Err(VCSError(f"Git-Fehler: {stderr}"))
        except subprocess.TimeoutExpired:
            return Err(VCSError("Git-Timeout nach 60 Sekunden"))
        except FileNotFoundError:
            return Err(VCSError("Git ist nicht installiert"))

    def get_current_branch(self, repo_path: Path) -> Result[str, VCSError]:
        """Gibt den aktuellen Branch-Namen zurück."""
        return self.run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)

    def checkout(
        self,
        repo_path: Path,
        branch: str,
        *,
        create: bool = False,
    ) -> Result[None, VCSError]:
        """Wechselt zu einem Branch, optional mit Erstellung."""
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(branch)

        match self.run(args, cwd=repo_path):
            case Ok(_):
                return Ok(None)
            case Err(e) if "already exists" in str(e):
                return Err(BranchExistsError(f"Branch '{branch}' existiert bereits"))
            case Err(e):
                return Err(e)

    def add(self, repo_path: Path, files: Sequence[Path] | None = None) -> Result[None, VCSError]:
        """Staged Dateien für den nächsten Commit."""
        if files:
            args = ["add", *[str(f) for f in files]]
        else:
            args = ["add", "-A"]

        match self.run(args, cwd=repo_path):
            case Ok(_):
                return Ok(None)
            case Err(e):
                return Err(e)

    def commit(self, repo_path: Path, message: str) -> Result[str, VCSError]:
        """Erstellt einen Commit und gibt den Commit-Hash zurück."""
        match self.run(["commit", "-m", message], cwd=repo_path):
            case Ok(_):
                return self.run(["rev-parse", "HEAD"], cwd=repo_path)
            case Err(e):
                return Err(e)

    def push(
        self,
        repo_path: Path,
        remote: str = "origin",
        branch: str | None = None,
        *,
        force: bool = False,
    ) -> Result[None, VCSError]:
        """Pusht zum Remote."""
        args = ["push", remote]
        if branch:
            args.append(branch)
        if force:
            args.append("--force")

        match self.run(args, cwd=repo_path):
            case Ok(_):
                return Ok(None)
            case Err(e):
                return Err(e)

    def get_remote_url(self, repo_path: Path, remote: str = "origin") -> Result[str, VCSError]:
        """Gibt die Remote-URL zurück."""
        return self.run(["remote", "get-url", remote], cwd=repo_path)

    def format_patch(
        self,
        repo_path: Path,
        output_dir: Path,
        *,
        commits: int = 1,
    ) -> Result[str, VCSError]:
        """Erstellt Patch-Dateien für die letzten N Commits."""
        return self.run(
            ["format-patch", f"-{commits}", f"--output-directory={output_dir}"],
            cwd=repo_path,
        )
