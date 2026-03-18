"""
YAML Policy Loader — Lädt und validiert .dependapy.yml Dateien.

Unterstütztes Format:

    version: 1
    ignore:
      - name: "boto*"
        reason: "managed by infra team"
      - name: "legacy-pkg"
    allow:
      - name: "*"
        update-types: ["minor", "patch"]
      - name: "requests"
        update-types: ["major", "minor", "patch"]
    labels: ["dependencies", "automated"]
    reviewers: ["@user1", "@org/team"]
    assignees: ["@user2"]
    commit-message:
      prefix: "chore(deps)"
      include-scope: true
    groups:
      - name: "aws"
        patterns: ["boto*", "aws*"]
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from dependapy.domain.errors import PolicyError, PolicyNotFoundError, PolicyValidationError
from dependapy.domain.policy import (
    AllowRule,
    CommitMessage,
    DependencyGroup,
    IgnoreRule,
    Policy,
)
from dependapy.domain.result import Err, Ok, Result

logger = logging.getLogger("dependapy.infrastructure.adapters.policy_loader")


def load_policy(project_root: Path) -> Result[Policy, PolicyError]:
    """Lädt eine .dependapy.yml Policy-Datei aus dem Projekt-Root.

    Returns:
        Ok(Policy) wenn die Datei existiert und valide ist.
        Err(PolicyNotFoundError) wenn keine Policy-Datei gefunden wird.
        Err(PolicyValidationError) wenn die Datei ungültig ist.
    """
    candidates = [
        project_root / ".dependapy.yml",
        project_root / ".dependapy.yaml",
        project_root / "dependapy.yml",
        project_root / "dependapy.yaml",
    ]

    policy_path: Path | None = None
    for candidate in candidates:
        if candidate.is_file():
            policy_path = candidate
            break

    if policy_path is None:
        return Err(PolicyNotFoundError("Keine .dependapy.yml gefunden"))

    logger.info("Policy geladen: %s", policy_path)

    try:
        import yaml
    except ImportError:
        # PyYAML nicht installiert — parse manuell nicht möglich
        # Fallback: versuche tomllib falls es eine TOML-Section ist
        return Err(
            PolicyValidationError(
                "PyYAML ist nicht installiert. "
                "Installiere mit: pip install dependapy[policy] oder pip install pyyaml"
            )
        )

    try:
        raw = policy_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        return Err(PolicyValidationError(f"YAML-Syntax-Fehler in {policy_path}: {e}"))

    if not isinstance(data, dict):
        return Err(PolicyValidationError("Policy-Datei muss ein YAML-Dictionary sein"))

    return _parse_policy(data)


def _parse_policy(
    data: dict[str, Any],
) -> Result[Policy, PolicyError]:
    """Parst ein YAML-Dictionary in ein Policy-Objekt."""
    try:
        version = int(data.get("version", 1))
        if version != 1:
            return Err(PolicyValidationError(f"Unbekannte Policy-Version: {version}"))

        ignore = _parse_ignore(data.get("ignore", []))
        allow = _parse_allow(data.get("allow", []))
        labels = tuple(str(l) for l in data.get("labels", []))  # noqa: E741
        reviewers = tuple(str(r) for r in data.get("reviewers", []))
        assignees = tuple(str(a) for a in data.get("assignees", []))
        commit_message = _parse_commit_message(data.get("commit-message", {}))
        groups = _parse_groups(data.get("groups", []))
        auto_merge = bool(data.get("auto-merge", False))

        return Ok(
            Policy(
                version=version,
                ignore=ignore,
                allow=allow,
                labels=labels,
                reviewers=reviewers,
                assignees=assignees,
                commit_message=commit_message,
                groups=groups,
                auto_merge=auto_merge,
            )
        )
    except (TypeError, ValueError, KeyError) as e:
        return Err(PolicyValidationError(f"Policy-Validierungsfehler: {e}"))


def _parse_ignore(raw: list[Any]) -> tuple[IgnoreRule, ...]:
    """Parst die ignore-Section."""
    rules: list[IgnoreRule] = []
    for item in raw:
        if isinstance(item, str):
            rules.append(IgnoreRule(name=item))
        elif isinstance(item, dict):
            rules.append(
                IgnoreRule(
                    name=str(item["name"]),
                    versions=item.get("versions"),
                    reason=item.get("reason"),
                )
            )
    return tuple(rules)


def _parse_allow(raw: list[Any]) -> tuple[AllowRule, ...]:
    """Parst die allow-Section."""
    rules: list[AllowRule] = []
    for item in raw:
        if isinstance(item, dict):
            name = str(item["name"])
            raw_types = item.get("update-types", ["major", "minor", "patch"])
            update_types = frozenset(str(t) for t in raw_types)
            rules.append(AllowRule(name=name, update_types=update_types))
    return tuple(rules)


def _parse_commit_message(raw: dict[str, Any] | None) -> CommitMessage:
    """Parst die commit-message-Section."""
    if not raw:
        return CommitMessage()
    return CommitMessage(
        prefix=str(raw.get("prefix", "chore(deps)")),
        include_scope=bool(raw.get("include-scope", True)),
    )


def _parse_groups(raw: list[Any]) -> tuple[DependencyGroup, ...]:
    """Parst die groups-Section."""
    groups: list[DependencyGroup] = []
    for item in raw:
        if isinstance(item, dict):
            groups.append(
                DependencyGroup(
                    name=str(item["name"]),
                    patterns=tuple(str(p) for p in item.get("patterns", [])),
                )
            )
    return tuple(groups)
