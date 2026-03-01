"""
Value Objects — Immutable Datentypen ohne Identität.

Alle Value Objects sind frozen dataclasses mit slots=True.
Version wrapping packaging.version.Version (ADR-003).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from packaging.version import InvalidVersion
from packaging.version import Version as PkgVersion

# === Enums ===


class UpdateType(StrEnum):
    """Art eines Dependency-Updates."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class ConstraintOperator(StrEnum):
    """Operator für Version-Constraints in pyproject.toml."""

    GTE = ">="
    EQ = "=="
    COMPATIBLE = "~="


# === Value Objects ===


@dataclass(frozen=True, slots=True)
class Version:
    """Immutable Version Value Object.

    Wrapping packaging.version.Version für PEP 440 Compliance.
    Unterstützt Pre-Releases, Post-Releases, Epochs.
    """

    _inner: PkgVersion

    @classmethod
    def from_string(cls, s: str) -> Version:
        """Parse einen Version-String wie '3.12.1' oder '2.0.0rc1'."""
        return cls(_inner=PkgVersion(s))

    @property
    def major(self) -> int:
        return self._inner.major

    @property
    def minor(self) -> int:
        return self._inner.minor

    @property
    def micro(self) -> int:
        return self._inner.micro

    @property
    def is_prerelease(self) -> bool:
        return self._inner.is_prerelease

    @property
    def is_postrelease(self) -> bool:
        return self._inner.is_postrelease

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._inner > other._inner

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._inner >= other._inner

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._inner < other._inner

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._inner <= other._inner

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._inner == other._inner

    def __hash__(self) -> int:
        return hash(self._inner)

    def __str__(self) -> str:
        return str(self._inner)

    def __repr__(self) -> str:
        return f"Version('{self._inner}')"


@dataclass(frozen=True, slots=True)
class VersionConstraint:
    """Constraint wie >=3.11 oder ==2.0.0."""

    operator: ConstraintOperator
    version: Version
    upper_bound: Version | None = None

    def is_satisfied_by(self, version: Version) -> bool:
        """Prüft ob eine Version dieses Constraint erfüllt."""
        match self.operator:
            case ConstraintOperator.GTE:
                ok = version >= self.version
                if self.upper_bound:
                    ok = ok and version < self.upper_bound
                return ok
            case ConstraintOperator.EQ:
                return version == self.version
            case ConstraintOperator.COMPATIBLE:
                # PEP 440 compatible release: ~= X.Y means >= X.Y, == X.*
                # ~= X.Y.Z means >= X.Y.Z, == X.Y.*
                # Derive upper bound: drop last component, increment second-to-last.
                if version < self.version:
                    return False
                if self.upper_bound is not None:
                    return version < self.upper_bound
                parts = str(self.version).split(".")
                if len(parts) >= 2:
                    upper_parts = parts[:-1]
                    upper_parts[-1] = str(int(upper_parts[-1]) + 1)
                    try:
                        upper = Version.from_string(".".join(upper_parts))
                        return version < upper
                    except (InvalidVersion, ValueError):
                        pass
                # Fallback: only same major
                return version.major == self.version.major
            case _:
                return False

    def __str__(self) -> str:
        s = f"{self.operator.value}{self.version}"
        if self.upper_bound:
            s += f",<{self.upper_bound}"
        return s


@dataclass(frozen=True, slots=True)
class PackageSpec:
    """Spezifikation eines Python-Packages mit Version-Constraint."""

    name: str
    version_constraint: VersionConstraint
    extras: frozenset[str] = frozenset()

    def __str__(self) -> str:
        extras_str = f"[{','.join(sorted(self.extras))}]" if self.extras else ""
        return f"{self.name}{extras_str}{self.version_constraint}"
