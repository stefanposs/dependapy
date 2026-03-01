"""
Application Configuration — Frozen Dataclass + os.environ.

Liest DEPENDAPY_* Umgebungsvariablen und optional .env-Dateien.
Kein pydantic nötig — stdlib reicht.
"""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass, field, fields
from enum import StrEnum
from pathlib import Path


class VCSProvider(StrEnum):
    """Unterstützte VCS Provider."""

    GITHUB = "github"
    OFFLINE = "offline"


def _load_dotenv(path: Path = Path(".env")) -> None:
    """Minimaler .env-Loader — liest KEY=VALUE Zeilen in os.environ."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:  # bestehende Env-Vars haben Vorrang
            os.environ[key] = value


def _env(name: str, default: str = "") -> str:
    """Liest DEPENDAPY_{name} aus os.environ mit Fallback."""
    return os.environ.get(f"DEPENDAPY_{name}", default)


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Zentrale Konfiguration für dependapy.

    Erstelle via ``AppConfig.from_env()`` — liest DEPENDAPY_* Umgebungsvariablen.
    Direkte Konstruktion ebenfalls möglich für Tests.
    """

    # Registry URLs
    pypi_base_url: str = "https://pypi.org/pypi/{package_name}/json"
    python_eol_api_url: str = "https://endoflife.date/api/python.json"

    # API Einstellungen
    api_timeout: int = 10
    num_latest_python_versions: int = 3

    # VCS Provider (default: offline — kein Token nötig, funktioniert auf jedem Runner)
    vcs_provider: VCSProvider = VCSProvider.OFFLINE
    vcs_token: str | None = field(default=None, repr=False)
    vcs_base_branch: str = "main"
    branch_prefix: str = "dependapy/"

    # Logging
    log_level: str = "INFO"

    # Policy (Phase 2)
    policy_file: str = ".dependapy.yml"

    @classmethod
    def from_env(cls, **overrides: object) -> AppConfig:
        """Erstellt AppConfig aus DEPENDAPY_* Umgebungsvariablen.

        ``overrides`` überschreiben Env-Werte (z.B. aus CLI-Argumenten).
        """
        _load_dotenv()

        # slots=True → cls.attr liefert Deskriptoren; defaults via fields() holen
        fd: dict[str, object] = {
            f.name: f.default for f in fields(cls) if f.default is not dataclasses.MISSING
        }

        defaults: dict[str, object] = {
            "pypi_base_url": _env("PYPI_BASE_URL", str(fd.get("pypi_base_url", ""))),
            "python_eol_api_url": _env("PYTHON_EOL_API_URL", str(fd.get("python_eol_api_url", ""))),
            "api_timeout": int(_env("API_TIMEOUT", str(fd.get("api_timeout", 10)))),
            "num_latest_python_versions": int(
                _env("NUM_LATEST_PYTHON_VERSIONS", str(fd.get("num_latest_python_versions", 3)))
            ),
            "vcs_provider": VCSProvider(
                _env("VCS_PROVIDER", str(fd.get("vcs_provider", VCSProvider.OFFLINE.value)))
            ),
            "vcs_token": _env("VCS_TOKEN") or None,
            "vcs_base_branch": _env("VCS_BASE_BRANCH", str(fd.get("vcs_base_branch", "main"))),
            "branch_prefix": _env("BRANCH_PREFIX", str(fd.get("branch_prefix", "dependapy/"))),
            "log_level": _env("LOG_LEVEL", str(fd.get("log_level", "INFO"))),
            "policy_file": _env("POLICY_FILE", str(fd.get("policy_file", ".dependapy.yml"))),
        }

        # CLI-Overrides haben höchste Priorität
        defaults.update({k: v for k, v in overrides.items() if v is not None})

        return cls(**defaults)  # type: ignore[arg-type]
