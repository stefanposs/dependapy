"""
VCS-Typen — Reine Datenstrukturen für VCS-Operationen.

Diese Types definieren das Protokoll zwischen Application Layer und
VCS-Adaptern. Sie leben in der Domain, sind aber VCS-spezifisch und
vom rest der Domain isoliert.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PRRequest:
    """Request zum Erstellen einer Pull Request."""

    repo_owner: str
    repo_name: str
    head_branch: str
    base_branch: str
    title: str
    body: str
    reviewers: list[str] | None = None
    labels: list[str] | None = None
    auto_merge: bool = False


@dataclass(frozen=True, slots=True)
class PRResult:
    """Ergebnis einer PR-Erstellung."""

    url: str
    number: int
    provider: str


@dataclass(frozen=True, slots=True)
class RepoInfo:
    """Repository-Metadaten."""

    owner: str
    name: str
    default_branch: str
    provider: str
