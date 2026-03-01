"""Tests für dependapy.application.use_cases — AnalyzeDependencies, ApplyUpdates, SubmitChanges."""

from __future__ import annotations

from pathlib import Path

from dependapy.application.use_cases import AnalyzeDependencies, ApplyUpdates, SubmitChanges
from dependapy.domain.models import Project
from dependapy.domain.value_objects import ConstraintOperator, VersionConstraint
from tests.factories import make_dep, make_project, make_version
from tests.fakes import (
    FakePackageRegistry,
    FakeProjectRepository,
    FakePythonVersionRegistry,
    FakeVCSPort,
)


class TestAnalyzeDependencies:
    def test_returns_err_when_no_files_found(self) -> None:
        repo = FakeProjectRepository()  # no files added → find_project_files returns []
        use_case = AnalyzeDependencies(
            registry=FakePackageRegistry(),
            project_repo=repo,
            python_registry=FakePythonVersionRegistry(),
        )
        result = use_case.execute(Path("/nonexistent"))
        assert result.is_err()

    def test_returns_analysis_for_single_project(self, tmp_path: Path) -> None:
        dep = make_dep("requests", "2.31.0")
        proj = make_project(dep, path=tmp_path / "pyproject.toml")

        repo = FakeProjectRepository()
        repo.add_project(proj)

        registry = FakePackageRegistry(versions={"requests": "2.32.4"})
        use_case = AnalyzeDependencies(
            registry=registry,
            project_repo=repo,
            python_registry=FakePythonVersionRegistry(),
        )

        result = use_case.execute(tmp_path)
        assert result.is_ok()

        analysis_list = result.unwrap()
        assert len(analysis_list) == 1
        analysis = analysis_list[0]
        assert analysis.outdated_count == 1
        assert analysis.total_count == 1

    def test_up_to_date_dep_not_counted_as_outdated(self, tmp_path: Path) -> None:
        dep = make_dep("requests", "2.32.4")
        proj = make_project(dep, path=tmp_path / "pyproject.toml")

        repo = FakeProjectRepository()
        repo.add_project(proj)

        registry = FakePackageRegistry(versions={"requests": "2.32.4"})
        use_case = AnalyzeDependencies(
            registry=registry,
            project_repo=repo,
            python_registry=FakePythonVersionRegistry(),
        )

        result = use_case.execute(tmp_path)
        assert result.is_ok()
        analysis = result.unwrap()[0]
        assert analysis.outdated_count == 0

    def test_skips_projects_that_fail_to_load(self, tmp_path: Path) -> None:
        repo = FakeProjectRepository()
        repo._project_files = [tmp_path / "pyproject.toml"]  # file exists but won't load

        use_case = AnalyzeDependencies(
            registry=FakePackageRegistry(),
            project_repo=repo,
            python_registry=FakePythonVersionRegistry(),
        )
        result = use_case.execute(tmp_path)
        # Should succeed with empty list (all projects failed to load → logged warnings)
        assert result.is_ok()
        assert result.unwrap() == []

    def test_multiple_deps_batch_queried(self, tmp_path: Path) -> None:
        dep1 = make_dep("requests", "2.31.0")
        dep2 = make_dep("httpx", "0.26.0")
        proj = make_project(dep1, dep2, path=tmp_path / "pyproject.toml")

        repo = FakeProjectRepository()
        repo.add_project(proj)

        registry = FakePackageRegistry(versions={"requests": "2.32.4", "httpx": "0.28.0"})
        use_case = AnalyzeDependencies(
            registry=registry,
            project_repo=repo,
            python_registry=FakePythonVersionRegistry(),
        )

        result = use_case.execute(tmp_path)
        assert result.is_ok()
        analysis = result.unwrap()[0]
        assert analysis.outdated_count == 2
        assert analysis.total_count == 2

    def test_has_updates_property(self, tmp_path: Path) -> None:
        dep = make_dep("flask", "3.0.0")
        proj = make_project(dep, path=tmp_path / "pyproject.toml")

        repo = FakeProjectRepository()
        repo.add_project(proj)

        registry = FakePackageRegistry(versions={"flask": "3.1.0"})
        use_case = AnalyzeDependencies(
            registry=registry,
            project_repo=repo,
            python_registry=FakePythonVersionRegistry(),
        )

        result = use_case.execute(tmp_path)
        analysis = result.unwrap()[0]
        assert analysis.outdated_count > 0

    def test_python_outdated_false_when_constraint_satisfied(self, tmp_path: Path) -> None:
        """>=3.11 ist NICHT outdated wenn supported = [3.13, 3.12, 3.11]."""
        proj = Project(
            name="test-pkg",
            path=tmp_path / "pyproject.toml",
            python_constraint=VersionConstraint(
                operator=ConstraintOperator.GTE,
                version=make_version("3.11"),
            ),
        )
        repo = FakeProjectRepository()
        repo.add_project(proj)

        use_case = AnalyzeDependencies(
            registry=FakePackageRegistry(),
            project_repo=repo,
            python_registry=FakePythonVersionRegistry(versions=["3.13", "3.12", "3.11"]),
        )
        result = use_case.execute(tmp_path)
        assert result.is_ok()
        assert result.unwrap()[0].python_outdated is False

    def test_python_outdated_true_when_no_supported_version_satisfies(self, tmp_path: Path) -> None:
        """>=3.8 ist outdated wenn supported = [3.13, 3.12, 3.11] und 3.8 EOL."""
        proj = Project(
            name="test-pkg",
            path=tmp_path / "pyproject.toml",
            python_constraint=VersionConstraint(
                operator=ConstraintOperator.EQ,
                version=make_version("3.8.0"),
            ),
        )
        repo = FakeProjectRepository()
        repo.add_project(proj)

        use_case = AnalyzeDependencies(
            registry=FakePackageRegistry(),
            project_repo=repo,
            python_registry=FakePythonVersionRegistry(versions=["3.13", "3.12", "3.11"]),
        )
        result = use_case.execute(tmp_path)
        assert result.is_ok()
        assert result.unwrap()[0].python_outdated is True

    def test_python_outdated_false_when_gte_covers_latest(self, tmp_path: Path) -> None:
        """>=3.10 ist NICHT outdated solange irgendeine supported Version >= 3.10 ist."""
        proj = Project(
            name="test-pkg",
            path=tmp_path / "pyproject.toml",
            python_constraint=VersionConstraint(
                operator=ConstraintOperator.GTE,
                version=make_version("3.10"),
            ),
        )
        repo = FakeProjectRepository()
        repo.add_project(proj)

        use_case = AnalyzeDependencies(
            registry=FakePackageRegistry(),
            project_repo=repo,
            python_registry=FakePythonVersionRegistry(versions=["3.13", "3.12"]),
        )
        result = use_case.execute(tmp_path)
        assert result.is_ok()
        assert result.unwrap()[0].python_outdated is False


