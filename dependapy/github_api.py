"""
GitHub API module for creating and updating pull requests
"""

import importlib.util
import logging
import os
import subprocess
from pathlib import Path

from dependapy.constants import SENTINEL, SentinelType

logger = logging.getLogger("dependapy.github_api")


def get_repo_info(repo_path: Path) -> tuple[str, str] | SentinelType:
    """
    Get repository owner and name from remote URL
    Returns a tuple of (owner, repo) or SENTINEL if the info could not be retrieved
    """
    try:
        # Get the remote URL
        remote_url = subprocess.check_output(  # nosec B607
            ["git", "-C", str(repo_path), "config", "--get", "remote.origin.url"],
            text=True,
        ).strip()

        # Parse URL to extract owner and repo name
        if "github.com" in remote_url:
            # Handle SSH format: git@github.com:owner/repo.git
            if remote_url.startswith("git@"):
                path = remote_url.split(":", 1)[1]
            # Handle HTTPS format: https://github.com/owner/repo.git
            else:
                path = remote_url.split("github.com/", 1)[1]

            # Remove .git suffix if present
            if path.endswith(".git"):
                path = path[:-4]

            parts = path.split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
    except Exception:
        logger.exception("Failed to get repository info")

    return SENTINEL


def create_or_update_pull_request(
    repo_path: Path,
    branch_name: str,
    updated_files: list[Path],
    github_token: str,
) -> str:
    """
    Create or update a pull request with dependency updates

    Uses PyGithub if available, falls back to gh CLI if installed

    Returns the URL of the created/updated pull request
    """
    # First try using PyGithub
    try:
        # Check if PyGithub is available
        if importlib.util.find_spec("github") is not None:
            logger.info("Using PyGithub for PR creation")
            return create_pr_with_pygithub(
                repo_path=repo_path,
                branch_name=branch_name,
                updated_files=updated_files,
                github_token=github_token,
            )
    except ImportError:
        logger.info("PyGithub not available, trying gh CLI")

    # Fall back to gh CLI if PyGithub is not available
    try:
        return create_pr_with_gh_cli(
            repo_path=repo_path,
            branch_name=branch_name,
            updated_files=updated_files,
            github_token=github_token,
        )
    except Exception as exc:
        logger.exception("Failed to create PR with gh CLI")
        error_message = "Could not create PR with either PyGithub or gh CLI"
        raise RuntimeError(error_message) from exc


def create_pr_with_pygithub(
    repo_path: Path,
    branch_name: str,
    updated_files: list[Path],
    github_token: str,
) -> str:
    """Create or update a PR using PyGithub"""
    try:
        from github import Github
    except ImportError as exc:
        error_message = "PyGithub package is required but not installed"
        raise ImportError(error_message) from exc

    # Get repository info
    repo_info = get_repo_info(repo_path)
    if repo_info is SENTINEL:
        error_message = "Could not determine repository owner and name"
        raise ValueError(error_message)

    # We've verified that repo_info is not SENTINEL, so it must be a tuple
    assert isinstance(repo_info, tuple)
    owner, repo_name = repo_info

    # Setup git for committing
    setup_git_for_commit(repo_path, branch_name)

    # Add updated files to git
    for file_path in updated_files:
        subprocess.run(["git", "-C", str(repo_path), "add", str(file_path)], check=True)

    # Check if there are changes to commit
    status = subprocess.check_output(
        ["git", "-C", str(repo_path), "status", "--porcelain"],
        text=True,
    ).strip()

    if not status:
        logger.info("No changes to commit")
        return "No changes to commit"

    # Commit changes
    commit_message = "chore(dependapy): update dependencies and python version"
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m", commit_message], check=True
    )

    # Push changes
    subprocess.run(
        ["git", "-C", str(repo_path), "push", "origin", branch_name, "--force"],
        check=True,
    )

    # Create or update PR
    g = Github(github_token)
    repo = g.get_repo(f"{owner}/{repo_name}")

    # Check for existing PR from this branch
    existing_pr = None
    for pr in repo.get_pulls(state="open"):
        if pr.head.ref == branch_name:
            existing_pr = pr
            break

    if existing_pr:
        logger.info("Updating existing PR #%s", existing_pr.number)
        return existing_pr.html_url
    else:
        # Create new PR
        pr_title = "Update dependencies and Python version"
        pr_body = (
            "This PR was automatically created by dependapy.\n\n"
            "It updates dependencies to their latest versions and ensures "
            "compatibility with the three latest Python minor versions."
        )
        new_pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            base="main",  # Assuming main is the default branch
            head=branch_name,
        )
        logger.info("Created new PR #%s", new_pr.number)
        return new_pr.html_url


