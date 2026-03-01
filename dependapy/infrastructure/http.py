"""
HTTP Client — Wrapper um requests mit Retry-Logik.

Zentralisiert alle HTTP-Aufrufe und bietet:
- Automatische Retries mit Exponential Backoff
- Einheitliches Timeout-Handling
- Result-basierte Fehlerbehandlung
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dependapy.domain.result import Err, Ok, Result

logger = logging.getLogger("dependapy.infrastructure.http")


@dataclass(frozen=True, slots=True)
class HttpError:
    """Fehler bei HTTP-Operationen.

    Kein Exception-Subtyp — wird ausschließlich in Err() gewrappt, nie geraised.
    """

    message: str
    status_code: int | None = None
    is_timeout: bool = False

    def __str__(self) -> str:
        return self.message


class HttpClient:
    """HTTP-Client mit eingebautem Retry und Timeout."""

    def __init__(self, timeout: int = 10, max_retries: int = 3) -> None:
        self._timeout = timeout
        self._session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def get(self, url: str, **kwargs: Any) -> Result[requests.Response, HttpError]:  # noqa: ANN401
        """Führt einen GET-Request aus."""
        try:
            response = self._session.get(url, timeout=self._timeout, **kwargs)
            return Ok(response)
        except requests.Timeout as e:
            logger.warning("HTTP Timeout: %s", url)
            return Err(HttpError(message=f"Timeout: {e}", is_timeout=True))
        except requests.ConnectionError as e:
            logger.warning("HTTP Connection Error: %s", url)
            return Err(HttpError(message=f"Connection Error: {e}"))
        except requests.RequestException as e:
            logger.warning("HTTP Request Error: %s — %s", url, e)
            return Err(HttpError(message=str(e)))

    def post(
        self,
        url: str,
        *,
        json: dict | None = None,
        headers: dict | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> Result[requests.Response, HttpError]:
        """Führt einen POST-Request aus."""
        try:
            response = self._session.post(
                url, json=json, headers=headers, timeout=self._timeout, **kwargs
            )
            return Ok(response)
        except requests.Timeout as e:
            return Err(HttpError(message=f"Timeout: {e}", is_timeout=True))
        except requests.ConnectionError as e:
            return Err(HttpError(message=f"Connection Error: {e}"))
        except requests.RequestException as e:
            return Err(HttpError(message=str(e)))

    def close(self) -> None:
        """Schließt die Session."""
        self._session.close()
