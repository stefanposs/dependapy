"""
Module for creating Git patches without requiring GitHub API access
"""

import logging
import os
import subprocess
from pathlib import Path

from dependapy.constants import SENTINEL, SentinelType

logger = logging.getLogger("dependapy.offline_pr")


def create_git_patch(
    repo_path: Path, branch_name: str, updated_files: list[Path], output_path: str
) -> str | SentinelType:
    """
    Create a Git patch file for the changes instead of creating a PR.

    This is useful for environments where GitHub API access is restricted.

    Args:
        repo_path: Path to the Git repository
        branch_name: Name of the branch to create for changes
        updated_files: List of files that were updated
        output_path: Path where to save the patch file

    Returns:
        Path to the created patch file or SENTINEL if creation fails
    """
    current_branch = None
    try:
        # Save current branch
        current_branch = subprocess.check_output(
            ["git", "-C", str(repo_path), "branch", "--show-current"], text=True
        ).strip()

        # Create and checkout a new branch for the changes
        try:
            # Try to create new branch
            subprocess.run(
                ["git", "-C", str(repo_path), "checkout", "-b", branch_name],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            # Branch might already exist, try to check it out
            subprocess.run(
                ["git", "-C", str(repo_path), "checkout", branch_name], check=True
            )

        # Add all updated files to git
        for file_path in updated_files:
            subprocess.run(
                ["git", "-C", str(repo_path), "add", str(file_path)], check=True
            )

        # Commit changes
        commit_message = "chore(dependapy): update dependencies [offline-mode]"
        subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", commit_message], check=True
        )

        # Generate patch
        abs_output_path = os.path.abspath(output_path)
        with open(abs_output_path, "w") as output_file:
            subprocess.run(
                ["git", "-C", str(repo_path), "format-patch", "HEAD^", "--stdout"],
                check=True,
                stdout=output_file,
            )

        # Return to original branch
        subprocess.run(
            ["git", "-C", str(repo_path), "checkout", current_branch], check=True
        )

        logger.info("Created Git patch at %s", abs_output_path)
        return abs_output_path

    except subprocess.CalledProcessError as e:
        logger.error("Git operation failed: %s", e)
        logger.error(
            "Command output: %s", e.stdout if hasattr(e, "stdout") else "No output"
        )
        # Try to return to the original branch if we know it
        if current_branch:
            try:
                subprocess.run(
                    ["git", "-C", str(repo_path), "checkout", current_branch],
                    check=True,
                )
            except Exception as checkout_error:
                # If this fails too, we can't do much about it
                logger.error("Failed to return to original branch: %s", checkout_error)
        return SENTINEL
    except Exception as e:
        # Handle any other exceptions that might occur
        logger.error("Error creating Git patch: %s", e)
        # Try to return to the original branch if we know it
        if current_branch:
            try:
                subprocess.run(
                    ["git", "-C", str(repo_path), "checkout", current_branch],
                    check=False,  # Don't fail if this fails too
                )
            except Exception as checkout_error:
                logger.error("Failed to return to original branch: %s", checkout_error)
        return SENTINEL