class TestApplyUpdates:
    def _make_analysis(self, outdated: int, path: Path | None = None) -> object:
        from dependapy.application.dtos import AnalysisResult

        proj = Project(
            name="test",
            path=path or Path("/tmp/test-proj"),
            python_constraint=None,
        )
        return AnalysisResult(project=proj, outdated_count=outdated, total_count=max(outdated, 1))

    def test_saves_projects_with_outdated_deps(self, tmp_path: Path) -> None:
        analysis = self._make_analysis(3, tmp_path / "pyproject.toml")

        repo = FakeProjectRepository()
        use_case = ApplyUpdates(project_repo=repo)

        result = use_case.execute([analysis])
        assert result.is_ok()
        update_result = result.unwrap()
        assert len(update_result.updated_files) == 1

    def test_skips_projects_without_updates(self) -> None:
        analysis = self._make_analysis(0)

        repo = FakeProjectRepository()
        use_case = ApplyUpdates(project_repo=repo)

        result = use_case.execute([analysis])
        assert result.is_ok()
        assert result.unwrap().updated_files == ()

    def test_counts_errors(self, tmp_path: Path) -> None:
        path = tmp_path / "pyproject.toml"
        analysis = self._make_analysis(2, path)

        repo = FakeProjectRepository()
        repo.add_save_error(analysis.project.path)  # type: ignore[union-attr]
        use_case = ApplyUpdates(project_repo=repo)

        result = use_case.execute([analysis])
        assert result.is_ok()
        assert result.unwrap().error_count == 1

    def test_empty_list_returns_empty_update_result(self) -> None:
        repo = FakeProjectRepository()
        use_case = ApplyUpdates(project_repo=repo)

        result = use_case.execute([])
        assert result.is_ok()
        assert result.unwrap().updated_files == ()
        assert result.unwrap().error_count == 0


class TestSubmitChanges:
    def test_successful_submit_returns_pr_url(self, tmp_path: Path) -> None:
        vcs = FakeVCSPort(pr_url="https://github.com/owner/repo/pull/42")
        use_case = SubmitChanges(vcs=vcs)

        result = use_case.execute(
            repo_path=tmp_path,
            updated_files=[tmp_path / "pyproject.toml"],
            branch_name="dependapy/updates",
            base_branch="main",
        )

        assert result.is_ok()
        submit_result = result.unwrap()
        assert submit_result.url == "https://github.com/owner/repo/pull/42"
        assert submit_result.files_changed == 1

    def test_branch_creation_failure_returns_err(self, tmp_path: Path) -> None:
        vcs = FakeVCSPort(fail_on_branch=True)
        use_case = SubmitChanges(vcs=vcs)

        result = use_case.execute(
            repo_path=tmp_path,
            updated_files=[tmp_path / "pyproject.toml"],
        )
        assert result.is_err()

    def test_commit_failure_returns_err(self, tmp_path: Path) -> None:
        vcs = FakeVCSPort(fail_on_commit=True)
        use_case = SubmitChanges(vcs=vcs)

        result = use_case.execute(
            repo_path=tmp_path,
            updated_files=[tmp_path / "pyproject.toml"],
        )
        assert result.is_err()

    def test_push_failure_returns_err(self, tmp_path: Path) -> None:
        vcs = FakeVCSPort(fail_on_push=True)
        use_case = SubmitChanges(vcs=vcs)

        result = use_case.execute(
            repo_path=tmp_path,
            updated_files=[tmp_path / "pyproject.toml"],
        )
        assert result.is_err()

    def test_pr_creation_failure_returns_err(self, tmp_path: Path) -> None:
        vcs = FakeVCSPort(fail_on_pr=True)
        use_case = SubmitChanges(vcs=vcs)

        result = use_case.execute(
            repo_path=tmp_path,
            updated_files=[tmp_path / "pyproject.toml"],
        )
        assert result.is_err()

    def test_branch_and_commit_are_recorded(self, tmp_path: Path) -> None:
        vcs = FakeVCSPort()
        use_case = SubmitChanges(vcs=vcs)

        use_case.execute(
            repo_path=tmp_path,
            updated_files=[tmp_path / "pyproject.toml"],
            branch_name="dependapy/test-branch",
        )

        assert "dependapy/test-branch" in vcs.branches_created
        assert len(vcs.commits_made) == 1
        assert "dependapy/test-branch" in vcs.pushes_made
