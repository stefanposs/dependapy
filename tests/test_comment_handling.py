"""Test for handling comments in dependency updates"""

import tempfile
from pathlib import Path

from dependapy.analyzer import FileAnalysisResult, UpdateInfo
from dependapy.updater import update_dependencies


def test_update_dependencies_with_comments():
    """Test updating dependencies with inline comments"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "pyproject_with_comments.toml"

        # Create a test pyproject.toml file with inline comments
        with open(test_file, "w") as f:
            f.write("""
[project]
name = "test-project-with-comments"
version = "0.1.0"
dependencies = [
    "requests>=2.25.0",  # Current latest is 2.31.0
    "packaging==20.0",   # Important dependency with specific version
    "flask>=2.0.0",      # Web framework
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
                    current_version="20.0",
                    latest_version="23.2",
                    file_path=test_file,
                ),
            ],
            python_update=None,
        )

        # Update dependencies
        results = update_dependencies([analysis_result])

        # Verify results
        assert len(results) == 1
        assert results[0].file_path == test_file
        assert results[0].modified is True

        # Read the updated file
        with open(test_file, "r") as f:
            updated_content = f.read()

        # Check that the dependencies were updated
        assert "requests>=2.31.0" in updated_content
        assert "packaging==23.2" in updated_content

        # Check that comments were preserved (they should follow the updated version)
        assert "# Current latest is 2.31.0" in updated_content
        assert "# Important dependency with specific version" in updated_content
        assert "# Web framework" in updated_content
