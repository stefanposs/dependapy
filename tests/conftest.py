"""Shared pytest fixtures for dependapy tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from dependapy.domain.models import Dependency, Project
from dependapy.domain.value_objects import Version
from tests.factories import make_spec, make_version


@pytest.fixture
def sample_version() -> Version:
    return make_version("2.32.4")


@pytest.fixture
def requests_dep() -> Dependency:
    return Dependency(
        spec=make_spec("requests", "2.31.0"),
        current_version=make_version("2.31.0"),
        source_file=Path("pyproject.toml"),
        dependency_group="main",
    )


@pytest.fixture
def outdated_requests_dep() -> Dependency:
    return Dependency(
        spec=make_spec("requests", "2.31.0"),
        current_version=make_version("2.31.0"),
        latest_version=make_version("2.32.4"),
        source_file=Path("pyproject.toml"),
        dependency_group="main",
    )


@pytest.fixture
def sample_project(tmp_path: Path, requests_dep: Dependency) -> Project:
    proj = Project(
        name="sample-project",
        path=tmp_path / "pyproject.toml",
        python_constraint=None,
    )
    proj.add_dependency(requests_dep)
    return proj


@pytest.fixture
def simple_pyproject_toml(tmp_path: Path) -> Path:
    content = """\
[project]
name = "sample-project"
version = "0.1.0"
dependencies = [
    "requests>=2.31.0",
    "httpx==0.26.0",
]
requires-python = ">=3.11"
"""
    path = tmp_path / "pyproject.toml"
    path.write_text(content, encoding="utf-8")
    return path
