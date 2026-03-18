"""
Policy — Domain Model für .dependapy.yml Konfiguration.

Definiert Regeln für Dependency-Updates:
- ignore: Packages die nicht aktualisiert werden
- allow: Erlaubte Update-Typen pro Package
- labels: PR-Labels
- reviewers / assignees: PR-Reviewer und -Zuweisungen
- commit_message: Commit-Message-Template mit Prefix
- groups: Gruppenweise Updates in einem PR
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch


@dataclass(frozen=True, slots=True)
class IgnoreRule:
    """Ignoriert ein Package bei Updates.

    name kann ein glob-Pattern sein (z.B. 'boto*').
    versions kann ein Bereich sein (z.B. '>= 2.0').
    """

    name: str
    versions: str | None = None
    reason: str | None = None

    def matches(self, package_name: str) -> bool:
        """Prüft ob der Package-Name zu dieser Ignore-Regel passt."""
        return fnmatch(package_name.lower(), self.name.lower())


@dataclass(frozen=True, slots=True)
class AllowRule:
    """Erlaubte Update-Typen für ein Package oder Glob-Pattern.

    update_types: "major", "minor", "patch" — welche Updates erlaubt sind.
    """

    name: str
    update_types: frozenset[str] = frozenset({"major", "minor", "patch"})

    def matches(self, package_name: str) -> bool:
        """Prüft ob der Package-Name zu dieser Allow-Regel passt."""
        return fnmatch(package_name.lower(), self.name.lower())


@dataclass(frozen=True, slots=True)
class CommitMessage:
    """Commit-Message-Template für PRs."""

    prefix: str = "chore(deps)"
    include_scope: bool = True


@dataclass(frozen=True, slots=True)
class DependencyGroup:
    """Gruppiert Packages in einen gemeinsamen PR.

    patterns: Glob-Patterns für Package-Namen.
    """

    name: str
    patterns: tuple[str, ...] = ()

    def matches(self, package_name: str) -> bool:
        """Prüft ob das Package zu dieser Gruppe gehört."""
        return any(fnmatch(package_name.lower(), p.lower()) for p in self.patterns)


@dataclass(frozen=True, slots=True)
class Policy:
    """Zentrale Policy-Definition aus .dependapy.yml.

    Wird vom PolicyLoader geladen und von Use Cases konsumiert.
    """

    version: int = 1
    ignore: tuple[IgnoreRule, ...] = ()
    allow: tuple[AllowRule, ...] = ()
    labels: tuple[str, ...] = ()
    reviewers: tuple[str, ...] = ()
    assignees: tuple[str, ...] = ()
    commit_message: CommitMessage = field(default_factory=CommitMessage)
    groups: tuple[DependencyGroup, ...] = ()
    auto_merge: bool = False

    def is_ignored(self, package_name: str) -> bool:
        """Prüft ob ein Package ignoriert werden soll."""
        return any(rule.matches(package_name) for rule in self.ignore)

    def allowed_update_types(self, package_name: str) -> frozenset[str]:
        """Gibt die erlaubten Update-Typen für ein Package zurück.

        Wenn keine Allow-Regel greift, sind alle Updates erlaubt.
        """
        for rule in self.allow:
            if rule.matches(package_name):
                return rule.update_types
        return frozenset({"major", "minor", "patch"})

    def find_group(self, package_name: str) -> DependencyGroup | None:
        """Findet die Gruppe, zu der ein Package gehört."""
        for group in self.groups:
            if group.matches(package_name):
                return group
        return None

    def format_commit_message(self, scope: str, description: str) -> str:
        """Formatiert eine Commit-Message nach Template."""
        prefix = self.commit_message.prefix
        if self.commit_message.include_scope and scope:
            return f"{prefix}({scope}): {description}"
        return f"{prefix}: {description}"
