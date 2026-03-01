"""
Ports — Abstract Protocol Interfaces für die Domain.

Alle externen Abhängigkeiten werden über Ports abstrahiert.
Konkrete Implementierungen (Adapter) leben in infrastructure/.

Phase 1 definiert 4 Kern-Ports:
- PackageRegistry — PyPI, andere Registries
- ProjectRepository — pyproject.toml lesen/schreiben
- VCSPort — GitHub, GitLab, Offline-Patch
- PythonVersionRegistry — Python EOL-Daten
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from dependapy.domain.errors import (
    ProjectError,
    RegistryError,
    VCSError,
)
from dependapy.domain.models import Project
from dependapy.domain.result import Result
from dependapy.domain.value_objects import Version
from dependapy.domain.vcs_types import PRRequest, PRResult, RepoInfo


@runtime_checkable
class PackageRegistry(Protocol):
    """Port: Zugriff auf Package-Registries (PyPI, etc.)."""

    def get_latest_version(self, package_name: str) -> Result[Version, RegistryError]:
        """Gibt die neueste Version eines Packages zurück."""
        ...

    def get_latest_versions_batch(
        self, package_names: list[str]
    ) -> dict[str, Result[Version, RegistryError]]:
        """Gibt die neuesten Versionen für mehrere Packages zurück.

        Default: Sequentielle Abfrage. Adapter können parallele
        Implementierungen bereitstellen.
        """
        ...


@runtime_checkable
class ProjectRepository(Protocol):
    """Port: Lade und speichere Projekt-Daten aus/in pyproject.toml."""

    def load_project(self, path: Path) -> Result[Project, ProjectError]:
        """Lädt ein Projekt aus einer pyproject.toml-Datei."""
        ...

    def save_project(self, project: Project) -> Result[None, ProjectError]:
        """Speichert Änderungen an einem Projekt zurück in die Datei."""
        ...

    def find_project_files(self, root: Path) -> Result[list[Path], ProjectError]:
        """Findet alle pyproject.toml-Dateien in einem Verzeichnis (rekursiv)."""
        ...


@runtime_checkable
class VCSPort(Protocol):
    """Port: Version Control System Operationen.

    Abstraktion über GitHub, GitLab, Bitbucket, Offline-Patch.
    Jeder Adapter implementiert dieses Protocol.
    """

    def create_branch(self, repo_path: Path, branch_name: str) -> Result[None, VCSError]:
        """Erstellt einen neuen Branch."""
        ...

    def commit_changes(
        self, repo_path: Path, files: Sequence[Path], message: str
    ) -> Result[str, VCSError]:
        """Committet Dateien und gibt den Commit-Hash zurück."""
        ...

    def push_changes(self, repo_path: Path, branch: str) -> Result[None, VCSError]:
        """Pusht Changes zum Remote."""
        ...

    def create_pull_request(self, request: PRRequest) -> Result[PRResult, VCSError]:
        """Erstellt einen Pull Request / Merge Request."""
        ...

    def get_repo_info(self, repo_path: Path) -> Result[RepoInfo, VCSError]:
        """Gibt Repository-Metadaten zurück (Owner, Name, Default Branch)."""
        ...


@runtime_checkable
class PythonVersionRegistry(Protocol):
    """Port: Python-Versions-Informationen (EOL-Daten)."""

    def get_supported_versions(self) -> Result[list[Version], RegistryError]:
        """Gibt die aktuell unterstützten Python 3.x Versionen zurück."""
        ...
