"""Tests für dependapy.domain.value_objects — Version, VersionConstraint, PackageSpec."""

from __future__ import annotations

import pytest

from dependapy.domain.value_objects import (
    ConstraintOperator,
    PackageSpec,
    UpdateType,
    Version,
    VersionConstraint,
)
from dependapy.domain.vcs_types import PRRequest


class TestVersion:
    def test_from_string(self) -> None:
        v = Version.from_string("3.12.1")
        assert v.major == 3
        assert v.minor == 12
        assert v.micro == 1

    def test_comparison_greater(self) -> None:
        assert Version.from_string("3.12.0") > Version.from_string("3.11.0")

    def test_comparison_less(self) -> None:
        assert Version.from_string("2.0.0") < Version.from_string("3.0.0")

    def test_comparison_equal(self) -> None:
        assert Version.from_string("1.2.3") == Version.from_string("1.2.3")

    def test_comparison_ge(self) -> None:
        assert Version.from_string("3.12.1") >= Version.from_string("3.12.1")
        assert Version.from_string("3.13.0") >= Version.from_string("3.12.0")

    def test_comparison_le(self) -> None:
        assert Version.from_string("1.0.0") <= Version.from_string("2.0.0")

    def test_str(self) -> None:
        assert str(Version.from_string("3.12.1")) == "3.12.1"

    def test_repr(self) -> None:
        assert repr(Version.from_string("3.12.1")) == "Version('3.12.1')"

    def test_is_prerelease_false(self) -> None:
        assert Version.from_string("3.12.0").is_prerelease is False

    def test_is_prerelease_true(self) -> None:
        assert Version.from_string("3.13.0rc1").is_prerelease is True

    def test_hashable(self) -> None:
        v1 = Version.from_string("1.0.0")
        v2 = Version.from_string("1.0.0")
        assert hash(v1) == hash(v2)
        assert {v1, v2} == {v1}

    def test_frozen_not_mutable(self) -> None:
        v = Version.from_string("1.0.0")
        with pytest.raises((AttributeError, TypeError)):
            v._inner = None  # type: ignore[misc]

    def test_invalid_version_raises(self) -> None:
        with pytest.raises(Exception):
            Version.from_string("not-a-version")

    def test_gt_wrong_type_returns_not_implemented(self) -> None:
        v = Version.from_string("1.0.0")
        result = v.__gt__("1.0.0")
        assert result is NotImplemented

    def test_eq_wrong_type_returns_not_implemented(self) -> None:
        v = Version.from_string("1.0.0")
        result = v.__eq__("1.0.0")
        assert result is NotImplemented


class TestVersionConstraint:
    def test_gte_satisfied(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.GTE,
            version=Version.from_string("3.11"),
        )
        assert c.is_satisfied_by(Version.from_string("3.12")) is True
        assert c.is_satisfied_by(Version.from_string("3.11")) is True
        assert c.is_satisfied_by(Version.from_string("3.10")) is False

    def test_gte_with_upper_bound(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.GTE,
            version=Version.from_string("3.11"),
            upper_bound=Version.from_string("4.0"),
        )
        assert c.is_satisfied_by(Version.from_string("3.12")) is True
        assert c.is_satisfied_by(Version.from_string("4.0")) is False
        assert c.is_satisfied_by(Version.from_string("4.1")) is False

    def test_eq_satisfied(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.EQ,
            version=Version.from_string("2.0.0"),
        )
        assert c.is_satisfied_by(Version.from_string("2.0.0")) is True
        assert c.is_satisfied_by(Version.from_string("2.0.1")) is False

    def test_compatible_satisfied(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.COMPATIBLE,
            version=Version.from_string("1.4"),
        )
        assert c.is_satisfied_by(Version.from_string("1.5")) is True
        assert c.is_satisfied_by(Version.from_string("1.4")) is True
        assert c.is_satisfied_by(Version.from_string("1.3")) is False

    def test_compatible_enforces_upper_major_boundary(self) -> None:
        """~= 1.4 must reject 2.0 (== 1.* semantic, PEP 440)."""
        c = VersionConstraint(
            operator=ConstraintOperator.COMPATIBLE,
            version=Version.from_string("1.4"),
        )
        assert c.is_satisfied_by(Version.from_string("2.0.0")) is False
        assert c.is_satisfied_by(Version.from_string("3.0.0")) is False

    def test_compatible_minor_boundary(self) -> None:
        """~= 1.4.2 means >= 1.4.2, == 1.4.* — must reject 1.5.0."""
        c = VersionConstraint(
            operator=ConstraintOperator.COMPATIBLE,
            version=Version.from_string("1.4.2"),
        )
        assert c.is_satisfied_by(Version.from_string("1.4.3")) is True
        assert c.is_satisfied_by(Version.from_string("1.5.0")) is False
        assert c.is_satisfied_by(Version.from_string("1.4.1")) is False

    def test_str_without_upper_bound(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.GTE,
            version=Version.from_string("3.11"),
        )
        assert str(c) == ">=3.11"

    def test_str_with_upper_bound(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.GTE,
            version=Version.from_string("3.11"),
            upper_bound=Version.from_string("4.0"),
        )
        assert str(c) == ">=3.11,<4.0"

    def test_frozen(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.GTE,
            version=Version.from_string("1.0"),
        )
        with pytest.raises((AttributeError, TypeError)):
            c.operator = ConstraintOperator.EQ  # type: ignore[misc]


