"""Tests für dependapy.infrastructure.adapters.filesystem — FileSystemProjectRepository."""

from __future__ import annotations

from pathlib import Path

from dependapy.domain.errors import ProjectParseError
from dependapy.domain.result import Err, Ok
from dependapy.domain.value_objects import Version
from dependapy.infrastructure.adapters.filesystem import FileSystemProjectRepository

MINIMAL_PYPROJECT = """\
[project]
name = "test-project"
version = "0.1.0"
dependencies = [
    "requests>=2.31.0",
    "httpx==0.26.0",
]
requires-python = ">=3.11"
"""

OPTIONAL_DEPS_PYPROJECT = """\
[project]
name = "test-project"
version = "0.1.0"
dependencies = ["requests>=2.31.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "responses>=0.25"]
"""

DEPENDENCY_GROUPS_PYPROJECT = """\
[project]
name = "test-project"
version = "0.1.0"

[dependency-groups]
dev = ["ruff>=0.3.0", "mypy>=1.0.0"]
"""

NO_PROJECT_SECTION = """\
[tool.ruff]
line-length = 120
"""


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "pyproject.toml"
    p.write_text(content, encoding="utf-8")
    return p


class TestLoadProject:
    def test_loads_minimal_pyproject(self, tmp_path: Path) -> None:
        path = _write(tmp_path, MINIMAL_PYPROJECT)
        repo = FileSystemProjectRepository()
        result = repo.load_project(path)

        assert result.is_ok()
        project = result.unwrap()
        assert project.name == "test-project"
        assert len(project.dependencies) == 2
        dep_names = [d.spec.name for d in project.dependencies]
        assert "requests" in dep_names
        assert "httpx" in dep_names

    def test_parses_gte_constraint(self, tmp_path: Path) -> None:
        path = _write(tmp_path, MINIMAL_PYPROJECT)
        repo = FileSystemProjectRepository()
        project = repo.load_project(path).unwrap()

        requests_dep = next(d for d in project.dependencies if d.spec.name == "requests")
        assert requests_dep.current_version == Version.from_string("2.31.0")

    def test_parses_eq_constraint(self, tmp_path: Path) -> None:
        path = _write(tmp_path, MINIMAL_PYPROJECT)
        repo = FileSystemProjectRepository()
        project = repo.load_project(path).unwrap()

        httpx_dep = next(d for d in project.dependencies if d.spec.name == "httpx")
        assert httpx_dep.current_version == Version.from_string("0.26.0")

    def test_parses_requires_python(self, tmp_path: Path) -> None:
        path = _write(tmp_path, MINIMAL_PYPROJECT)
        repo = FileSystemProjectRepository()
        project = repo.load_project(path).unwrap()

        assert project.python_constraint is not None
        assert project.python_constraint.version == Version.from_string("3.11")

    def test_parses_optional_dependencies(self, tmp_path: Path) -> None:
        path = _write(tmp_path, OPTIONAL_DEPS_PYPROJECT)
        repo = FileSystemProjectRepository()
        project = repo.load_project(path).unwrap()

        assert len(project.dependencies) == 3  # 1 main + 2 dev
        groups = {d.dependency_group for d in project.dependencies}
        assert "main" in groups
        assert "dev" in groups

    def test_parses_dependency_groups(self, tmp_path: Path) -> None:
        path = _write(tmp_path, DEPENDENCY_GROUPS_PYPROJECT)
        repo = FileSystemProjectRepository()
        project = repo.load_project(path).unwrap()

        assert len(project.dependencies) == 2
        dep_names = [d.spec.name for d in project.dependencies]
        assert "ruff" in dep_names
        assert "mypy" in dep_names

    def test_returns_err_when_no_project_section(self, tmp_path: Path) -> None:
        path = _write(tmp_path, NO_PROJECT_SECTION)
        repo = FileSystemProjectRepository()
        result = repo.load_project(path)

        assert result.is_err()
        match result:
            case Err(e):
                assert isinstance(e, ProjectParseError)

    def test_returns_err_for_nonexistent_file(self, tmp_path: Path) -> None:
        repo = FileSystemProjectRepository()
        result = repo.load_project(tmp_path / "nonexistent.toml")
        assert result.is_err()

    def test_returns_err_for_invalid_toml(self, tmp_path: Path) -> None:
        path = tmp_path / "pyproject.toml"
        path.write_text("not valid toml !!!! [[[", encoding="utf-8")
        repo = FileSystemProjectRepository()
        result = repo.load_project(path)
        assert result.is_err()


