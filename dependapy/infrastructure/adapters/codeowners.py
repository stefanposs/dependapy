"""
CODEOWNERS Parser — Liest und matcht CODEOWNERS-Dateien.

Unterstützt GitHub CODEOWNERS Format (.github/CODEOWNERS, CODEOWNERS, docs/CODEOWNERS).
"""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path

logger = logging.getLogger("dependapy.infrastructure.adapters.codeowners")

# Standard-Pfade für CODEOWNERS
_CODEOWNERS_PATHS = (
    ".github/CODEOWNERS",
    "CODEOWNERS",
    "docs/CODEOWNERS",
)


class CodeownersEntry:
    """Eine Regel aus der CODEOWNERS-Datei."""

    __slots__ = ("owners", "pattern")

    def __init__(self, pattern: str, owners: list[str]) -> None:
        self.pattern = pattern
        self.owners = owners

    def matches(self, file_path: str) -> bool:
        """Prüft ob ein Dateipfad zu dieser Regel passt."""
        # Normalize: entferne führende /
        pattern = self.pattern.lstrip("/")
        normalized = file_path.lstrip("/")

        # Exakter Verzeichnis-Match: "src/" matcht alles unter src/
        if pattern.endswith("/"):
            return normalized.startswith(pattern) or fnmatch.fnmatch(normalized, f"{pattern}**")

        # Glob-Pattern: "*.py", "src/**/*.toml"
        if fnmatch.fnmatch(normalized, pattern):
            return True

        # Auch als Verzeichnis-Prefix matchen: "src" matcht "src/foo.py"
        if not any(c in pattern for c in ("*", "?", "[")):
            return normalized.startswith(f"{pattern}/")

        return False


def parse_codeowners(repo_root: Path) -> list[CodeownersEntry]:
    """Parst die CODEOWNERS-Datei eines Repositories.

    Sucht in den Standard-Pfaden (.github/CODEOWNERS, CODEOWNERS, docs/CODEOWNERS).
    Gibt eine leere Liste zurück wenn keine Datei gefunden wird.
    """
    for relative_path in _CODEOWNERS_PATHS:
        codeowners_path = repo_root / relative_path
        if codeowners_path.is_file():
            logger.debug("CODEOWNERS gefunden: %s", codeowners_path)
            return _parse_file(codeowners_path)

    logger.debug("Keine CODEOWNERS-Datei gefunden in %s", repo_root)
    return []


def _parse_file(path: Path) -> list[CodeownersEntry]:
    """Parst eine einzelne CODEOWNERS-Datei."""
    entries: list[CodeownersEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        pattern = parts[0]
        owners = [p for p in parts[1:] if not p.startswith("#")]
        if owners:
            entries.append(CodeownersEntry(pattern=pattern, owners=owners))

    logger.debug("CODEOWNERS: %d Regeln geladen", len(entries))
    return entries


def find_owners_for_file(file_path: str, entries: list[CodeownersEntry]) -> list[str]:
    """Findet die CODEOWNERS für eine Datei.

    CODEOWNERS-Regeln werden von unten nach oben ausgewertet —
    die letzte passende Regel gewinnt (wie bei GitHub).
    """
    owners: list[str] = []
    for entry in entries:
        if entry.matches(file_path):
            owners = entry.owners  # Letzte passende Regel überschreibt
    return owners


def find_owners_for_files(file_paths: list[str], entries: list[CodeownersEntry]) -> list[str]:
    """Findet alle eindeutigen CODEOWNERS für eine Liste von Dateien."""
    all_owners: set[str] = set()
    for file_path in file_paths:
        all_owners.update(find_owners_for_file(file_path, entries))
    return sorted(all_owners)
