"""
Offline Version Source — Lokale Versionsquelle für Air-Gapped Runner.

Liest Package-Versionen aus lokalen Quellen statt von PyPI:
1. uv.lock (TOML-Format)
2. requirements.txt (pinned versions)

Implementiert das PackageRegistry Protocol für den Offline-Betrieb.
"""

from __future__ import annotations

import logging
import re
import tomllib
from pathlib import Path

from dependapy.domain.errors import PackageNotFoundError, RegistryError
from dependapy.domain.result import Err, Ok, Result
from dependapy.domain.value_objects import Version

logger = logging.getLogger("dependapy.infrastructure.adapters.offline_registry")

# Package name normalization: PEP 503
_NORMALIZE_RE = re.compile(r"[-_.]+")


def _normalize(name: str) -> str:
    """PEP 503 — normalisiert Package-Namen für Vergleiche."""
    return _NORMALIZE_RE.sub("-", name).lower()


class OfflineRegistryAdapter:
    """Offline Package Registry — liest Versionen aus lokalen Lock-Dateien.

    Durchsucht das Projektverzeichnis nach uv.lock oder requirements.txt
    und baut einen lokalen Versions-Cache auf.
    """

    def __init__(self, project_root: Path) -> None:
        self._versions: dict[str, Version] = {}
        self._loaded = False
        self._project_root = project_root

    def _ensure_loaded(self) -> None:
        """Lazy-Load: Lädt Versionen erst beim ersten Zugriff."""
        if self._loaded:
            return
        self._loaded = True

        # Priorität: uv.lock > requirements.txt
        uv_lock = self._project_root / "uv.lock"
        if uv_lock.is_file():
            self._load_uv_lock(uv_lock)
            return

        # Fallback: requirements.txt / requirements-*.txt
        for req_file in sorted(self._project_root.glob("requirements*.txt")):
            self._load_requirements_txt(req_file)

    def _load_uv_lock(self, path: Path) -> None:
        """Parst uv.lock (TOML-Format) und extrahiert Package-Versionen."""
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            packages = data.get("package", [])
            for pkg in packages:
                name = pkg.get("name", "")
                version = pkg.get("version", "")
                if name and version:
                    try:
                        self._versions[_normalize(name)] = Version.from_string(version)
                    except (ValueError, TypeError):
                        logger.debug("Ungültige Version in uv.lock: %s=%s", name, version)
            logger.info("Offline-Registry: %d Packages aus %s geladen", len(self._versions), path)
        except (tomllib.TOMLDecodeError, OSError) as e:
            logger.warning("uv.lock nicht lesbar: %s", e)

    def _load_requirements_txt(self, path: Path) -> None:
        """Parst requirements.txt und extrahiert pinned Versionen."""
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Format: package==1.2.3 oder package>=1.2.3
                match = re.match(r"^([a-zA-Z0-9_.-]+)==([^\s;#]+)", line)
                if match:
                    name, version = match.group(1), match.group(2)
                    try:
                        self._versions[_normalize(name)] = Version.from_string(version)
                    except (ValueError, TypeError):
                        pass
            logger.info("Offline-Registry: %d Packages aus %s geladen", len(self._versions), path)
        except OSError as e:
            logger.warning("requirements.txt nicht lesbar: %s", e)

    def close(self) -> None:
        """Kompatibilität mit Closable-Protocol."""

    def get_latest_version(self, package_name: str) -> Result[Version, RegistryError]:
        """Gibt die lokal bekannte Version eines Packages zurück."""
        self._ensure_loaded()
        normalized = _normalize(package_name)
        if normalized in self._versions:
            return Ok(self._versions[normalized])
        return Err(
            PackageNotFoundError(
                f"Package '{package_name}' nicht in lokaler Versionsquelle gefunden"
            )
        )

    def get_latest_versions_batch(
        self, package_names: list[str]
    ) -> dict[str, Result[Version, RegistryError]]:
        """Gibt Versionen für mehrere Packages zurück (synchron, kein Netzwerk)."""
        self._ensure_loaded()
        return {name: self.get_latest_version(name) for name in package_names}
