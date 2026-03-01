"""
Example: Custom analyze → apply → report pipeline.

Demonstrates building a full dependency update pipeline using dependapy's
Python API with the Result pattern for error handling.

Usage:
    uv run python examples/custom_pipeline.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from dependapy.application.config import AppConfig
from dependapy.bootstrap import bootstrap
from dependapy.domain.result import Err, Ok

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def run_pipeline(project_path: Path, *, dry_run: bool = True) -> int:
    """Run a custom analyze → apply → report pipeline.

    Args:
        project_path: Path to the project root containing pyproject.toml.
        dry_run: If True, only analyze without applying changes.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    config = AppConfig.from_env(vcs_provider="offline")

    with bootstrap(config) as app:
        # ── Step 1: Analyze ──────────────────────────────────────────
        print(f"Analyzing {project_path} ...")
        match app.analyze.execute(project_path):
            case Ok(results):
                pass
            case Err(error):
                print(f"Analysis failed: {error}")
                return 1

        # ── Step 2: Report ───────────────────────────────────────────
        total_outdated = sum(r.outdated_count for r in results)
        total_deps = sum(r.total_count for r in results)

        print(
            f"\nFound {total_outdated}/{total_deps} outdated dependencies "
            f"across {len(results)} project(s).\n"
        )

        for result in results:
            if result.outdated_count == 0:
                print(f"  {result.project.name}: all up-to-date")
                continue

            print(f"  {result.project.name}: {result.outdated_count} outdated")
            for dep in result.project.get_outdated():
                print(
                    f"    - {dep.spec.name}: "
                    f"{dep.current_version} → {dep.latest_version} "
                    f"({dep.update_type()})"
                )

        if total_outdated == 0:
            print("\nNothing to update.")
            return 0

        if dry_run:
            print("\nDry run — no changes applied.")
            return 0

        # ── Step 3: Apply Updates ────────────────────────────────────
        print("\nApplying updates ...")
        match app.apply.execute(results):
            case Ok(update_result):
                print(f"  Updated {len(update_result.updated_files)} file(s)")
                if update_result.error_count > 0:
                    print(f"  Errors: {update_result.error_count}")
                for f in update_result.updated_files:
                    print(f"    → {f}")
            case Err(error):
                print(f"Update failed: {error}")
                return 1

    print("\nDone.")
    return 0


def main() -> int:
    """Run the pipeline on the example project."""
    project_path = Path(__file__).parent / "example_py_project"

    if not (project_path / "pyproject.toml").exists():
        print(f"Error: No pyproject.toml found at {project_path}")
        return 1

    # Set dry_run=False to actually modify pyproject.toml
    return run_pipeline(project_path, dry_run=True)


if __name__ == "__main__":
    sys.exit(main())
