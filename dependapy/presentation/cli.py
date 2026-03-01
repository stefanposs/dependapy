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
    # 1. Analyze
    match app.analyze.execute(project_path):
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

    # 3. Submit Changes
    match app.submit.execute(project_path, updated_files):
        case Ok(submit_result):
            logging.info("Änderungen eingereicht: %s", submit_result.url)
            return 0
        case Err(error):
            logging.error("Einreichung fehlgeschlagen: %s", error)
            return 1


if __name__ == "__main__":
    sys.exit(cli_main())
