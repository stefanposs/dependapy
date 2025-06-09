#!/usr/bin/env python3
"""
dependapy - A custom dependabot alternative for Python projects
"""
import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

from dependapy.analyzer import scan_repository
from dependapy.updater import update_dependencies
from dependapy.github_api import create_or_update_pull_request

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
        default=os.getcwd(),
        help="Path to the repository to scan (default: current directory)"
    )
    parser.add_argument(
        "--token", 
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub token (default: from GITHUB_TOKEN environment variable)"
    )
    parser.add_argument(
        "--no-pr", 
        action="store_true", 
        help="Don't create or update pull requests, just show what would be updated"
    )
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    logger.info(f"Scanning repository at {repo_path}")

    # Step 1: Scan the repository for pyproject.toml files
    analysis_results = scan_repository(repo_path)
    if not analysis_results:
        logger.info("No pyproject.toml files found or no updates needed.")
        return 0

    # Step 2: Update dependencies in the found pyproject.toml files
    update_results = update_dependencies(analysis_results)
    if not update_results:
        logger.info("No updates were made.")
        return 0
    
    # Step 3: Create or update a pull request if changes were made
    if not args.no_pr and args.token:
        today = datetime.now().strftime("%Y-%m-%d")
        branch_name = f"dependapy/update-{today}"
        
        try:
            pr_url = create_or_update_pull_request(
                repo_path=repo_path,
                branch_name=branch_name,
                updated_files=[result.file_path for result in update_results],
                github_token=args.token
            )
            logger.info(f"Pull request created or updated: {pr_url}")
        except Exception as e:
            logger.error(f"Failed to create pull request: {e}")
            return 1
    elif not args.token and not args.no_pr:
        logger.warning("GitHub token not provided. Skipping pull request creation.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
