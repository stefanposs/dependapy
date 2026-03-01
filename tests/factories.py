"""Shared test factories for dependapy tests.

Provides reusable builder functions for domain objects.
Import these instead of defining per-file helpers.
"""

from __future__ import annotations

from pathlib import Path

from dependapy.domain.models import Dependency, Project
from dependapy.domain.value_objects import (
    ConstraintOperator,
    PackageSpec,
    Version,
    VersionConstraint,
)


def make_version(s: str) -> Version:
    """Create a Version from a string like '2.31.0'."""
    return Version.from_string(s)


def make_spec(name: str, version: str = "1.0.0") -> PackageSpec:
    """Create a PackageSpec with a >= constraint."""
    return PackageSpec(
        name=name,
        version_constraint=VersionConstraint(
            operator=ConstraintOperator.GTE,
            version=make_version(version),
        ),
    )


def make_dep(
    name: str = "requests",
    current: str = "2.31.0",
    *,
    latest: str | None = None,
    group: str = "main",
) -> Dependency:
    """Create a Dependency with optional latest version."""
    return Dependency(
        spec=make_spec(name, current),
        current_version=make_version(current),
        latest_version=make_version(latest) if latest else None,
        source_file=Path("pyproject.toml"),
        dependency_group=group,
    )


def make_project(
    *deps: Dependency,
    name: str = "test-pkg",
    path: Path | None = None,
) -> Project:
    """Create a Project with optional dependencies."""
    proj = Project(
        name=name,
        path=path or Path("/tmp/test-proj"),
        python_constraint=None,
    )
    for dep in deps:
        proj.add_dependency(dep)
    return proj