class TestPackageSpec:
    def _make_spec(
        self,
        name: str = "requests",
        version: str = "2.32.4",
        op: ConstraintOperator = ConstraintOperator.GTE,
    ) -> PackageSpec:
        return PackageSpec(
            name=name,
            version_constraint=VersionConstraint(
                operator=op,
                version=Version.from_string(version),
            ),
        )

    def test_name(self) -> None:
        assert self._make_spec().name == "requests"

    def test_str_no_extras(self) -> None:
        spec = self._make_spec()
        assert str(spec) == "requests>=2.32.4"

    def test_str_with_extras(self) -> None:
        spec = PackageSpec(
            name="uvicorn",
            version_constraint=VersionConstraint(
                operator=ConstraintOperator.GTE,
                version=Version.from_string("0.30.0"),
            ),
            extras=frozenset({"standard"}),
        )
        assert str(spec) == "uvicorn[standard]>=0.30.0"

    def test_frozen(self) -> None:
        spec = self._make_spec()
        with pytest.raises((AttributeError, TypeError)):
            spec.name = "other"  # type: ignore[misc]


class TestUpdateType:
    def test_values(self) -> None:
        assert UpdateType.MAJOR == "major"
        assert UpdateType.MINOR == "minor"
        assert UpdateType.PATCH == "patch"


class TestPRRequest:
    def test_creation(self) -> None:
        pr = PRRequest(
            repo_owner="owner",
            repo_name="repo",
            head_branch="feature",
            base_branch="main",
            title="PR Title",
            body="PR Body",
        )
        assert pr.repo_owner == "owner"
        assert pr.title == "PR Title"


class TestVersionComparisonNotImplemented:
    """Deckt die NotImplemented-Branches der Vergleichsoperatoren ab."""

    def test_lt_wrong_type(self) -> None:
        v = Version.from_string("1.0.0")
        assert v.__lt__("1.0.0") is NotImplemented

    def test_le_wrong_type(self) -> None:
        v = Version.from_string("1.0.0")
        assert v.__le__("1.0.0") is NotImplemented

    def test_ge_wrong_type(self) -> None:
        v = Version.from_string("1.0.0")
        assert v.__ge__("1.0.0") is NotImplemented


class TestCompatibleConstraintEdgeCases:
    """Deckt die COMPATIBLE-Operator-Branches ab."""

    def test_compatible_rejects_lower_version(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.COMPATIBLE,
            version=Version.from_string("2.5.0"),
        )
        assert c.is_satisfied_by(Version.from_string("2.4.0")) is False

    def test_compatible_derives_upper_bound(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.COMPATIBLE,
            version=Version.from_string("2.5.0"),
        )
        # ~=2.5.0 means >=2.5.0, ==2.5.*  → 2.5.1 OK, 2.6.0 NOT OK
        assert c.is_satisfied_by(Version.from_string("2.5.1")) is True
        assert c.is_satisfied_by(Version.from_string("2.6.0")) is False

    def test_compatible_with_explicit_upper_bound(self) -> None:
        c = VersionConstraint(
            operator=ConstraintOperator.COMPATIBLE,
            version=Version.from_string("2.5.0"),
            upper_bound=Version.from_string("3.0.0"),
        )
        assert c.is_satisfied_by(Version.from_string("2.9.0")) is True
        assert c.is_satisfied_by(Version.from_string("3.0.0")) is False
