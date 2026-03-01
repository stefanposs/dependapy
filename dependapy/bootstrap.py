"""
Composition Root — Verdrahtet alle Abhängigkeiten.

Dies ist der einzige Ort, der alle konkreten Implementierungen kennt.
Alle anderen Module arbeiten nur mit abstrakten Ports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from dependapy.application.config import AppConfig, VCSProvider
from dependapy.application.use_cases import AnalyzeDependencies, ApplyUpdates, SubmitChanges
from dependapy.domain.errors import ConfigurationError
from dependapy.domain.ports import (
    PackageRegistry,
    ProjectRepository,
    PythonVersionRegistry,
    VCSPort,
)
from dependapy.infrastructure.adapters.endoflife import EndOfLifeAdapter
from dependapy.infrastructure.adapters.filesystem import FileSystemProjectRepository
from dependapy.infrastructure.adapters.pypi import PyPIAdapter
from dependapy.infrastructure.http import HttpClient
from dependapy.infrastructure.vcs.git_client import GitClient
from dependapy.infrastructure.vcs.github import GitHubVCSAdapter
from dependapy.infrastructure.vcs.offline import OfflinePatchAdapter

logger = logging.getLogger("dependapy.bootstrap")


@runtime_checkable
class Closable(Protocol):
    """Protokoll für Ressourcen, die geschlossen werden können."""

    def close(self) -> None: ...


@dataclass
class Application:
    """Container für alle Use Cases. Erstellt via bootstrap()."""

    analyze: AnalyzeDependencies
    apply: ApplyUpdates
    submit: SubmitChanges
    config: AppConfig
    _closables: list[Closable] = field(default_factory=list, repr=False)

    def close(self) -> None:
        """Gibt alle Ressourcen frei (ThreadPools, HTTP-Sessions)."""
        for resource in self._closables:
            try:
                resource.close()
            except Exception:
                logger.warning(
                    "Fehler beim Schließen von %s", type(resource).__name__, exc_info=True
                )

    def __enter__(self) -> Application:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def bootstrap(config: AppConfig | None = None) -> Application:
    """Composition Root — verdrahtet alle Abhängigkeiten.

    Args:
        config: Konfiguration. Wird aus Umgebungsvariablen geladen wenn None.

    Returns:
        Application mit allen verdrahteten Use Cases.
    """
    if config is None:
        config = AppConfig.from_env()

    # HTTP Client
    http = HttpClient(timeout=config.api_timeout, max_retries=3)

    # Adapters
    registry: PackageRegistry = PyPIAdapter(
        http_client=http,
        base_url=config.pypi_base_url,
    )
    python_reg: PythonVersionRegistry = EndOfLifeAdapter(
        http_client=http,
        api_url=config.python_eol_api_url,
        num_versions=config.num_latest_python_versions,
    )
    project_repo: ProjectRepository = FileSystemProjectRepository()
    vcs: VCSPort = _create_vcs(config)

    # Use Cases
    return Application(
        analyze=AnalyzeDependencies(
            registry=registry,
            project_repo=project_repo,
            python_registry=python_reg,
        ),
        apply=ApplyUpdates(project_repo=project_repo),
        submit=SubmitChanges(vcs=vcs),
        config=config,
        _closables=[registry, http],
    )


def _create_vcs(config: AppConfig) -> VCSPort:
    """Erstellt den passenden VCS-Adapter basierend auf der Konfiguration."""
    git = GitClient()

    match config.vcs_provider:
        case VCSProvider.GITHUB:
            if not config.vcs_token:
                raise ConfigurationError(
                    "DEPENDAPY_VCS_TOKEN ist pflicht wenn vcs_provider='github' ist."
                    " Setze die Variable oder verwende --provider offline."
                )
            return GitHubVCSAdapter(
                token=config.vcs_token,
                git_client=git,
            )
        case VCSProvider.OFFLINE:
            return OfflinePatchAdapter(git_client=git)
        case _:
            raise ConfigurationError(f"Unbekannter VCS Provider: {config.vcs_provider!r}")
