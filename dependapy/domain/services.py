"""
Domain Services — Reine Funktionen für domänenspezifische Berechnungen.

Kein OOP-Overhead nötig: VersionResolver und UpdatePlanner waren
stateless — jetzt einfach plain functions.
"""

from __future__ import annotations

from dependapy.domain.models import Dependency, PlannedUpdate, Project, UpdatePlan
from dependapy.domain.value_objects import UpdateType, Version

# ----- Version Resolution (pure functions) -----

_TYPE_RANK: dict[UpdateType, int] = {
    UpdateType.PATCH: 0,
    UpdateType.MINOR: 1,
    UpdateType.MAJOR: 2,
}


def compute_update_type(current: Version, target: Version) -> UpdateType | None:
    """Bestimmt ob es ein Major, Minor oder Patch Update ist.

    Gibt None zurück wenn target <= current (kein Update / Downgrade).
    """
    if target <= current:
        return None
    if target.major > current.major:
        return UpdateType.MAJOR
    if target.minor > current.minor:
        return UpdateType.MINOR
    return UpdateType.PATCH


def determine_target_version(
    dep: Dependency,
    *,
    max_update_type: UpdateType = UpdateType.PATCH,
) -> Version | None:
    """Bestimmt die Ziel-Version basierend auf erlaubtem Update-Typ.

    Gibt None zurück wenn kein Update möglich/erlaubt ist.
    """
    if dep.latest_version is None or not dep.is_outdated():
        return None

    update_type = dep.update_type()
    if update_type is None:
        return None

    if _TYPE_RANK.get(update_type, 0) <= _TYPE_RANK.get(max_update_type, 0):
        return dep.latest_version

    return None


# ----- Update Planning (pure function) -----


def create_update_plan(
    project: Project,
    *,
    max_update_type: UpdateType = UpdateType.PATCH,
) -> UpdatePlan:
    """Erstellt einen Update-Plan für alle veralteten Dependencies.

    Reine Funktion — kein State, keine Klasse nötig.
    """
    plan = UpdatePlan(project=project)

    for dep in project.get_outdated():
        target = determine_target_version(dep, max_update_type=max_update_type)
        if target is not None:
            update_type = dep.update_type()
            if update_type is not None:
                plan.add_update(
                    PlannedUpdate(
                        dependency=dep,
                        target_version=target,
                        update_type=update_type,
                    )
                )

    return plan