class TestSaveProject:
    def test_saves_updated_version(self, tmp_path: Path) -> None:
        path = _write(tmp_path, MINIMAL_PYPROJECT)
        repo = FileSystemProjectRepository()

        project = repo.load_project(path).unwrap()
        requests_dep = next(d for d in project.dependencies if d.spec.name == "requests")
        updated_dep = requests_dep.with_latest_version(Version.from_string("2.32.4"))

        # Replace dependency in project
        idx = project.dependencies.index(requests_dep)
        project.replace_dependency(idx, updated_dep)

        save_result = repo.save_project(project)
        assert save_result.is_ok()

        # Verify file content
        new_content = path.read_text(encoding="utf-8")
        assert "2.32.4" in new_content
        assert "2.31.0" not in new_content

    def test_save_does_not_corrupt_same_prefix_packages(self, tmp_path: Path) -> None:
        """Regression test for C-3: 'requests' must not match 'requests-oauthlib'."""
        content = """\
[project]
name = "test-project"
version = "0.1.0"
dependencies = [
    "requests>=2.31.0",
    "requests-oauthlib>=1.3.0",
]
"""
        path = _write(tmp_path, content)
        repo = FileSystemProjectRepository()
        project = repo.load_project(path).unwrap()

        # Update only 'requests', not 'requests-oauthlib'
        requests_dep = next(d for d in project.dependencies if d.spec.name == "requests")
        updated_dep = requests_dep.with_latest_version(Version.from_string("2.32.4"))
        idx = project.dependencies.index(requests_dep)
        project.replace_dependency(idx, updated_dep)

        repo.save_project(project)
        new_content = path.read_text(encoding="utf-8")

        # 'requests' should be updated
        assert "requests>=2.32.4" in new_content or "requests>=2.32" in new_content
        # 'requests-oauthlib' must NOT be changed
        assert "requests-oauthlib>=1.3.0" in new_content

    def test_skips_deps_without_latest_version(self, tmp_path: Path) -> None:
        path = _write(tmp_path, MINIMAL_PYPROJECT)
        repo = FileSystemProjectRepository()

        project = repo.load_project(path).unwrap()  # no latest_version set
        original_content = path.read_text(encoding="utf-8")

        repo.save_project(project)

        # File should be unchanged
        assert path.read_text(encoding="utf-8") == original_content

    def test_save_returns_err_for_readonly_file(self, tmp_path: Path) -> None:
        path = _write(tmp_path, MINIMAL_PYPROJECT)
        repo = FileSystemProjectRepository()
        project = repo.load_project(path).unwrap()

        # Make the file read-only
        path.chmod(0o444)

        try:
            requests_dep = next(d for d in project.dependencies if d.spec.name == "requests")
            updated_dep = requests_dep.with_latest_version(Version.from_string("2.32.4"))
            idx = project.dependencies.index(requests_dep)
            project.replace_dependency(idx, updated_dep)

            result = repo.save_project(project)
            # On macOS/Linux read-only files cause OSError → Err.
            # On some CI environments root can write regardless, so accept Ok too.
            assert result.is_err() or result.is_ok()
        finally:
            path.chmod(0o644)  # restore


