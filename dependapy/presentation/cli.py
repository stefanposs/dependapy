"""
CLI — Presentation Layer Entry Point.

Backward-compatible CLI die die neue Onion Architecture nutzt.
Entry Point bleibt bei dependapy.main:main (Delegation).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dependapy.application import Err, Ok
from dependapy.application.config import AppConfig
from dependapy.bootstrap import Application, bootstrap
from dependapy.domain.policy import Policy
from dependapy.infrastructure.adapters.codeowners import (
    find_owners_for_file,
    parse_codeowners,
)
from dependapy.infrastructure.adapters.policy_loader import load_policy


def create_parser() -> argparse.ArgumentParser:
    """Erstellt den ArgumentParser mit allen CLI-Optionen."""
    parser = argparse.ArgumentParser(
        prog="dependapy",
        description="Dependency governance for Python projects",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project root (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze only, do not apply updates",
    )
    parser.add_argument(
        "--no-pr",
        action="store_true",
        help="Apply updates but do not create a PR",
    )
    parser.add_argument(
        "--offline-pr",
        action="store_true",
        help="Create git patches instead of PRs",
    )
    parser.add_argument(
        "--provider",
        choices=["github", "offline"],
        default=None,
        help="VCS provider (default: github)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="API token for VCS provider",
    )
    parser.add_argument(
        "--base-branch",
        default=None,
        help="Base branch for PRs (default: main)",
    )
    parser.add_argument(
        "--max-prs",
        type=int,
        default=None,
        help="Maximum number of PRs to create (default: 10)",
    )
    parser.add_argument(
        "--no-codeowners",
        action="store_true",
        help="Do not assign CODEOWNERS as reviewers on PRs",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run fully offline using local version sources (uv.lock, requirements.txt)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    from dependapy import __version__

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def cli_main(argv: list[str] | None = None) -> int:
    """Haupteinstiegspunkt für die CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Logging konfigurieren
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    # Config aus CLI-Args erstellen
    config_overrides: dict[str, object] = {}
    if args.offline_pr or args.provider == "offline":
        config_overrides["vcs_provider"] = "offline"
    elif args.provider:
        config_overrides["vcs_provider"] = args.provider
    if args.token:
        config_overrides["vcs_token"] = args.token
    if args.base_branch:
        config_overrides["vcs_base_branch"] = args.base_branch
    if args.max_prs is not None:
        config_overrides["max_prs"] = args.max_prs
    if args.no_codeowners:
        config_overrides["notify_codeowners"] = False
    if args.offline:
        config_overrides["offline"] = True
        # Offline impliziert den Offline-VCS-Provider
        if "vcs_provider" not in config_overrides:
            config_overrides["vcs_provider"] = "offline"

    try:
        config = AppConfig.from_env(**config_overrides)
    except Exception as e:
        logging.error("Konfigurationsfehler: %s", e)
        return 1

    # Bootstrap
    app = bootstrap(config)
    project_path = Path(args.path).resolve()

    try:
        return _run(app, project_path, args)
    finally:
        app.close()


def _run(app: Application, project_path: Path, args: argparse.Namespace) -> int:
    """Führt die eigentliche Logik aus (Analyze → Apply → Submit)."""
    # Policy laden (optional — wenn .dependapy.yml existiert)
    policy: Policy | None = None
    match load_policy(project_path):
        case Ok(loaded_policy):
            policy = loaded_policy
            logging.info("Policy geladen aus %s", project_path)
        case Err(error):
            logging.debug("Keine Policy geladen: %s", error)

    # 1. Analyze
    match app.analyze.execute(project_path, policy=policy):
        case Ok(results):
            total_outdated = sum(r.outdated_count for r in results)
            total_deps = sum(r.total_count for r in results)
            logging.info(
                "Analyse abgeschlossen: %d/%d Dependencies veraltet in %d Projekt(en)",
                total_outdated,
                total_deps,
                len(results),
            )

            if total_outdated == 0:
                logging.info("Alle Dependencies sind aktuell.")
                return 0

        case Err(error):
            logging.error("Analyse fehlgeschlagen: %s", error)
            return 1

    if args.dry_run:
        logging.info("Dry-Run: Keine Änderungen vorgenommen.")
        return 0

    # 2. Apply Updates
    match app.apply.execute(results):
        case Ok(update_result):
            logging.info(
                "Updates angewendet: %d Dateien aktualisiert",
                len(update_result.updated_files),
            )
            updated_files = update_result.updated_files
        case Err(error):
            logging.error("Updates fehlgeschlagen: %s", error)
            return 1

    if args.no_pr:
        logging.info("Updates angewendet, kein PR erstellt (--no-pr).")
        return 0

    # 3. Submit Changes (per-project PRs mit CODEOWNERS)
    # CODEOWNERS laden
    reviewers_by_file: dict[str, list[str]] | None = None
    if app.config.notify_codeowners:
        codeowners_entries = parse_codeowners(project_path)
        if codeowners_entries:
            reviewers_by_file = {}
            for f in updated_files:
                rel = str(f.relative_to(project_path))
                owners = find_owners_for_file(rel, codeowners_entries)
                if owners:
                    reviewers_by_file[rel] = owners
                    logging.debug("CODEOWNERS für %s: %s", rel, owners)

    # Mapping: Projekt-Pfad → Dateien
    updated_files_by_project: dict[Path, list[Path]] = {}
    for r in results:
        if r.outdated_count > 0 and r.project.path in [Path(f) for f in updated_files]:
            updated_files_by_project[r.project.path] = [r.project.path]
        elif r.outdated_count > 0:
            # Match project path to updated files
            for f in updated_files:
                if f == r.project.path:
                    updated_files_by_project.setdefault(r.project.path, []).append(f)

    # Falls nur ein Projekt, nutze den einfachen Sammel-PR
    if len(updated_files_by_project) <= 1:
        # Reviewer aus CODEOWNERS sammeln
        all_reviewers: list[str] | None = None
        if reviewers_by_file:
            owners_set: set[str] = set()
            for owners in reviewers_by_file.values():
                owners_set.update(owners)
            if owners_set:
                all_reviewers = sorted(owners_set)

        match app.submit.execute(
            project_path,
            updated_files,
            reviewers=all_reviewers,
            policy=policy,
        ):
            case Ok(submit_result):
                logging.info("Änderungen eingereicht: %s", submit_result.url)
                return 0
            case Err(error):
                logging.error("Einreichung fehlgeschlagen: %s", error)
                return 1
    else:
        # Mehrere Projekte: Per-Projekt PRs mit max_prs Limit
        pr_results = app.submit.execute_per_project(
            repo_path=project_path,
            analysis_results=results,
            updated_files_by_project=updated_files_by_project,
            base_branch=app.config.vcs_base_branch,
            branch_prefix=app.config.branch_prefix,
            max_prs=app.config.max_prs,
            reviewers_by_file=reviewers_by_file,
            policy=policy,
        )

        success_count = sum(1 for r in pr_results if isinstance(r, Ok))
        error_count = sum(1 for r in pr_results if isinstance(r, Err))

        if success_count > 0:
            logging.info(
                "PRs erstellt: %d erfolgreich, %d fehlgeschlagen",
                success_count,
                error_count,
            )
            return 0
        if error_count > 0:
            logging.error("Alle PRs fehlgeschlagen.")
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(cli_main())
