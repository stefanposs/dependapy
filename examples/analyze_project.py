"""
Example: Analyze project dependencies using the dependapy Python API.

Demonstrates how to bootstrap dependapy, run analysis, and inspect results.

Usage:
    uv run python examples/analyze_project.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from dependapy.application.config import AppConfig
from dependapy.bootstrap import bootstrap
from dependapy.domain.result import Err, Ok

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def main() -> int:
    """Analyze dependencies of the example project."""
    project_path = Path(__file__).parent / "example_py_project"

    if not (project_path / "pyproject.toml").exists():
        print(f"Error: No pyproject.toml found at {project_path}")
        return 1

    # Bootstrap with offline mode (no GitHub token needed)
    config = AppConfig.from_env(vcs_provider="offline")

    with bootstrap(config) as app:
        match app.analyze.execute(project_path):
            case Ok(results):
                for result in results:
                    proj = result.project
                    print(f"Project: {proj.name}")
                    print(f"  Total dependencies: {result.total_count}")
                    print(f"  Outdated:           {result.outdated_count}")
                    print(f"  Python outdated:    {result.python_outdated}")
                    print()

                    if result.outdated_count > 0:
                        print("  Outdated dependencies:")
                        for dep in proj.get_outdated():
                            print(
                                f"    {dep.spec.name}: "
                                f"{dep.current_version} → {dep.latest_version} "
                                f"({dep.update_type()})"
                            )
                        print()

                    print("  All dependencies:")
                    for dep in proj.dependencies:
                        status = "outdated" if dep.is_outdated() else "up-to-date"
                        latest = dep.latest_version or "unknown"
                        print(
                            f"    {dep.spec.name}: {dep.current_version} "
                            f"(latest: {latest}) [{status}]"
                        )

            case Err(error):
                print(f"Analysis failed: {error}")
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
