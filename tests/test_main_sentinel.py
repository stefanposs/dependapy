"""Test for main module's SENTINEL handling"""

import unittest
from unittest import mock
from pathlib import Path

from dependapy.constants import SENTINEL
from dependapy.main import main


class TestMainSentinelHandling(unittest.TestCase):
    """Test cases for main module's SENTINEL handling"""

    @mock.patch("sys.argv", ["dependapy", "--repo-path", "/fake/path"])
    @mock.patch("dependapy.main.scan_repository")
    @mock.patch("dependapy.main.update_dependencies")
    def test_main_handles_update_sentinel(self, mock_update, mock_scan):
        """Test that main handles SENTINEL returns from update_dependencies"""
        # Set up mocks
        mock_scan.return_value = ["fake_result"]
        mock_update.return_value = SENTINEL

        # Run main function
        result = main()

        # Verify that it returns error code
        self.assertEqual(result, 1)

    @mock.patch("sys.argv", ["dependapy", "--repo-path", "/fake/path", "--offline-pr"])
    @mock.patch("dependapy.main.scan_repository")
    @mock.patch("dependapy.main.update_dependencies")
    @mock.patch("dependapy.main.create_git_patch")
    def test_main_handles_git_patch_sentinel(self, mock_patch, mock_update, mock_scan):
        """Test that main handles SENTINEL returns from create_git_patch"""
        # Set up mocks
        mock_scan.return_value = ["fake_result"]
        mock_update.return_value = [
            mock.MagicMock(file_path=Path("/fake/path/file"), modified=True)
        ]
        mock_patch.return_value = SENTINEL

        # Run main function
        result = main()

        # Verify that it returns error code
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
