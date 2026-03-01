"""
Domain Entities — Geschäftsobjekte mit Verhalten.

Dependency ist frozen (immutable). Project ist der Aggregate Root.
Keine UUIDs — erst mit Persistence Layer (Phase 2).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from dependapy.domain.errors import PolicyError
from dependapy.domain.value_objects import (
    PackageSpec,
    UpdateType,
    Version,
    VersionConstraint,
)


@dataclass(frozen=True, slots=True)
class Dependency:
    """Eine einzelne Abhängigkeit eines Projekts (immutable).

    Enrichment (latest_version setzen) erzeugt eine neue Instanz via
    dataclasses.replace(dep, latest_version=...).
    """

    spec: PackageSpec
    current_version: Version
    latest_version: Version | None = None
    source_file: Path | None = None
    dependency_group: str = "main"

    def is_outdated(self) -> bool:
        """Prüft ob eine neuere Version verfügbar ist."""
        if self.latest_version is None:
            return False
        return self.latest_version > self.current_version

    def update_type(self) -> UpdateType | None:
        """Bestimmt den Update-Typ (major/minor/patch)."""
        if not self.is_outdated() or self.latest_version is None:
            return None
        if self.latest_version.major > self.current_version.major:
            return UpdateType.MAJOR
        if self.latest_version.minor > self.current_version.minor:
            return UpdateType.MINOR
        return UpdateType.PATCH

    def with_latest_version(self, latest: Version) -> Dependency:
        """Erstellt eine neue Dependency-Instanz mit gesetzter latest_version."""
        return dataclasses.replace(self, latest_version=latest)


class PlanStatus(StrEnum):
    """Status eines Update-Plans."""

    DRAFT = "draft"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PlannedUpdate:
    """Ein geplantes Update innerhalb eines UpdatePlans."""

    dependency: Dependency
    target_version: Version
    update_type: UpdateType
    auto_merge: bool = False


@dataclass
class Project:
    """Aggregate Root: Ein Python-Projekt mit seinen Dependencies.

    Project ist mutable, da Dependencies während der Analyse hinzugefügt
    und angereichert werden.
    """

    name: str
    path: Path
    python_constraint: VersionConstraint | None = None
    dependencies: list[Dependency] = field(default_factory=list)
    analyzed_at: datetime | None = None

    def add_dependency(self, dep: Dependency) -> None:
        """Fügt eine Dependency hinzu."""
        self.dependencies.append(dep)

    def get_outdated(self) -> list[Dependency]:
        """Gibt alle veralteten Dependencies zurück."""
        return [d for d in self.dependencies if d.is_outdated()]

    def mark_analyzed(self) -> None:
        """Markiert das Projekt als analysiert."""
        self.analyzed_at = datetime.now(UTC)

    def replace_dependency(self, index: int, new_dep: Dependency) -> None:
        """Ersetzt eine Dependency an einem bestimmten Index."""
        self.dependencies[index] = new_dep


_VALID_TRANSITIONS: dict[PlanStatus, frozenset[PlanStatus]] = {
    PlanStatus.DRAFT: frozenset({PlanStatus.APPROVED, PlanStatus.REJECTED}),
    PlanStatus.APPROVED: frozenset({PlanStatus.APPLIED, PlanStatus.FAILED}),
    PlanStatus.REJECTED: frozenset(),
    PlanStatus.APPLIED: frozenset(),
    PlanStatus.FAILED: frozenset({PlanStatus.DRAFT}),
}


@dataclass
class UpdatePlan:
    """Ein Plan für Dependency-Updates."""

    project: Project
    updates: list[PlannedUpdate] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: PlanStatus = PlanStatus.DRAFT

    def _transition(self, target: PlanStatus) -> None:
        """Validiert und führt einen Statusübergang durch."""
        allowed = _VALID_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            msg = f"Invalid transition: {self.status.value} \u2192 {target.value}"
            raise PolicyError(msg)
        self.status = target

    def add_update(self, update: PlannedUpdate) -> None:
        """Fügt ein geplantes Update hinzu (nur im DRAFT-Status)."""
        if self.status != PlanStatus.DRAFT:
            msg = f"Cannot add updates to plan in status {self.status}"
            raise PolicyError(msg)
        self.updates.append(update)

    def approve(self) -> None:
        self._transition(PlanStatus.APPROVED)

    def reject(self) -> None:
        self._transition(PlanStatus.REJECTED)

    def mark_applied(self) -> None:
        self._transition(PlanStatus.APPLIED)

    def mark_failed(self) -> None:
        self._transition(PlanStatus.FAILED)

    def retry(self) -> None:
        """Setzt den Plan nach einem Fehler zurück auf DRAFT."""
        self._transition(PlanStatus.DRAFT)
