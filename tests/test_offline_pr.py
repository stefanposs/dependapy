"""Tests for the offline PR functionality"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import subprocess

from dependapy.constants import SENTINEL
from dependapy.offline_pr import create_git_patch


class TestOfflinePR(unittest.TestCase):
    """Test cases for the offline PR functionality"""

    @mock.patch("subprocess.run")
    @mock.patch("subprocess.check_output")
    def test_create_git_patch(self, mock_check_output, mock_run):
        """Test creating a Git patch file"""
        # Mock the subprocess.check_output to return a branch name
        mock_check_output.return_value = "main"

        # Set up test data
        repo_path = Path("/tmp/test_repo")
        branch_name = "test-branch"
        updated_files = [Path("/tmp/test_repo/pyproject.toml")]

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            output_path = temp_file.name

        try:
            # Call the function
            result = create_git_patch(
                repo_path, branch_name, updated_files, output_path
            )

            # Verify the result
            self.assertEqual(result, os.path.abspath(output_path))

            # Verify that the expected Git commands were called
            expected_calls = [
                mock.call(
                    ["git", "-C", str(repo_path), "checkout", "-b", branch_name],
                    check=True,
                    capture_output=True,
                    text=True,
                ),
                mock.call(
                    ["git", "-C", str(repo_path), "add", str(updated_files[0])],
                    check=True,
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        str(repo_path),
                        "commit",
                        "-m",
                        mock.ANY,
                    ],  # We don't check the exact message
                    check=True,
                ),
                # Format-patch call is harder to verify due to the file redirect
                mock.call(
                    ["git", "-C", str(repo_path), "checkout", "main"], check=True
                ),
            ]

            # Check that all expected calls were made (excluding the format-patch call)
            for expected_call in expected_calls:
                # Find if this call was made to mock_run
                self.assertIn(expected_call, mock_run.call_args_list)

        finally:
            # Clean up the temp file
            try:
                os.unlink(output_path)
            except (OSError, FileNotFoundError):
                pass

    @mock.patch("subprocess.run")
    @mock.patch("subprocess.check_output")
    def test_create_git_patch_failure(self, mock_check_output, mock_run):
        """Test creating a Git patch file when a Git command fails"""
        # Mock the subprocess.check_output to return a branch name
        mock_check_output.return_value = "main"

        # Set up mock to raise CalledProcessError
        # Create a CalledProcessError with output and error attributes
        error = subprocess.CalledProcessError(1, "git command")
        error.stdout = "error output"
        error.stderr = "error message"
        mock_run.side_effect = error

        # Set up test data
        repo_path = Path("/tmp/test_repo")
        branch_name = "test-branch"
        updated_files = [Path("/tmp/test_repo/pyproject.toml")]

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            output_path = temp_file.name

        try:
            # Call the function
            result = create_git_patch(
                repo_path, branch_name, updated_files, output_path
            )

            # Verify that SENTINEL is returned on failure
            self.assertIs(result, SENTINEL)
        finally:
            # Clean up
            try:
                os.unlink(output_path)
            except (OSError, FileNotFoundError):
                pass
