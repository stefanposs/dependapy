"""Tests für dependapy.domain.services — reine Funktionen."""

from __future__ import annotations

from dependapy.domain.services import (
    compute_update_type,
    create_update_plan,
    determine_target_version,
)
from dependapy.domain.value_objects import UpdateType
from tests.factories import make_dep, make_project, make_version

# ----- compute_update_type -----


def test_patch_update() -> None:
    assert compute_update_type(make_version("2.31.0"), make_version("2.31.1")) == UpdateType.PATCH


def test_minor_update() -> None:
    assert compute_update_type(make_version("2.31.0"), make_version("2.32.0")) == UpdateType.MINOR


def test_major_update() -> None:
    assert compute_update_type(make_version("2.0.0"), make_version("3.0.0")) == UpdateType.MAJOR


def test_downgrade_returns_none() -> None:
    assert compute_update_type(make_version("3.0.0"), make_version("2.0.0")) is None


def test_same_version_returns_none() -> None:
    assert compute_update_type(make_version("2.31.0"), make_version("2.31.0")) is None


# ----- determine_target_version -----


def test_determine_target_none_when_no_latest() -> None:
    dep = make_dep("requests", "2.31.0", latest=None)
    assert determine_target_version(dep, max_update_type=UpdateType.MAJOR) is None


def test_determine_target_none_when_not_outdated() -> None:
    dep = make_dep("requests", "2.31.0", latest="2.31.0")
    assert not dep.is_outdated()
    assert determine_target_version(dep, max_update_type=UpdateType.MAJOR) is None


def test_determine_target_patch_allowed() -> None:
    dep = make_dep("requests", "2.31.0", latest="2.31.1")
    assert determine_target_version(dep, max_update_type=UpdateType.PATCH) == make_version("2.31.1")


def test_determine_target_minor_allowed_for_minor() -> None:
    dep = make_dep("requests", "2.31.0", latest="2.32.0")
    assert determine_target_version(dep, max_update_type=UpdateType.MINOR) == make_version("2.32.0")


def test_determine_target_major_blocked_when_max_patch() -> None:
    dep = make_dep("requests", "2.0.0", latest="3.0.0")
    assert determine_target_version(dep, max_update_type=UpdateType.PATCH) is None


def test_determine_target_minor_blocked_when_max_patch() -> None:
    dep = make_dep("requests", "2.31.0", latest="2.32.0")
    assert determine_target_version(dep, max_update_type=UpdateType.PATCH) is None


def test_determine_target_major_allowed_when_max_major() -> None:
    dep = make_dep("requests", "2.0.0", latest="3.0.0")
    assert determine_target_version(dep, max_update_type=UpdateType.MAJOR) == make_version("3.0.0")


# ----- create_update_plan -----


def test_creates_plan_with_updates() -> None:
    dep = make_dep("requests", "2.31.0", latest="2.31.1")
    proj = make_project(dep)

    plan = create_update_plan(proj, max_update_type=UpdateType.PATCH)
    assert len(plan.updates) == 1
    assert plan.updates[0].dependency.spec.name == "requests"
    assert plan.updates[0].target_version == make_version("2.31.1")
    assert plan.updates[0].update_type == UpdateType.PATCH


def test_plan_filters_by_max_update_type() -> None:
    dep_patch = make_dep("requests", "2.31.0", latest="2.31.1")
    dep_minor = make_dep("httpx", "0.26.0", latest="0.27.0")
    dep_major = make_dep("flask", "2.0.0", latest="3.0.0")
    proj = make_project(dep_patch, dep_minor, dep_major)

    plan = create_update_plan(proj, max_update_type=UpdateType.MINOR)
    assert len(plan.updates) == 2
    names = {u.dependency.spec.name for u in plan.updates}
    assert "requests" in names
    assert "httpx" in names
    assert "flask" not in names


def test_plan_empty_when_no_outdated() -> None:
    dep = make_dep("requests", "2.32.4", latest="2.32.4")
    proj = make_project(dep)
    assert len(create_update_plan(proj).updates) == 0


def test_plan_empty_when_no_deps() -> None:
    proj = make_project()
    assert len(create_update_plan(proj).updates) == 0


def test_plan_default_max_is_patch() -> None:
    dep_minor = make_dep("httpx", "0.26.0", latest="0.27.0")
    proj = make_project(dep_minor)
    # default max_update_type = PATCH → minor blocked
    assert len(create_update_plan(proj).updates) == 0


def test_all_update_types_allowed_with_major() -> None:
    dep_patch = make_dep("a", "1.0.0", latest="1.0.1")
    dep_minor = make_dep("b", "1.0.0", latest="1.1.0")
    dep_major = make_dep("c", "1.0.0", latest="2.0.0")
    proj = make_project(dep_patch, dep_minor, dep_major)

    plan = create_update_plan(proj, max_update_type=UpdateType.MAJOR)
    assert len(plan.updates) == 3
