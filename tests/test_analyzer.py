"""Tests for the analyzer module of dependapy"""
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from dependapy.analyzer import (
    get_latest_python_versions,
    get_latest_version,
    get_min_python_version,
    parse_dependency_version,
    scan_file,
    scan_repository,
)


def test_parse_dependency_version():
    """Test the parse_dependency_version function"""
    # Test with quoted format
    package, version = parse_dependency_version('"requests>=2.25.0"')
    assert package == "requests"
    assert version == "2.25.0"
    
    # Test with unquoted format
    package, version = parse_dependency_version("requests>=2.25.0")
    assert package == "requests"
    assert version == "2.25.0"
    
    # Test with == format
    package, version = parse_dependency_version("requests==2.25.0")
    assert package == "requests"
    assert version == "2.25.0"
    
    # Test without version
    package, version = parse_dependency_version("requests")
    assert package == "requests"
    assert version == ""


def test_get_min_python_version():
    """Test the get_min_python_version function"""
    assert get_min_python_version(">=3.8") == "3.8"
    assert get_min_python_version(">=3.8,<4.0") == "3.8"
    assert get_min_python_version(">=3.8.0") == "3.8"
    assert get_min_python_version("<4.0") is None
    assert get_min_python_version("~=3.8") is None


@mock.patch("dependapy.analyzer.requests.get")
def test_get_latest_python_versions(mock_get):
    """Test the get_latest_python_versions function with mocked API response"""
    # Mock API response
    mock_response = mock.Mock()
    mock_response.json.return_value = [
        {"cycle": "3.12", "eol": "2028-10-02"},
        {"cycle": "3.11", "eol": "2027-10-24"},
        {"cycle": "3.10", "eol": "2026-10-04"},
        {"cycle": "3.9", "eol": "2025-10-05"},
    ]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    versions = get_latest_python_versions()
    assert versions == ["3.12", "3.11", "3.10"]
    mock_get.assert_called_with("https://endoflife.date/api/python.json")


@mock.patch("dependapy.analyzer.requests.get")
def test_get_latest_version(mock_get):
    """Test the get_latest_version function with mocked PyPI response"""
    # Mock PyPI response
    mock_response = mock.Mock()
    mock_response.json.return_value = {"info": {"version": "2.31.0"}}
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    version = get_latest_version("requests")
    assert version == "2.31.0"
    mock_get.assert_called_with("https://pypi.org/pypi/requests/json", timeout=10)
    
    # Test caching
    version = get_latest_version("requests")
    assert version == "2.31.0"
    # Should only be called once due to caching
    assert mock_get.call_count == 1


def test_scan_file():
    """Test scanning a pyproject.toml file with mock data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "pyproject.toml"
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
        
        # Mock the latest Python versions and get_latest_version function
        with mock.patch("dependapy.analyzer.get_latest_python_versions") as mock_py_versions:
            with mock.patch("dependapy.analyzer.get_latest_version") as mock_get_version:
                mock_py_versions.return_value = ["3.12", "3.11", "3.10"]
                mock_get_version.side_effect = lambda pkg: {"requests": "2.31.0", "packaging": "23.2"}[pkg]
                
                result = scan_file(test_file, ["3.12", "3.11", "3.10"])
                
                # Should require Python version update
                assert result.python_update is not None
                assert result.python_update.current_constraint == ">=3.8"
                assert result.python_update.recommended_constraint == ">=3.10"
                
                # Should have two package updates
                assert len(result.package_updates) == 2
                assert any(update.package_name == "requests" and 
                         update.current_version == "2.25.0" and 
                         update.latest_version == "2.31.0" 
                         for update in result.package_updates)
                assert any(update.package_name == "packaging" and 
                         update.current_version == "23.0" and 
                         update.latest_version == "23.2" 
                         for update in result.package_updates)


def test_scan_repository():
    """Test scanning a repository with mock pyproject.toml files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create a few pyproject.toml files in different directories
        (repo_path / "project1").mkdir()
        with open(repo_path / "project1" / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "project1"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["requests>=2.31.0"]
            """)
        
        (repo_path / "project2").mkdir()
        with open(repo_path / "project2" / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "project2"
version = "0.1.0"
requires-python = ">=3.8"
dependencies = ["requests>=2.25.0"]
            """)
        
        # Mock functions
        with mock.patch("dependapy.analyzer.get_latest_python_versions") as mock_py_versions:
            with mock.patch("dependapy.analyzer.scan_file") as mock_scan:
                mock_py_versions.return_value = ["3.12", "3.11", "3.10"]
                
                # Mock only project2 needing updates
                mock_scan.side_effect = lambda file_path, versions: None if "project1" in str(file_path) else mock.MagicMock()
                
                results = scan_repository(repo_path)
                assert len(results) == 1  # Only project2 should need updates
