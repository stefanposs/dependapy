"""
EndOfLife Adapter — Implementiert PythonVersionRegistry Port.

Fragt die unterstützten Python-Versionen von endoflife.date ab.
"""

from __future__ import annotations

import functools
import logging

from dependapy.domain.errors import RegistryError
from dependapy.domain.result import Err, Ok, Result
from dependapy.domain.value_objects import Version
from dependapy.infrastructure.http import HttpClient

logger = logging.getLogger("dependapy.infrastructure.adapters.endoflife")

# Fallback-Versionen wenn API nicht erreichbar
_FALLBACK_VERSION_STRINGS: tuple[str, ...] = ("3.13", "3.12", "3.11")


@functools.cache
def _fallback_versions() -> tuple[Version, ...]:
    """Cached Fallback-Versionen — wird nur einmal berechnet."""
    logger.info("Verwende Fallback Python-Versionen: %s", _FALLBACK_VERSION_STRINGS)
    return tuple(Version.from_string(v) for v in _FALLBACK_VERSION_STRINGS)


class EndOfLifeAdapter:
    """Python Version Registry via endoflife.date API.

    Implementiert das PythonVersionRegistry Protocol.
    """

    def __init__(
        self,
        http_client: HttpClient,
        api_url: str = "https://endoflife.date/api/python.json",
        num_versions: int = 3,
    ) -> None:
        self._http = http_client
        self._api_url = api_url
        self._num_versions = num_versions
        self._cache: list[Version] | None = None

    def get_supported_versions(self) -> Result[list[Version], RegistryError]:
        """Gibt die neuesten unterstützten Python 3.x Minor-Versionen zurück."""
        if self._cache is not None:
            return Ok(self._cache)

        match self._http.get(self._api_url):
            case Ok(response) if response.status_code == 200:
                try:
                    data = response.json()
                    py3_cycles = [v["cycle"] for v in data if v["cycle"].startswith("3.")]
                    # Sortiere absteigend nach Version
                    py3_cycles.sort(key=lambda x: Version.from_string(x), reverse=True)
                    versions = [Version.from_string(c) for c in py3_cycles[: self._num_versions]]
                    self._cache = versions
                    logger.info(
                        "Unterstützte Python-Versionen: %s",
                        ", ".join(str(v) for v in versions),
                    )
                    return Ok(versions)
                except (KeyError, ValueError) as e:
                    logger.warning("Ungültige EOL-API-Antwort: %s", e)
                    fallback = list(_fallback_versions())
                    self._cache = fallback
                    return Ok(fallback)
            case Ok(response):
                logger.warning("EOL API HTTP %d", response.status_code)
                fallback = list(_fallback_versions())
                self._cache = fallback
                return Ok(fallback)
            case Err(error):
                logger.warning("EOL API nicht erreichbar: %s", error)
                fallback = list(_fallback_versions())
                self._cache = fallback
                return Ok(fallback)
