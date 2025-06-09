"""
Analyzer module for scanning pyproject.toml files and checking for updates
"""

import logging
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib

import requests
from packaging.version import parse

logger = logging.getLogger("dependapy.analyzer")


# Get the three latest Python minor versions
def get_latest_python_versions() -> list[str]:
    """Get the three latest Python 3.x minor versions"""
    try:
        response = requests.get("https://endoflife.date/api/python.json", timeout=10)
        response.raise_for_status()
        python_versions = response.json()

        # Filter for Python 3.x versions and sort
        py3_versions = [v["cycle"] for v in python_versions if v["cycle"].startswith("3.")]
        py3_versions.sort(key=lambda x: parse(x), reverse=True)

        # Get the three latest minor versions
        latest_versions = py3_versions[:3]
        logger.info("Latest Python versions: %s", ", ".join(latest_versions))
    except Exception:
        logger.exception("Failed to get latest Python versions")
        # Fallback to hard-coded versions if API fails
        return ["3.12", "3.11", "3.10"]
    else:
        return latest_versions


# Cache for PyPI package versions to avoid repeated requests
_PYPI_CACHE: dict[str, str | None] = {}


def get_latest_version(package_name: str) -> str | None:
    """Get the latest version of a package from PyPI"""
    if package_name in _PYPI_CACHE:
        return _PYPI_CACHE[package_name]

    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=10)
        if response.status_code == 404:
            logger.warning("Package %s not found on PyPI", package_name)
            _PYPI_CACHE[package_name] = None
            return None

        response.raise_for_status()
        data = response.json()
        latest_version = data["info"]["version"]
        _PYPI_CACHE[package_name] = latest_version
    except Exception:
        logger.exception("Error fetching version for %s", package_name)
        _PYPI_CACHE[package_name] = None
        return None
    else:
        return latest_version


def parse_dependency_version(dependency_spec: str) -> tuple[str, str]:
    """Parse package and version from a dependency specifier"""
    # Remove quotes if present
    if dependency_spec.startswith('"') and dependency_spec.endswith('"'):
        dependency_spec = dependency_spec[1:-1]

    # Check for version specifiers
    if ">=" in dependency_spec:
        parts = dependency_spec.split(">=")
        package = parts[0].strip()
        version = parts[1].strip()
    elif "==" in dependency_spec:
        parts = dependency_spec.split("==")
        package = parts[0].strip()
        version = parts[1].strip()
    else:
        # No version specifier found
        package = dependency_spec.strip()
        version = ""

    return package, version


@dataclass
class UpdateInfo:
    """Information about a package that needs an update"""

    package_name: str
    current_version: str
    latest_version: str
    file_path: Path


@dataclass
class PythonVersionUpdateInfo:
    """Information about Python version that needs an update"""

    current_constraint: str
    recommended_constraint: str
    file_path: Path


@dataclass
class FileAnalysisResult:
    """Result of analyzing a pyproject.toml file"""

    file_path: Path
    package_updates: list[UpdateInfo]
    python_update: PythonVersionUpdateInfo | None = None


def scan_file(file_path: Path, latest_python_versions: list[str]) -> FileAnalysisResult | None:
    """Scan a single pyproject.toml file for updates"""
    logger.info("Analyzing %s", file_path)

    try:
        with file_path.open("rb") as f:
            pyproject = tomllib.load(f)
    except Exception:
        logger.exception("Failed to parse %s", file_path)
        return None

    project_section = pyproject.get("project", {})
    if not project_section:
        logger.warning("No [project] section in %s, skipping", file_path)
        return None

    # Check Python version constraint
    python_update = None
    requires_python = project_section.get("requires-python")
    if requires_python:
        min_python_version = get_min_python_version(requires_python)
        if min_python_version and min_python_version not in latest_python_versions:
            # We should update the Python version constraint
            min_latest = min(latest_python_versions, key=lambda v: parse(v))
            recommended = f">={min_latest}"
            python_update = PythonVersionUpdateInfo(
                current_constraint=requires_python,
                recommended_constraint=recommended,
                file_path=file_path,
            )
            logger.info(
                "Python version update needed in %s: %s -> %s",
                file_path,
                requires_python,
                recommended,
            )

    # Check dependencies
    dependencies = project_section.get("dependencies", [])
    optional_deps = project_section.get("optional-dependencies", {})

    # Process main dependencies
    all_deps = list(dependencies)

    # Process optional dependencies
    for deps in optional_deps.values():
        all_deps.extend(deps)

    # Check for updates
    package_updates = []
    for dep in all_deps:
        package_name, current_version = parse_dependency_version(dep)
        if not current_version:  # Skip if we couldn't extract a version
            continue

        latest_version = get_latest_version(package_name)
        if not latest_version:
            continue

        if parse(latest_version) > parse(current_version):
            update = UpdateInfo(
                package_name=package_name,
                current_version=current_version,
                latest_version=latest_version,
                file_path=file_path,
            )
            package_updates.append(update)
            logger.info(
                "Update needed for %s: %s -> %s",
                package_name,
                current_version,
                latest_version,
            )

    if not package_updates and not python_update:
        logger.info("No updates needed for %s", file_path)
        return None

    return FileAnalysisResult(
        file_path=file_path,
        package_updates=package_updates,
        python_update=python_update,
    )


def get_min_python_version(requires_python: str) -> str | None:
    """Extract minimum Python version from requires-python constraint"""
    # Handle common formats like ">=3.8", ">=3.8,<4.0", ">=3.8.0"
    if requires_python.startswith(">="):
        version_part = requires_python.split(",")[0].strip()[2:]
        # Ensure we get just the minor version (3.x)
        if version_part.startswith("3."):
            parts = version_part.split(".")
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
    return None


def scan_repository(repo_path: Path) -> list[FileAnalysisResult]:
    """Scan repository for pyproject.toml files and analyze them"""
    latest_python_versions = get_latest_python_versions()

    # Find all pyproject.toml files recursively
    pyproject_files = list(repo_path.glob("**/pyproject.toml"))
    logger.info("Found %d pyproject.toml files", len(pyproject_files))

    results = []
    for file_path in pyproject_files:
        result = scan_file(file_path, latest_python_versions)
        if result:
            results.append(result)

    return results
