"""Tests für dependapy.domain.models — Dependency, Project, UpdatePlan."""

from __future__ import annotations

from pathlib import Path

import pytest

from dependapy.domain.errors import PolicyError
from dependapy.domain.models import (
    PlannedUpdate,
    PlanStatus,
    Project,
    UpdatePlan,
)
from dependapy.domain.value_objects import UpdateType
from tests.factories import make_dep, make_version


class TestDependency:
    def test_is_outdated_when_latest_is_greater(self) -> None:
        dep = make_dep(current="2.31.0", latest="2.32.0")
        assert dep.is_outdated() is True

    def test_is_not_outdated_when_current(self) -> None:
        dep = make_dep(current="2.32.0", latest="2.32.0")
        assert dep.is_outdated() is False

    def test_is_not_outdated_without_latest(self) -> None:
        dep = make_dep(current="1.0.0", latest=None)
        assert dep.is_outdated() is False

    def test_update_type_patch(self) -> None:
        dep = make_dep(current="2.31.0", latest="2.31.1")
        assert dep.update_type() == UpdateType.PATCH

    def test_update_type_minor(self) -> None:
        dep = make_dep(current="2.31.0", latest="2.32.0")
        assert dep.update_type() == UpdateType.MINOR

    def test_update_type_major(self) -> None:
        dep = make_dep(current="2.0.0", latest="3.0.0")
        assert dep.update_type() == UpdateType.MAJOR

    def test_update_type_none_when_no_latest(self) -> None:
        dep = make_dep(current="1.0.0", latest=None)
        assert dep.update_type() is None

    def test_with_latest_version_returns_new_instance(self) -> None:
        dep = make_dep(current="1.0.0")
        updated = dep.with_latest_version(make_version("1.5.0"))
        assert updated.latest_version == make_version("1.5.0")
        # Original unchanged
        assert dep.latest_version is None

    def test_with_latest_version_preserves_fields(self) -> None:
        dep = make_dep(name="flask", current="3.0.0", group="dev")
        updated = dep.with_latest_version(make_version("3.1.0"))
        assert updated.spec.name == "flask"
        assert updated.dependency_group == "dev"
        assert updated.current_version == make_version("3.0.0")

    def test_frozen(self) -> None:
        dep = make_dep()
        with pytest.raises((AttributeError, TypeError)):
            dep.dependency_group = "other"  # type: ignore[misc]


class TestProject:
    def _make_project(self, path: Path | None = None) -> Project:
        return Project(
            name="my-pkg",
            path=path or Path("/tmp/my-pkg"),
            python_constraint=None,
        )

    def test_add_dependency(self) -> None:
        proj = self._make_project()
        dep = make_dep()
        proj.add_dependency(dep)
        assert len(proj.dependencies) == 1
        assert proj.dependencies[0] == dep

    def test_get_outdated_empty(self) -> None:
        proj = self._make_project()
        dep = make_dep(current="1.0.0", latest=None)
        proj.add_dependency(dep)
        assert proj.get_outdated() == []

    def test_get_outdated_returns_only_outdated(self) -> None:
        proj = self._make_project()
        dep_ok = make_dep(name="ok-lib", current="1.0.0", latest="1.0.0")
        dep_old = make_dep(name="old-lib", current="1.0.0", latest="2.0.0")
        proj.add_dependency(dep_ok)
        proj.add_dependency(dep_old)
        outdated = proj.get_outdated()
        assert len(outdated) == 1
        assert outdated[0].spec.name == "old-lib"

    def test_mark_analyzed(self) -> None:
        proj = self._make_project()
        assert proj.analyzed_at is None
        proj.mark_analyzed()
        assert proj.analyzed_at is not None

    def test_dependency_count(self) -> None:
        proj = self._make_project()
        for i in range(5):
            proj.add_dependency(make_dep(name=f"lib-{i}"))
        assert len(proj.dependencies) == 5


class TestUpdatePlan:
    def test_initial_status_is_draft(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        assert plan.status == PlanStatus.DRAFT

    def test_approve_changes_status(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        plan.approve()
        assert plan.status == PlanStatus.APPROVED

    def test_reject_changes_status(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        plan.reject()
        assert plan.status == PlanStatus.REJECTED

    def test_add_planned_update(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        dep = make_dep(name="requests", current="2.31.0", latest="2.32.0")
        planned = PlannedUpdate(
            dependency=dep,
            target_version=make_version("2.32.0"),
            update_type=UpdateType.MINOR,
        )
        plan.add_update(planned)
        assert len(plan.updates) == 1
        assert plan.updates[0].dependency.spec.name == "requests"

    def test_mark_applied(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        plan.approve()
        plan.mark_applied()
        assert plan.status == PlanStatus.APPLIED

    def test_mark_failed(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        plan.approve()
        plan.mark_failed()
        assert plan.status == PlanStatus.FAILED

    # --- State transition guard tests ---

    def test_approve_from_rejected_raises(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        plan.reject()
        with pytest.raises(PolicyError, match="Invalid transition"):
            plan.approve()

    def test_mark_applied_from_draft_raises(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        with pytest.raises(PolicyError, match="Invalid transition"):
            plan.mark_applied()

    def test_mark_failed_from_draft_raises(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        with pytest.raises(PolicyError, match="Invalid transition"):
            plan.mark_failed()

    def test_reject_from_applied_raises(self) -> None:
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        plan.approve()
        plan.mark_applied()
        with pytest.raises(PolicyError, match="Invalid transition"):
            plan.reject()

    def test_failed_can_retry_to_draft(self) -> None:
        """FAILED → DRAFT is allowed via retry()."""
        proj = Project(name="p", path=Path("/tmp"), python_constraint=None)
        plan = UpdatePlan(project=proj)
        plan.approve()
        plan.mark_failed()
        assert plan.status == PlanStatus.FAILED
        plan.retry()
        assert plan.status == PlanStatus.DRAFT
