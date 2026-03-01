"""
dependapy - A custom dependabot alternative for Python projects using pyproject.toml
"""

from importlib.metadata import PackageNotFoundError as _PNF  # noqa: N814
from importlib.metadata import version as _get_version

try:
    __version__ = _get_version("dependapy")
except _PNF:
    __version__ = "0.0.0-dev"