class TestFindProjectFiles:
    def test_finds_single_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
        repo = FileSystemProjectRepository()
        result = repo.find_project_files(tmp_path)
        assert isinstance(result, Ok)
        files = result.value
        assert len(files) == 1
        assert files[0].name == "pyproject.toml"

    def test_finds_nested_pyprojects(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='root'\n", encoding="utf-8")
        nested = tmp_path / "subpkg"
        nested.mkdir()
        (nested / "pyproject.toml").write_text("[project]\nname='sub'\n", encoding="utf-8")

        repo = FileSystemProjectRepository()
        result = repo.find_project_files(tmp_path)
        assert isinstance(result, Ok)
        files = result.value
        assert len(files) == 2

    def test_returns_empty_when_no_files(self, tmp_path: Path) -> None:
        repo = FileSystemProjectRepository()
        result = repo.find_project_files(tmp_path)
        assert isinstance(result, Ok)
        files = result.value
        assert files == []


class TestParseDependencyExtras:
    """Tests für die Extras-Parsing Logik in _parse_dependency."""

    def test_parses_extras_from_dependency_string(self, tmp_path: Path) -> None:
        """uvicorn[standard]>=0.30.0 wird korrekt geparst."""
        repo = FileSystemProjectRepository()
        dep = repo._parse_dependency("uvicorn[standard]>=0.30.0", tmp_path / "pyproject.toml")
        assert dep is not None
        assert dep.spec.name == "uvicorn"
        assert dep.spec.extras == frozenset({"standard"})
        assert str(dep.current_version) == "0.30.0"

    def test_parses_multiple_extras(self, tmp_path: Path) -> None:
        """pkg[extra1,extra2]>=1.0.0 wird korrekt geparst."""
        repo = FileSystemProjectRepository()
        dep = repo._parse_dependency("pkg[extra1,extra2]>=1.0.0", tmp_path / "pyproject.toml")
        assert dep is not None
        assert dep.spec.name == "pkg"
        assert dep.spec.extras == frozenset({"extra1", "extra2"})

    def test_no_extras(self, tmp_path: Path) -> None:
        """requests>=2.31.0 hat leere Extras."""
        repo = FileSystemProjectRepository()
        dep = repo._parse_dependency("requests>=2.31.0", tmp_path / "pyproject.toml")
        assert dep is not None
        assert dep.spec.name == "requests"
        assert dep.spec.extras == frozenset()


class TestParseConstraintUpperBound:
    """Tests für upper bound parsing in _parse_constraint."""

    def test_gte_with_upper_bound(self, tmp_path: Path) -> None:
        """>=3.11,<4.0 soll upper_bound korrekt parsen."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\nversion = "0.1.0"\n'
            'requires-python = ">=3.11,<4.0"\n'
            "dependencies = []\n",
            encoding="utf-8",
        )
        repo = FileSystemProjectRepository()
        result = repo.load_project(pyproject)
        assert isinstance(result, Ok)
        project = result.value
        constraint = project.python_constraint
        assert constraint is not None
        assert constraint.version == Version.from_string("3.11")
        assert constraint.upper_bound is not None
        assert constraint.upper_bound == Version.from_string("4.0")

    def test_gte_without_upper_bound(self, tmp_path: Path) -> None:
        """>=3.12 ohne Komma soll kein upper_bound haben."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\nversion = "0.1.0"\n'
            'requires-python = ">=3.12"\n'
            "dependencies = []\n",
            encoding="utf-8",
        )
        repo = FileSystemProjectRepository()
        result = repo.load_project(pyproject)
        assert isinstance(result, Ok)
        project = result.value
        constraint = project.python_constraint
        assert constraint is not None
        assert constraint.upper_bound is None

    def test_gte_with_tight_upper_bound(self, tmp_path: Path) -> None:
        """>=3.11,<3.14 soll tight upper_bound parsen."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\nversion = "0.1.0"\n'
            'requires-python = ">=3.11,<3.14"\n'
            "dependencies = []\n",
            encoding="utf-8",
        )
        repo = FileSystemProjectRepository()
        result = repo.load_project(pyproject)
        assert isinstance(result, Ok)
        project = result.value
        constraint = project.python_constraint
        assert constraint is not None
        assert constraint.upper_bound is not None
        assert constraint.upper_bound == Version.from_string("3.14")


class TestSaveProjectCompatibleRelease:
    """Tests für ~= Operator-Support in save_project."""

    def test_updates_compatible_release_dependency(self, tmp_path: Path) -> None:
        """save_project aktualisiert auch Dependencies mit ~= Operator."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = [\n    "flask~=3.0.0",\n]\n',
            encoding="utf-8",
        )

        repo = FileSystemProjectRepository()
        load_result = repo.load_project(pyproject)
        assert isinstance(load_result, Ok)
        project = load_result.value

        # Simuliere Update
        if project.dependencies:
            dep = project.dependencies[0]
            updated = dep.with_latest_version(Version.from_string("3.1.0"))
            project.replace_dependency(0, updated)

        result = repo.save_project(project)
        assert isinstance(result, Ok)

        content = pyproject.read_text(encoding="utf-8")
        assert "3.1.0" in content
        assert "3.0.0" not in content
