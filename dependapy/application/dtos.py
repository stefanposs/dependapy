"""
Data Transfer Objects — Schichten-übergreifende Datenstrukturen.

DTOs werden von Use Cases zurückgegeben und von der Presentation Layer konsumiert.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dependapy.domain.models import Project


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Ergebnis der Dependency-Analyse eines Projekts."""

    project: Project
    outdated_count: int
    total_count: int
    python_outdated: bool = False


@dataclass(frozen=True, slots=True)
class SubmitResult:
    """Ergebnis der Change-Einreichung."""

    url: str
    provider: str
    files_changed: int


@dataclass(frozen=True, slots=True)
class UpdateResult:
    """Ergebnis des Update-Vorgangs."""

    updated_files: tuple[Path, ...] = ()
    skipped_count: int = 0
    error_count: int = 0
