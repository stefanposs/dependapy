#!/usr/bin/env python3
"""
dependapy - A custom dependabot alternative for Python projects
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dependapy.analyzer import scan_repository
from dependapy.github_api import create_or_update_pull_request
from dependapy.updater import update_dependencies

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("dependapy")


def main():
    """Main entry point for dependapy"""
    parser = argparse.ArgumentParser(description="Analyze and update Python dependencies")
    parser.add_argument(
        "--repo-path",
        default=str(Path.cwd()),
        help="Path to the repository to scan (default: current directory)",
    )
    parser.add_argument(
        "--no-pr",
        action="store_true",
        help="Don't create a pull request, just update files locally",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GitHub token (default: from GITHUB_TOKEN environment variable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't make any changes, just report what would be changed",
    )
    args = parser.parse_args()

    repo_path = Path(args.repo_path)
    dry_run = args.dry_run
    create_pr = not args.no_pr and not dry_run

    try:
        # Analyze repository
        logger.info("Analyzing repository at %s", repo_path)
        results = scan_repository(repo_path)

        if not results:
            logger.info("No dependencies need updating")
            return 0

        if dry_run:
            logger.info("Dry run - would update dependencies in %d files", len(results))
            return 0

        # Update dependencies
        update_results = update_dependencies(results)
        updated_files = [r.file_path for r in update_results if r.modified]

        if not updated_files:
            logger.info("No files were modified")
            return 0

        if create_pr:
            # Create PR with the changes
            # Note: PR title and body are determined in the github_api.py module
            # Create or update a pull request
            branch_name = "dependapy/dependency-updates"  # Define a branch name
            github_token = os.environ.get("GITHUB_TOKEN", args.token)

            pr_url = create_or_update_pull_request(
                repo_path=repo_path,
                branch_name=branch_name,
                updated_files=updated_files,
                github_token=github_token,
            )
            logger.info("Pull request created at %s", pr_url)
        else:
            logger.info("Updated dependencies in %d files", len(updated_files))
    except Exception:
        logger.exception("Error running dependapy")
        return 1


if __name__ == "__main__":
    sys.exit(main())
