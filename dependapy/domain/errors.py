"""
Domain Errors — Hierarchische Fehlertypen für alle Domain-Operationen.

Jeder Port definiert seinen eigenen Fehlertyp als Subklasse von DomainError.
Result[T, E] nutzt diese Typen als Error-Generics.
"""

from __future__ import annotations


class DomainError(Exception):
    """Basis-Fehler für alle Domain-Operationen."""

    def __init__(self, message: str, *, context: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


# === Registry Errors ===


class RegistryError(DomainError):
    """Fehler bei Package-Registry-Operationen."""


class PackageNotFoundError(RegistryError):
    """Package existiert nicht auf der Registry."""


class RegistryTimeoutError(RegistryError):
    """Timeout bei Registry-API-Anfrage."""


class RegistryNetworkError(RegistryError):
    """Netzwerkfehler bei Registry-API."""


# === Project Errors ===


class ProjectError(DomainError):
    """Fehler bei Projekt-Operationen."""


class ProjectParseError(ProjectError):
    """pyproject.toml konnte nicht geparst werden."""


class ProjectWriteError(ProjectError):
    """Projekt konnte nicht geschrieben werden."""


# === VCS Errors ===


class VCSError(DomainError):
    """Fehler bei VCS-Operationen."""


class BranchExistsError(VCSError):
    """Branch existiert bereits."""


class PushRejectedError(VCSError):
    """Push wurde vom Remote abgelehnt."""


class PRCreationError(VCSError):
    """Pull Request konnte nicht erstellt werden."""


# === Policy Errors ===


class PolicyError(DomainError):
    """Fehler bei Policy-Operationen."""


class PolicyValidationError(PolicyError):
    """Policy-Datei hat Validierungsfehler."""


class PolicyNotFoundError(PolicyError):
    """Policy-Datei wurde nicht gefunden."""


# === Configuration Errors ===


class ConfigurationError(DomainError):
    """Ungültige oder unvollständige Konfiguration."""
