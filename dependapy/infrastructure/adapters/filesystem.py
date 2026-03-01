"""
FileSystem Project Repository — Implementiert ProjectRepository Port.

Liest und schreibt pyproject.toml-Dateien.
"""

from __future__ import annotations

import contextlib
import logging
import re
import tomllib  # stdlib since Python 3.11, required by requires-python>=3.12
from itertools import chain
from pathlib import Path

from dependapy.domain.errors import ProjectError, ProjectParseError, ProjectWriteError
from dependapy.domain.models import Dependency, Project
from dependapy.domain.result import Err, Ok, Result
from dependapy.domain.value_objects import (
    ConstraintOperator,
    PackageSpec,
    Version,
    VersionConstraint,
)

logger = logging.getLogger("dependapy.infrastructure.adapters.filesystem")


class FileSystemProjectRepository:
    """Liest und schreibt Python-Projekte aus/in pyproject.toml.

    Implementiert das ProjectRepository Protocol.
    """

    def load_project(self, path: Path) -> Result[Project, ProjectError]:
        """Lädt ein Projekt aus einer pyproject.toml-Datei."""
        try:
            with path.open("rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            return Err(ProjectParseError(f"Konnte {path} nicht parsen: {e}"))

        project_section = data.get("project", {})
        if not project_section:
            return Err(ProjectParseError(f"Kein [project] Abschnitt in {path}"))

        name = project_section.get("name", path.parent.name)

        # Python Version Constraint
        python_constraint = None
        requires_python = project_section.get("requires-python")
        if requires_python:
            python_constraint = self._parse_constraint(requires_python)

        # Dependencies parsen — alle Quellen mit itertools.chain zusammenführen
        main_deps = project_section.get("dependencies", [])
        optional_deps = (
            (dep_str, group_name)
            for group_name, deps in project_section.get("optional-dependencies", {}).items()
            for dep_str in deps
        )
        dep_group_deps = (
            (dep_str, group_name)
            for group_name, deps in data.get("dependency-groups", {}).items()
            for dep_str in deps
            if isinstance(dep_str, str)
        )

        dependencies: list[Dependency] = [
            dep
            for dep_str, group in chain(
                ((d, "main") for d in main_deps),
                optional_deps,
                dep_group_deps,
            )
            if (dep := self._parse_dependency(dep_str, path, group=group)) is not None
        ]

        project = Project(
            name=name,
            path=path,
            python_constraint=python_constraint,
            dependencies=dependencies,
        )

        logger.info("Projekt geladen: %s (%d Dependencies)", name, len(dependencies))
        return Ok(project)

    def save_project(self, project: Project) -> Result[None, ProjectError]:
        """Speichert Änderungen an einem Projekt zurück in die pyproject.toml."""
        try:
            content = project.path.read_text(encoding="utf-8")
        except OSError as e:
            return Err(ProjectWriteError(f"Konnte {project.path} nicht lesen: {e}"))

        modified = False

        for dep in project.dependencies:
            if dep.latest_version is None or not dep.is_outdated():
                continue

            current_str = str(dep.current_version)
            new_str = str(dep.latest_version)
            package_name = dep.spec.name

            # Pattern: package_name mit >=, == oder ~= und current_version.
            # Negative lookbehind/lookahead ensures whole-name match (prevents
            # "requests" from matching "requests-oauthlib" etc.).
            pattern = (
                r"([\"']?(?<![a-zA-Z0-9._-])"
                f"{re.escape(package_name)}"
                r"(?:\[[^\]]*\])?"
                r"(?![a-zA-Z0-9._-])[\"']?\s*(?:>=|==|~=)\s*)"
                f"([\"']?){re.escape(current_str)}([\"']?)([^\\n]*)"
            )

            def _replacement(match: re.Match, version: str = new_str) -> str:
                prefix = match.group(1)
                q_start = match.group(2)
                q_end = match.group(3)
                suffix = match.group(4) or ""
                return f"{prefix}{q_start}{version}{q_end}{suffix}"

            # Apply only to non-comment lines to avoid matching inside comments.
            lines = content.split("\n")
            new_lines: list[str] = []
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    new_lines.append(line)
                else:
                    new_lines.append(re.sub(pattern, _replacement, line))
            new_content = "\n".join(new_lines)
            if new_content != content:
                content = new_content
                modified = True
                logger.info("Updated %s: %s → %s", package_name, current_str, new_str)

        # Python Version Constraint
        if project.python_constraint is not None:
            # TODO: Python version update logic (Phase 2)
            pass

        if modified:
            try:
                project.path.write_text(content, encoding="utf-8")
                logger.info("Gespeichert: %s", project.path)
            except OSError as e:
                return Err(ProjectWriteError(f"Konnte {project.path} nicht schreiben: {e}"))

        return Ok(None)

    def find_project_files(self, root: Path) -> Result[list[Path], ProjectError]:
        """Findet alle pyproject.toml-Dateien rekursiv."""
        try:
            files = list(root.glob("**/pyproject.toml"))
            logger.info("Gefunden: %d pyproject.toml Dateien in %s", len(files), root)
            return Ok(files)
        except OSError as e:
            return Err(ProjectError(f"Fehler beim Suchen in {root}: {e}"))

    @staticmethod
    def _parse_dependency(
        dep_str: str, source_file: Path, group: str = "main"
    ) -> Dependency | None:
        """Parst einen Dependency-String wie 'requests==2.32.4'."""
        dep_str = dep_str.strip().strip("'\"")

        # Extras extrahieren: uvicorn[standard]>=0.30.0 → name="uvicorn", extras={"standard"}
        extras: frozenset[str] = frozenset()
        extras_match = re.match(r"^([a-zA-Z0-9._-]+)\[([^\]]+)\]", dep_str)
        if extras_match:
            base_name = extras_match.group(1)
            extras = frozenset(e.strip() for e in extras_match.group(2).split(","))
            dep_str = base_name + dep_str[extras_match.end() :]  # Remove extras bracket

        for op in (">=", "==", "~="):
            if op in dep_str:
                parts = dep_str.split(op, 1)
                name = parts[0].strip()
                version_str = parts[1].strip().split(",")[0].strip()

                try:
                    version = Version.from_string(version_str)
                    constraint_op = ConstraintOperator(op)
                    constraint = VersionConstraint(operator=constraint_op, version=version)
                    spec = PackageSpec(
                        name=name,
                        version_constraint=constraint,
                        extras=extras,
                    )
                    return Dependency(
                        spec=spec,
                        current_version=version,
                        source_file=source_file,
                        dependency_group=group,
                    )
                except (ValueError, KeyError):
                    logger.warning("Konnte Version nicht parsen: %s", dep_str)
                    return None

        # Kein Version-Operator gefunden
        return None

    @staticmethod
    def _parse_constraint(constraint_str: str) -> VersionConstraint | None:
        """Parst einen Python-Version-Constraint wie '>=3.11' oder '>=3.11,<4.0'."""
        constraint_str = constraint_str.strip()
        for op in (">=", "==", "~="):
            if constraint_str.startswith(op):
                parts = constraint_str[len(op) :].split(",")
                version_str = parts[0].strip()
                upper_bound: Version | None = None
                if len(parts) > 1:
                    ub_str = parts[1].strip()
                    if ub_str.startswith("<"):
                        with contextlib.suppress(Exception):
                            upper_bound = Version.from_string(ub_str[1:].strip())
                try:
                    return VersionConstraint(
                        operator=ConstraintOperator(op),
                        version=Version.from_string(version_str),
                        upper_bound=upper_bound,
                    )
                except (ValueError, KeyError):
                    return None
        return None
