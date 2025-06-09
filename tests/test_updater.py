"""Tests for the updater module of dependapy"""

import tempfile
from pathlib import Path
import pytest
from unittest import mock

from dependapy.analyzer import FileAnalysisResult, PythonVersionUpdateInfo, UpdateInfo
from dependapy.updater import update_dependencies


def test_update_dependencies():
    """Test updating dependencies in pyproject.toml files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "pyproject.toml"

        # Create a test pyproject.toml file
        with open(test_file, "w") as f:
            f.write("""
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.1.0"
requires-python = ">=3.8"
dependencies = [
    "requests>=2.25.0",
    "packaging>=23.0",
]
            """)

        # Create an analysis result
        analysis_result = FileAnalysisResult(
            file_path=test_file,
            package_updates=[
                UpdateInfo(
                    package_name="requests",
                    current_version="2.25.0",
                    latest_version="2.31.0",
                    file_path=test_file,
                ),
                UpdateInfo(
                    package_name="packaging",
                    current_version="23.0",
                    latest_version="23.2",
                    file_path=test_file,
                ),
            ],
            python_update=PythonVersionUpdateInfo(
                current_constraint=">=3.8",
                recommended_constraint=">=3.10",
                file_path=test_file,
            ),
        )

        # Update the dependencies
        update_results = update_dependencies([analysis_result])

        # Check that the file was updated
        assert len(update_results) == 1
        assert update_results[0].file_path == test_file
        assert update_results[0].modified is True

        # Verify the contents of the updated file
        with open(test_file, "r") as f:
            content = f.read()
            assert 'requires-python = ">=3.10"' in content
            assert '"requests>=2.31.0"' in content or "requests>=2.31.0" in content
            assert '"packaging>=23.2"' in content or "packaging>=23.2" in content


def test_no_updates_needed():
    """Test when no updates are needed"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "pyproject.toml"

        # Create a test pyproject.toml file that's already up to date
        with open(test_file, "w") as f:
            f.write("""
[project]
name = "test-project"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31.0", 
    "packaging>=23.2",
]
            """)

        # Create an analysis result with no updates needed
        analysis_result = FileAnalysisResult(
            file_path=test_file,
            package_updates=[],  # No package updates needed
            python_update=None,  # No Python version update needed
        )

        # Update the dependencies
        update_results = update_dependencies([analysis_result])

        # Check that no files were modified
        assert len(update_results) == 0


def test_update_errors():
    """Test handling of errors when updating files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "pyproject.toml"
        non_existent_file = Path(tmpdir) / "non_existent.toml"

        # Create a test pyproject.toml file
        with open(test_file, "w") as f:
            f.write("""
[project]
name = "test-project"
version = "0.1.0"
requires-python = ">=3.8"
dependencies = ["requests>=2.25.0"]
            """)

        # Create analysis results including a non-existent file
        analysis_results = [
            FileAnalysisResult(
                file_path=test_file,
                package_updates=[
                    UpdateInfo(
                        package_name="requests",
                        current_version="2.25.0",
                        latest_version="2.31.0",
                        file_path=test_file,
                    ),
                ],
                python_update=None,
            ),
            FileAnalysisResult(
                file_path=non_existent_file,
                package_updates=[
                    UpdateInfo(
                        package_name="requests",
                        current_version="2.25.0",
                        latest_version="2.31.0",
                        file_path=non_existent_file,
                    ),
                ],
                python_update=None,
            ),
        ]

        # Update the dependencies - should handle the non-existent file gracefully
        update_results = update_dependencies(analysis_results)

        # Check that only the existing file was updated
        assert len(update_results) == 1
        assert update_results[0].file_path == test_file
        assert update_results[0].modified is True
