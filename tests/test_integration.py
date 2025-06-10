"""Integration test for dependapy"""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from dependapy.analyzer import scan_repository
from dependapy.github_api import create_or_update_pull_request
from dependapy.updater import update_dependencies


@pytest.fixture
def sample_repo():
    """Create a temporary repository with sample pyproject.toml files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create .git directory to simulate a Git repository
        os.makedirs(repo_path / ".git")

        # Create main project pyproject.toml
        with open(repo_path / "pyproject.toml", "w") as f:
            f.write("""
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "main-project"
version = "0.1.0"
requires-python = ">=3.8"
dependencies = [
    "requests>=2.25.0",
    "packaging>=20.0",
]
            """)

        # Create sub-project with its own pyproject.toml
        os.makedirs(repo_path / "subproject")
        with open(repo_path / "subproject" / "pyproject.toml", "w") as f:
            f.write("""
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "sub-project"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
    "flask>=2.0.0",
]
            """)

        yield repo_path


@mock.patch("dependapy.analyzer.get_latest_python_versions")
@mock.patch("dependapy.analyzer.get_latest_version")
def test_full_workflow_without_pr(mock_get_version, mock_py_versions, sample_repo):
    """Test the full workflow without creating a PR"""
    # Mock the latest Python versions
    mock_py_versions.return_value = ["3.12", "3.11", "3.10"]

    # Mock package versions
    mock_get_version.side_effect = lambda pkg: {
        "requests": "2.31.0",
        "packaging": "23.2",
        "flask": "2.3.3",
    }[pkg]

    # Step 1: Scan the repository
    analysis_results = scan_repository(sample_repo)
    assert len(analysis_results) == 2  # Should find two pyproject.toml files

    # Step 2: Update the dependencies
    update_results = update_dependencies(analysis_results)
    assert len(update_results) == 2  # Both files should be updated

    # Verify the main project file was updated correctly
    with open(sample_repo / "pyproject.toml", "r") as f:
        main_content = f.read()
        assert 'requires-python = ">=3.10"' in main_content
        assert any(
            ["requests>=2.31.0" in main_content, '"requests>=2.31.0"' in main_content]
        )
        assert any(
            ["packaging>=23.2" in main_content, '"packaging>=23.2"' in main_content]
        )

    # Verify the subproject file was updated correctly
    with open(sample_repo / "subproject" / "pyproject.toml", "r") as f:
        sub_content = f.read()
        assert 'requires-python = ">=3.10"' in sub_content
        assert any(["flask>=2.3.3" in sub_content, '"flask>=2.3.3"' in sub_content])


@mock.patch("dependapy.analyzer.get_latest_python_versions")
@mock.patch("dependapy.analyzer.get_latest_version")
@mock.patch("dependapy.github_api.create_pr_with_pygithub")
def test_full_workflow_with_pr_mock(
    mock_create_pr,
    mock_get_version,
    mock_py_versions,
    sample_repo,
):
    """Test the full workflow with PR creation using mocks"""
    # Mock the latest Python versions
    mock_py_versions.return_value = ["3.12", "3.11", "3.10"]

    # Mock package versions
    mock_get_version.side_effect = lambda pkg: {
        "requests": "2.31.0",
        "packaging": "23.2",
        "flask": "2.3.3",
    }[pkg]

    # Mock PR creation
    mock_create_pr.return_value = "https://github.com/user/repo/pull/1"

    # Step 1: Scan the repository
    analysis_results = scan_repository(sample_repo)

    # Step 2: Update the dependencies
    update_results = update_dependencies(analysis_results)

    # Step 3: Create a PR
    pr_url = create_or_update_pull_request(
        repo_path=sample_repo,
        branch_name="dependapy/update-test",
        updated_files=[result.file_path for result in update_results],
        github_token="fake-token",
    )

    # Verify PR was created
    assert pr_url == "https://github.com/user/repo/pull/1"
    # Verify the mocked function was called
    mock_create_pr.assert_called_once()
