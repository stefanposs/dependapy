"""
Use Cases — Application Layer Orchestrierung.

Jeder Use Case koordiniert Domain-Objekte und Ports.
Keine Geschäftslogik hier, nur Orchestrierung.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from dependapy.application.dtos import AnalysisResult, SubmitResult, UpdateResult
from dependapy.domain.models import Project
from dependapy.domain.ports import (
    PackageRegistry,
    ProjectRepository,
    PythonVersionRegistry,
    VCSPort,
)
from dependapy.domain.result import Err, Ok, Result
from dependapy.domain.value_objects import Version
from dependapy.domain.vcs_types import PRRequest

logger = logging.getLogger("dependapy.application")


class AnalyzeDependencies:
    """Use Case: Analysiert alle Dependencies eines Projekts.

    1. Findet alle pyproject.toml-Dateien
    2. Lädt Projekte
    3. Fragt neueste Versionen von PyPI ab
    4. Prüft Python-Version-Constraints
    """

    def __init__(
        self,
        registry: PackageRegistry,
        project_repo: ProjectRepository,
        python_registry: PythonVersionRegistry,
    ) -> None:
        self._registry = registry
        self._project_repo = project_repo
        self._python_registry = python_registry

    def execute(self, project_path: Path) -> Result[list[AnalysisResult], str]:
        """Führt die Dependency-Analyse durch."""
        match self._project_repo.find_project_files(project_path):
            case Err(error):
                return Err(f"Fehler beim Suchen nach pyproject.toml: {error}")
            case Ok(found_files) if not found_files:
                return Err(f"Keine pyproject.toml gefunden in {project_path}")
            case Ok(found_files):
                project_files = found_files

        # Python EOL-Versionen vorab laden
        supported_pythons: list[Version] = []
        match self._python_registry.get_supported_versions():
            case Ok(versions):
                supported_pythons = versions
            case Err(py_error):
                logger.warning("Python-Versionen nicht abrufbar: %s", py_error)

        results: list[AnalysisResult] = []

        for file_path in project_files:
            match self._project_repo.load_project(file_path):
                case Ok(project):
                    self._enrich_with_latest_versions(project)
                    outdated = project.get_outdated()
                    project.mark_analyzed()

                    # Python EOL-Check: Erfüllt mindestens eine supported
                    # Python-Version den Constraint des Projekts?
                    python_outdated = False
                    if project.python_constraint and supported_pythons:
                        python_outdated = not any(
                            project.python_constraint.is_satisfied_by(v) for v in supported_pythons
                        )

                    for dep in outdated:
                        logger.info(
                            "Outdated: %s %s → %s (%s)",
                            dep.spec.name,
                            dep.current_version,
                            dep.latest_version,
                            dep.update_type(),
                        )

                    results.append(
                        AnalysisResult(
                            project=project,
                            outdated_count=len(outdated),
                            total_count=len(project.dependencies),
                            python_outdated=python_outdated,
                        )
                    )

                case Err(error):
                    logger.warning("Projekt nicht ladbar: %s — %s", file_path, error)

        return Ok(results)

    def _enrich_with_latest_versions(self, project: Project) -> None:
        """Reichert jede Dependency mit der neuesten Version an."""
        names = [dep.spec.name for dep in project.dependencies]
        batch_results = self._registry.get_latest_versions_batch(names)

        for i, dep in enumerate(project.dependencies):
            result = batch_results.get(dep.spec.name)
            if result is not None:
                match result:
                    case Ok(latest):
                        project.replace_dependency(i, dep.with_latest_version(latest))
                    case Err(error):
                        logger.warning(
                            "Version für %s nicht abrufbar: %s",
                            dep.spec.name,
                            error,
                        )


class ApplyUpdates:
    """Use Case: Wendet Updates auf pyproject.toml-Dateien an."""

    def __init__(self, project_repo: ProjectRepository) -> None:
        self._project_repo = project_repo

    def execute(self, analysis_results: list[AnalysisResult]) -> Result[UpdateResult, str]:
        """Aktualisiert alle Projekte mit veralteten Dependencies."""
        updated_files: list[Path] = []
        error_count = 0

        for result in analysis_results:
            if result.outdated_count == 0:
                continue

            match self._project_repo.save_project(result.project):
                case Ok(_):
                    updated_files.append(result.project.path)
                    logger.info("Updated: %s", result.project.path)
                case Err(error):
                    logger.error("Update fehlgeschlagen für %s: %s", result.project.path, error)
                    error_count += 1

        return Ok(
            UpdateResult(
                updated_files=tuple(updated_files),
                error_count=error_count,
            )
        )


class SubmitChanges:
    """Use Case: Reicht Änderungen via VCS ein (PR oder Patch)."""

    def __init__(self, vcs: VCSPort) -> None:
        self._vcs = vcs

    def execute(
        self,
        repo_path: Path,
        updated_files: Sequence[Path],
        *,
        branch_name: str = "dependapy/dependency-updates",
        base_branch: str = "main",
    ) -> Result[SubmitResult, str]:
        """Erstellt Branch, Commit, Push und PR."""
        # 1. Branch erstellen
        match self._vcs.create_branch(repo_path, branch_name):
            case Err(error):
                return Err(f"Branch-Erstellung fehlgeschlagen: {error}")
            case Ok(_):
                pass

        # 2. Commit
        commit_msg = "chore(dependapy): update dependencies and python version"
        match self._vcs.commit_changes(repo_path, updated_files, commit_msg):
            case Err(error):
                return Err(f"Commit fehlgeschlagen: {error}")
            case Ok(_):
                pass

        # 3. Push
        match self._vcs.push_changes(repo_path, branch_name):
            case Err(error):
                return Err(f"Push fehlgeschlagen: {error}")
            case Ok(_):
                pass

        # 4. PR erstellen
        match self._vcs.get_repo_info(repo_path):
            case Err(error):
                return Err(f"Repo-Info nicht abrufbar: {error}")
            case Ok(info):
                pr_request = PRRequest(
                    repo_owner=info.owner,
                    repo_name=info.name,
                    head_branch=branch_name,
                    base_branch=base_branch,
                    title="chore(deps): update dependencies",
                    body=(
                        "This PR was automatically created by dependapy.\n\n"
                        "It updates dependencies to their latest versions."
                    ),
                )
                match self._vcs.create_pull_request(pr_request):
                    case Ok(pr_result):
                        logger.info("PR erstellt: %s", pr_result.url)
                        return Ok(
                            SubmitResult(
                                url=pr_result.url,
                                provider=pr_result.provider,
                                files_changed=len(updated_files),
                            )
                        )
                    case Err(pr_error):
                        return Err(f"PR-Erstellung fehlgeschlagen: {pr_error}")
