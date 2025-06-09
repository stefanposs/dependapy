#!/usr/bin/env python3
"""
Simple test script to verify dependapy functionality
"""
import os
import tempfile
import shutil
from pathlib import Path

# Create a temporary test directory
temp_dir = tempfile.mkdtemp()
print(f"Created temporary test directory at: {temp_dir}")

try:
    # Create a fake pyproject.toml file with outdated dependencies
    test_file_path = Path(temp_dir) / "pyproject.toml"
    
    with open(test_file_path, "w") as f:
        f.write("""
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"
description = "A test project for dependapy"
readme = "README.md"
requires-python = ">=3.8"
license = {file = "LICENSE"}
dependencies = [
    "requests>=2.25.0",
    "packaging>=21.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=6.0.0",
]
""")
    
    print(f"Created test pyproject.toml file at: {test_file_path}")
    print("\nRunning dependapy with --no-pr flag...\n")
    
    # Run dependapy in the temp directory with --no-pr flag
    os.system(f"python -m dependapy.main --repo-path {temp_dir} --no-pr")
    
    # Read and print the updated file
    print("\nChecking for updates in the pyproject.toml file...")
    with open(test_file_path, "r") as f:
        updated_content = f.read()
    
    print("\nUpdated pyproject.toml content:")
    print("=" * 50)
    print(updated_content)
    print("=" * 50)
    
finally:
    # Clean up
    shutil.rmtree(temp_dir)
    print(f"\nCleaned up temporary directory: {temp_dir}")
