"""
Test Fakes — In-memory Implementierungen aller Ports für Tests.

Fakes sind einfache, vorhersehbare Implementierungen, die das Port-Protocol
erfüllen, ohne externe Abhängigkeiten zu benötigen.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from dependapy.domain.errors import (
    PackageNotFoundError,
    ProjectError,
    ProjectWriteError,
    RegistryError,
    VCSError,
)
from dependapy.domain.models import Project
from dependapy.domain.result import Err, Ok, Result
from dependapy.domain.value_objects import Version
from dependapy.domain.vcs_types import PRRequest, PRResult, RepoInfo


class FakePackageRegistry:
    """Fake PackageRegistry für Tests — gibt konfigurierbare Versionen zurück."""

    def __init__(
        self,
        versions: dict[str, str] | None = None,
        fail_packages: set[str] | None = None,
    ) -> None:
        self._versions = versions or {}
        self._fail_packages = fail_packages or set()
        self.call_count: int = 0
        self.last_queried: str | None = None

    def get_latest_version(self, package_name: str) -> Result[Version, RegistryError]:
        self.call_count += 1
        self.last_queried = package_name
        if package_name in self._fail_packages:
            return Err(PackageNotFoundError(f"Package {package_name} not found"))
        if package_name in self._versions:
            return Ok(Version.from_string(self._versions[package_name]))
        return Err(PackageNotFoundError(f"Package {package_name} not found"))

    def get_latest_versions_batch(
        self, package_names: list[str]
    ) -> dict[str, Result[Version, RegistryError]]:
        return {name: self.get_latest_version(name) for name in package_names}


class FakePythonVersionRegistry:
    """Fake PythonVersionRegistry — gibt konfigurierbare Versionen zurück."""

    def __init__(self, versions: list[str] | None = None) -> None:
        self._versions = versions or ["3.13", "3.12", "3.11"]

    def get_supported_versions(self) -> Result[list[Version], RegistryError]:
        return Ok([Version.from_string(v) for v in self._versions])


class FakeProjectRepository:
    """Fake ProjectRepository — speichert Projekte im Memory."""

    def __init__(self) -> None:
        self._projects: dict[Path, Project] = {}
        self._save_errors: set[Path] = set()
        self._project_files: list[Path] = []

    def add_project(self, project: Project) -> None:
        """Fügt ein Projekt für Tests hinzu."""
        self._projects[project.path] = project
        if project.path not in self._project_files:
            self._project_files.append(project.path)

    def add_save_error(self, path: Path) -> None:
        """Konfiguriert, dass save_project für diesen Pfad fails."""
        self._save_errors.add(path)

    def load_project(self, path: Path) -> Result[Project, ProjectError]:
        if path in self._projects:
            return Ok(self._projects[path])
        from dependapy.domain.errors import ProjectParseError

        return Err(ProjectParseError(f"Project not found: {path}"))

    def save_project(self, project: Project) -> Result[None, ProjectError]:
        if project.path in self._save_errors:
            return Err(ProjectWriteError(f"Write failed: {project.path}"))
        self._projects[project.path] = project
        return Ok(None)

    def find_project_files(self, root: Path) -> Result[list[Path], ProjectError]:
        return Ok(self._project_files)


class FakeVCSPort:
    """Fake VCSPort — für Tests des SubmitChanges Use Case."""

    def __init__(
        self,
        *,
        fail_on_branch: bool = False,
        fail_on_commit: bool = False,
        fail_on_push: bool = False,
        fail_on_pr: bool = False,
        pr_url: str = "https://github.com/test/repo/pull/1",
    ) -> None:
        self._fail_on_branch = fail_on_branch
        self._fail_on_commit = fail_on_commit
        self._fail_on_push = fail_on_push
        self._fail_on_pr = fail_on_pr
        self._pr_url = pr_url

        self.branches_created: list[str] = []
        self.commits_made: list[str] = []
        self.pushes_made: list[str] = []
        self.prs_created: list[PRRequest] = []

    def create_branch(self, repo_path: Path, branch_name: str) -> Result[None, VCSError]:
        if self._fail_on_branch:
            return Err(VCSError("Branch creation failed"))
        self.branches_created.append(branch_name)
        return Ok(None)

    def commit_changes(
        self, repo_path: Path, files: Sequence[Path], message: str
    ) -> Result[str, VCSError]:
        if self._fail_on_commit:
            return Err(VCSError("Commit failed"))
        self.commits_made.append(message)
        return Ok("abc1234")

    def push_changes(self, repo_path: Path, branch: str) -> Result[None, VCSError]:
        if self._fail_on_push:
            return Err(VCSError("Push failed"))
        self.pushes_made.append(branch)
        return Ok(None)

    def create_pull_request(self, request: PRRequest) -> Result[PRResult, VCSError]:
        if self._fail_on_pr:
            return Err(VCSError("PR creation failed"))
        self.prs_created.append(request)
        return Ok(PRResult(url=self._pr_url, number=1, provider="fake"))

    def get_repo_info(self, repo_path: Path) -> Result[RepoInfo, VCSError]:
        return Ok(RepoInfo(owner="test", name="repo", default_branch="main", provider="fake"))
