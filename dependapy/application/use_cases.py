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
from dependapy.domain.models import Dependency, Project
from dependapy.domain.policy import Policy
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


def _update_type_allowed(dep: Dependency, policy: Policy) -> bool:
    """Prüft ob der Update-Typ einer Dependency durch die Policy erlaubt ist."""
    ut = dep.update_type()
    if ut is None:
        return True
    return ut.value in policy.allowed_update_types(dep.spec.name)


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

    def execute(
        self, project_path: Path, *, policy: Policy | None = None
    ) -> Result[list[AnalysisResult], str]:
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
                    self._enrich_with_latest_versions(project, policy=policy)
                    outdated = project.get_outdated()

                    # Policy-Filter: Ignorierte Packages und unerlaubte Update-Typen
                    if policy:
                        outdated = [
                            d
                            for d in outdated
                            if not policy.is_ignored(d.spec.name)
                            and _update_type_allowed(d, policy)
                        ]

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

    def _enrich_with_latest_versions(
        self, project: Project, *, policy: Policy | None = None
    ) -> None:
        """Reichert jede Dependency mit der neuesten Version an."""
        # Ignorierte Packages nicht abfragen — spart HTTP-Calls
        names = [
            dep.spec.name
            for dep in project.dependencies
            if not (policy and policy.is_ignored(dep.spec.name))
        ]
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
    """Use Case: Reicht Änderungen via VCS ein (PR oder Patch).

    Unterstützt:
    - Einzelner Sammel-PR (Legacy)
    - Per-Projekt PRs mit max_prs Limit
    - CODEOWNERS-basierte Reviewer-Zuweisung
    """

    def __init__(self, vcs: VCSPort) -> None:
        self._vcs = vcs

    def execute(
        self,
        repo_path: Path,
        updated_files: Sequence[Path],
        *,
        branch_name: str = "dependapy/dependency-updates",
        base_branch: str = "main",
        reviewers: list[str] | None = None,
        policy: Policy | None = None,
    ) -> Result[SubmitResult, str]:
        """Erstellt Branch, Commit, Push und PR."""
        # 1. Branch erstellen
        match self._vcs.create_branch(repo_path, branch_name):
            case Err(error):
                return Err(f"Branch-Erstellung fehlgeschlagen: {error}")
            case Ok(_):
                pass

        # 2. Commit — Message aus Policy oder Default
        if policy:
            commit_msg = policy.format_commit_message(
                "dependapy", "update dependencies and python version"
            )
        else:
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

        # 4. PR erstellen — Merge Policy Reviewers + CODEOWNERS Reviewers
        merged_reviewers = self._merge_reviewers(reviewers, policy)
        labels = list(policy.labels) if policy and policy.labels else None
        auto_merge = policy.auto_merge if policy else False

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
                    reviewers=merged_reviewers,
                    labels=labels,
                    auto_merge=auto_merge,
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

    @staticmethod
    def _merge_reviewers(
        codeowner_reviewers: list[str] | None, policy: Policy | None
    ) -> list[str] | None:
        """Kombiniert CODEOWNERS-Reviewer mit Policy-Reviewern."""
        merged: set[str] = set()
        if codeowner_reviewers:
            merged.update(codeowner_reviewers)
        if policy and policy.reviewers:
            merged.update(policy.reviewers)
        return sorted(merged) if merged else None

    def execute_per_project(
        self,
        repo_path: Path,
        analysis_results: list[AnalysisResult],
        updated_files_by_project: dict[Path, list[Path]],
        *,
        base_branch: str = "main",
        branch_prefix: str = "dependapy/",
        max_prs: int = 10,
        reviewers_by_file: dict[str, list[str]] | None = None,
        policy: Policy | None = None,
    ) -> list[Result[SubmitResult, str]]:
        """Erstellt separate PRs per Projekt oder Gruppe mit max_prs Limit.

        Wenn die Policy Gruppen definiert, werden Dependencies aus
        verschiedenen Projekten in einem gemeinsamen PR zusammengefasst.
        Ungrouped Dependencies erhalten weiterhin per-Projekt PRs.

        Args:
            repo_path: Root des Repositories.
            analysis_results: Analyse-Ergebnisse pro Projekt.
            updated_files_by_project: Mapping Projekt-Pfad → aktualisierte Dateien.
            base_branch: Basis-Branch für PRs.
            branch_prefix: Prefix für Branch-Namen.
            max_prs: Maximale Anzahl PRs (default: 10).
            reviewers_by_file: Mapping Dateipfad → Reviewer-Liste (aus CODEOWNERS).
            policy: Optionale Policy mit Gruppendefinitionen.

        Returns:
            Liste von Results (ein Eintrag pro erstelltem PR).
        """
        # Gruppierte PRs wenn Policy Gruppen definiert
        if policy and policy.groups:
            return self._execute_grouped(
                repo_path=repo_path,
                analysis_results=analysis_results,
                updated_files_by_project=updated_files_by_project,
                base_branch=base_branch,
                branch_prefix=branch_prefix,
                max_prs=max_prs,
                reviewers_by_file=reviewers_by_file,
                policy=policy,
            )

        return self._execute_per_project_simple(
            repo_path=repo_path,
            analysis_results=analysis_results,
            updated_files_by_project=updated_files_by_project,
            base_branch=base_branch,
            branch_prefix=branch_prefix,
            max_prs=max_prs,
            reviewers_by_file=reviewers_by_file,
            policy=policy,
        )

    def _execute_grouped(
        self,
        repo_path: Path,
        analysis_results: list[AnalysisResult],
        updated_files_by_project: dict[Path, list[Path]],
        *,
        base_branch: str,
        branch_prefix: str,
        max_prs: int,
        reviewers_by_file: dict[str, list[str]] | None,
        policy: Policy,
    ) -> list[Result[SubmitResult, str]]:
        """Erstellt PRs nach Dependency-Gruppen aus der Policy.

        Sammelt alle aktualisierten Dateien, deren Projekte Dependencies
        in derselben Gruppe haben. Projekte ohne Gruppen-Match bekommen
        weiterhin individuelle PRs.
        """
        # 1. Sammle alle Dateien pro Gruppe + ungrouped
        group_files: dict[str, set[Path]] = {}
        ungrouped_projects: list[AnalysisResult] = []

        for analysis in analysis_results:
            if analysis.outdated_count == 0:
                continue

            project_files = updated_files_by_project.get(analysis.project.path, [])
            if not project_files:
                continue

            # Prüfe ob irgendeine outdated dep zu einer Gruppe gehört
            matched_groups: set[str] = set()
            for dep in analysis.project.get_outdated():
                group = policy.find_group(dep.spec.name)
                if group:
                    matched_groups.add(group.name)

            if matched_groups:
                for group_name in matched_groups:
                    group_files.setdefault(group_name, set()).update(project_files)
            else:
                ungrouped_projects.append(analysis)

        # 2. PRs erstellen: erst Gruppen, dann ungrouped
        results: list[Result[SubmitResult, str]] = []
        pr_count = 0

        for group_name, files in sorted(group_files.items()):
            if pr_count >= max_prs:
                logger.warning("Max PRs erreicht (%d). Überspringe Gruppe: %s", max_prs, group_name)
                break

            reviewers = self._collect_reviewers(list(files), repo_path, reviewers_by_file)
            branch_name = f"{branch_prefix}group-{group_name.lower()}"

            result = self.execute(
                repo_path=repo_path,
                updated_files=list(files),
                branch_name=branch_name,
                base_branch=base_branch,
                reviewers=reviewers,
                policy=policy,
            )
            results.append(result)

            match result:
                case Ok(_):
                    pr_count += 1
                    logger.info("Gruppen-PR erstellt für: %s", group_name)
                case Err(error):
                    logger.error("Gruppen-PR für %s fehlgeschlagen: %s", group_name, error)

        # 3. Ungrouped als per-Projekt PRs
        ungrouped_files = {
            a.project.path: updated_files_by_project.get(a.project.path, [])
            for a in ungrouped_projects
        }
        if ungrouped_files:
            remaining = self._execute_per_project_simple(
                repo_path=repo_path,
                analysis_results=ungrouped_projects,
                updated_files_by_project=ungrouped_files,
                base_branch=base_branch,
                branch_prefix=branch_prefix,
                max_prs=max_prs - pr_count,
                reviewers_by_file=reviewers_by_file,
                policy=policy,
            )
            results.extend(remaining)

        logger.info("PRs erstellt: %d (max: %d)", pr_count, max_prs)
        return results

    @staticmethod
    def _collect_reviewers(
        files: list[Path],
        repo_path: Path,
        reviewers_by_file: dict[str, list[str]] | None,
    ) -> list[str] | None:
        """Sammelt Reviewer aus CODEOWNERS für eine Liste von Dateien."""
        if not reviewers_by_file:
            return None
        all_reviewers: set[str] = set()
        for f in files:
            rel_path = str(f.relative_to(repo_path))
            all_reviewers.update(reviewers_by_file.get(rel_path, []))
        return sorted(all_reviewers) if all_reviewers else None

    def _execute_per_project_simple(
        self,
        repo_path: Path,
        analysis_results: list[AnalysisResult],
        updated_files_by_project: dict[Path, list[Path]],
        *,
        base_branch: str = "main",
        branch_prefix: str = "dependapy/",
        max_prs: int = 10,
        reviewers_by_file: dict[str, list[str]] | None = None,
        policy: Policy | None = None,
    ) -> list[Result[SubmitResult, str]]:
        results: list[Result[SubmitResult, str]] = []
        pr_count = 0

        for analysis in analysis_results:
            if pr_count >= max_prs:
                logger.warning(
                    "Max PRs erreicht (%d). Überspringe: %s",
                    max_prs,
                    analysis.project.name,
                )
                break

            if analysis.outdated_count == 0:
                continue

            project_files = updated_files_by_project.get(analysis.project.path, [])
            if not project_files:
                continue

            # Reviewer für die Dateien dieses Projekts ermitteln
            reviewers: list[str] | None = None
            if reviewers_by_file:
                all_reviewers: set[str] = set()
                for f in project_files:
                    rel_path = str(f.relative_to(repo_path))
                    all_reviewers.update(reviewers_by_file.get(rel_path, []))
                if all_reviewers:
                    reviewers = sorted(all_reviewers)

            # Branch-Name pro Projekt
            safe_name = analysis.project.name.replace("/", "-").replace(" ", "-").lower()
            branch_name = f"{branch_prefix}update-{safe_name}"

            result = self.execute(
                repo_path=repo_path,
                updated_files=project_files,
                branch_name=branch_name,
                base_branch=base_branch,
                reviewers=reviewers,
                policy=policy,
            )
            results.append(result)

            match result:
                case Ok(_):
                    pr_count += 1
                case Err(error):
                    logger.error(
                        "PR für %s fehlgeschlagen: %s",
                        analysis.project.name,
                        error,
                    )

        logger.info("PRs erstellt: %d/%d (max: %d)", pr_count, len(analysis_results), max_prs)
        return results
