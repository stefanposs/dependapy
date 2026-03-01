"""
PyPI Adapter — Implementiert PackageRegistry Port.

Fragt Package-Versionen von PyPI ab mit Cache und Batch-Support.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from dependapy.domain.errors import (
    PackageNotFoundError,
    RegistryError,
    RegistryNetworkError,
    RegistryTimeoutError,
)
from dependapy.domain.result import Err, Ok, Result
from dependapy.domain.value_objects import Version
from dependapy.infrastructure.http import HttpClient

logger = logging.getLogger("dependapy.infrastructure.adapters.pypi")


class PyPIAdapter:
    """PyPI Package Registry Adapter.

    Implementiert das PackageRegistry Protocol für PyPI.
    Cached Ergebnisse um wiederholte Anfragen zu vermeiden.
    """

    def __init__(
        self,
        http_client: HttpClient,
        base_url: str = "https://pypi.org/pypi/{package_name}/json",
        max_workers: int = 10,
    ) -> None:
        self._http = http_client
        self._base_url = base_url
        self._max_workers = max_workers
        self._cache: dict[str, Result[Version, RegistryError]] = {}
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)

    def close(self) -> None:
        """Gibt den ThreadPoolExecutor frei."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    def get_latest_version(self, package_name: str) -> Result[Version, RegistryError]:
        """Gibt die neueste Version eines Packages von PyPI zurück."""
        if package_name in self._cache:
            return self._cache[package_name]

        url = self._base_url.format(package_name=package_name)
        match self._http.get(url):
            case Ok(response) if response.status_code == 404:
                result: Result[Version, RegistryError] = Err(
                    PackageNotFoundError(f"Package '{package_name}' nicht auf PyPI gefunden")
                )
            case Ok(response) if response.status_code == 200:
                try:
                    data = response.json()
                    version_str = data["info"]["version"]
                    result = Ok(Version.from_string(version_str))
                except (KeyError, ValueError) as e:
                    result = Err(RegistryError(f"Ungültige PyPI-Antwort für {package_name}: {e}"))
            case Ok(response):
                result = Err(RegistryError(f"PyPI HTTP {response.status_code} für {package_name}"))
            case Err(http_error):
                if http_error.is_timeout:
                    result = Err(RegistryTimeoutError(f"Timeout für {package_name}"))
                else:
                    result = Err(
                        RegistryNetworkError(f"Netzwerkfehler für {package_name}: {http_error}")
                    )

        self._cache[package_name] = result
        return result

    def get_latest_versions_batch(
        self, package_names: list[str]
    ) -> dict[str, Result[Version, RegistryError]]:
        """Fragt mehrere Package-Versionen parallel ab."""
        results: dict[str, Result[Version, RegistryError]] = {}

        # Bereits gecachte Ergebnisse sofort verwenden
        uncached = []
        for name in package_names:
            if name in self._cache:
                results[name] = self._cache[name]
            else:
                uncached.append(name)

        if not uncached:
            return results

        # Parallele Abfrage für ungecachte Packages
        futures = {self._executor.submit(self.get_latest_version, name): name for name in uncached}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = Err(RegistryError(f"Fehler für {name}: {e}"))

        return results
