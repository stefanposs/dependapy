"""Tests for the SENTINEL pattern implementation across dependapy"""

import unittest
from unittest import mock
from pathlib import Path

from dependapy.constants import SENTINEL
from dependapy.analyzer import scan_file, get_min_python_version
from dependapy.updater import update_dependencies
from dependapy.offline_pr import create_git_patch
from dependapy.github_api import get_repo_info


class TestSentinelPattern(unittest.TestCase):
    """Test cases for the SENTINEL pattern implementation"""

    def test_get_min_python_version_returns_sentinel(self):
        """Test that get_min_python_version returns SENTINEL for invalid input"""
        result = get_min_python_version("<4.0")
        self.assertIs(result, SENTINEL)

        result = get_min_python_version("~=3.8")
        self.assertIs(result, SENTINEL)

        # Test with completely invalid input
        result = get_min_python_version("invalid_constraint")
        self.assertIs(result, SENTINEL)

    @mock.patch("dependapy.analyzer.tomllib.load")
    def test_scan_file_returns_sentinel_on_error(self, mock_load):
        """Test that scan_file returns SENTINEL on errors"""
        # Simulate a parsing error
        mock_load.side_effect = Exception("Failed to parse")

        result = scan_file(Path("/fake/path/pyproject.toml"), ["3.10", "3.11", "3.12"])
        self.assertIs(result, SENTINEL)

    def test_update_dependencies_with_empty_results(self):
        """Test that update_dependencies returns SENTINEL with empty results"""
        # Call the function with an empty list
        result = update_dependencies([])

        # Check that result is SENTINEL
        self.assertIs(result, SENTINEL)

    @mock.patch("subprocess.run")
    @mock.patch("subprocess.check_output")
    def test_create_git_patch_sentinel_on_error(self, mock_check_output, mock_run):
        """Test that create_git_patch returns SENTINEL on errors"""
        # Setup mocks
        mock_check_output.return_value = "main"
        mock_run.side_effect = Exception("Git error")

        result = create_git_patch(
            Path("/fake/repo"),
            "fake-branch",
            [Path("/fake/repo/pyproject.toml")],
            "/tmp/output.patch",
        )

        self.assertIs(result, SENTINEL)

    @mock.patch("subprocess.check_output")
    def test_get_repo_info_sentinel_on_error(self, mock_check_output):
        """Test that get_repo_info returns SENTINEL on errors"""
        # Setup mock to raise error
        mock_check_output.side_effect = Exception("Git error")

        result = get_repo_info(Path("/fake/repo"))

        self.assertIs(result, SENTINEL)