def create_pr_with_gh_cli(
    repo_path: Path,
    branch_name: str,
    updated_files: list[Path],
    github_token: str,
) -> str:
    """Create or update a PR using the gh CLI"""
    # Setup git for committing
    setup_git_for_commit(repo_path, branch_name)

    # Set environment variable for gh CLI
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = github_token

    # Add updated files to git
    for file_path in updated_files:
        subprocess.run(["git", "-C", str(repo_path), "add", str(file_path)], check=True)

    # Check if there are changes to commit
    status = subprocess.check_output(
        ["git", "-C", str(repo_path), "status", "--porcelain"],
        text=True,
    ).strip()

    if not status:
        logger.info("No changes to commit")
        return "No changes to commit"

    # Commit changes
    commit_message = "chore(dependapy): update dependencies and python version"
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m", commit_message], check=True
    )

    # Push changes
    subprocess.run(
        ["git", "-C", str(repo_path), "push", "origin", branch_name, "--force"],
        check=True,
    )

    # Check if PR already exists
    pr_exists = False
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch_name, "--json", "number"],
            cwd=repo_path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        pr_exists = (
            len(result.stdout.strip()) > 2
        )  # Check if output is more than empty JSON array
    except subprocess.CalledProcessError:
        pr_exists = False

    if pr_exists:
        # PR exists, just get its URL
        result = subprocess.run(
            ["gh", "pr", "view", "--head", branch_name, "--json", "url"],
            cwd=repo_path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        import json

        pr_url = json.loads(result.stdout)["url"]
        logger.info("Existing PR updated: %s", pr_url)
        return pr_url
    else:
        # Create new PR
        pr_title = "Update dependencies and Python version"
        pr_body = (
            "This PR was automatically created by dependapy.\n\n"
            "It updates dependencies to their latest versions and ensures "
            "compatibility with the three latest Python minor versions."
        )

        result = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                pr_title,
                "--body",
                pr_body,
                "--head",
                branch_name,
            ],
            cwd=repo_path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        pr_url = result.stdout.strip()
        logger.info("Created new PR: %s", pr_url)
        return pr_url


def setup_git_for_commit(repo_path: Path, branch_name: str) -> None:
    """Configure git for making commits"""
    # Configure git user
    subprocess.run(
        ["git", "-C", str(repo_path), "config", "user.name", "dependapy-bot"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_path),
            "config",
            "user.email",
            "dependapy-bot@noreply.github.com",
        ],
        check=True,
    )

    # Check if we're in a GitHub Actions environment
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # GitHub Actions-specific git setup
        logger.info("Running in GitHub Actions environment")

    # Get current branch
    current_branch = subprocess.check_output(
        ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
    ).strip()

    # Create and checkout feature branch
    if current_branch != branch_name:
        # Check if branch already exists
        try:
            subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "--verify", branch_name],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Branch exists, just checkout
            subprocess.run(
                ["git", "-C", str(repo_path), "checkout", branch_name], check=True
            )
        except subprocess.CalledProcessError:
            # Branch doesn't exist, create it
            subprocess.run(
                ["git", "-C", str(repo_path), "checkout", "-b", branch_name], check=True
            )
