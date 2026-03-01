"""
Example: Domain services for version comparison and update planning.

Demonstrates using dependapy's pure domain functions directly — no HTTP calls,
no I/O, no side effects. Useful for embedding version logic in custom tooling.

Usage:
    uv run python examples/domain_services.py
"""

from __future__ import annotations

from pathlib import Path

from dependapy.domain.models import Dependency, Project
from dependapy.domain.services import (
    compute_update_type,
    create_update_plan,
    determine_target_version,
)
from dependapy.domain.value_objects import (
    ConstraintOperator,
    PackageSpec,
    UpdateType,
    Version,
    VersionConstraint,
)


def _make_dep(name: str, current: str, *, latest: str | None = None) -> Dependency:
    """Helper to create a Dependency with a >= constraint."""
    return Dependency(
        spec=PackageSpec(
            name=name,
            version_constraint=VersionConstraint(
                operator=ConstraintOperator.GTE,
                version=Version.from_string(current),
            ),
        ),
        current_version=Version.from_string(current),
        latest_version=Version.from_string(latest) if latest else None,
        source_file=Path("pyproject.toml"),
        dependency_group="main",
    )


def example_compute_update_type() -> None:
    """Classify the type of version bump between two versions."""
    print("=== compute_update_type ===")

    cases = [
        ("2.31.0", "2.31.1"),  # patch
        ("2.31.0", "2.32.0"),  # minor
        ("2.0.0", "3.0.0"),  # major
        ("3.0.0", "2.0.0"),  # downgrade → None
        ("1.0.0", "1.0.0"),  # same → None
    ]

    for current, target in cases:
        result = compute_update_type(Version.from_string(current), Version.from_string(target))
        label = result.value if result else "none (no update)"
        print(f"  {current} → {target}: {label}")
    print()


def example_determine_target_version() -> None:
    """Filter updates based on maximum allowed update type."""
    print("=== determine_target_version ===")

    dep = _make_dep("flask", "2.0.0", latest="3.1.0")

    for max_type in (UpdateType.PATCH, UpdateType.MINOR, UpdateType.MAJOR):
        target = determine_target_version(dep, max_update_type=max_type)
        if target:
            print(f"  max={max_type.value}: update to {target}")
        else:
            print(f"  max={max_type.value}: blocked (update too large)")
    print()


def example_create_update_plan() -> None:
    """Build an update plan for a project with multiple dependencies."""
    print("=== create_update_plan ===")

    project = Project(name="my-app", path=Path("/tmp/my-app"), python_constraint=None)
    project.add_dependency(_make_dep("requests", "2.28.0", latest="2.32.4"))
    project.add_dependency(_make_dep("flask", "2.3.0", latest="3.1.0"))
    project.add_dependency(_make_dep("click", "8.1.7", latest="8.1.7"))  # up-to-date

    for max_type in (UpdateType.PATCH, UpdateType.MINOR, UpdateType.MAJOR):
        plan = create_update_plan(project, max_update_type=max_type)
        print(f"  max={max_type.value}: {len(plan.updates)} update(s)")
        for update in plan.updates:
            print(
                f"    {update.dependency.spec.name}: "
                f"{update.dependency.current_version} → {update.target_version} "
                f"({update.update_type.value})"
            )
    print()


if __name__ == "__main__":
    example_compute_update_type()
    example_determine_target_version()
    example_create_update_plan()
