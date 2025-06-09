"""
Example script to demonstrate how to use dependapy with uv
"""
import os
import subprocess
import tempfile
from pathlib import Path


def create_sample_project():
    """Create a sample project with a pyproject.toml file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "sample-project"
        project_dir.mkdir()
        
        # Create a simple pyproject.toml file with outdated dependencies
        pyproject_path = project_dir / "pyproject.toml"
        with open(pyproject_path, "w") as f:
            f.write("""
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sample-project"
version = "0.1.0"
description = "A sample project"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "requests>=2.25.0",
    "packaging>=23.0",
]
            """)
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=project_dir, check=True)
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True)
        
        print(f"Sample project created at: {project_dir}")
        print(f"You can now run: cd {project_dir} && python -m dependapy.main --no-pr")
        
        return project_dir


def run_dependapy(project_path):
    """Run dependapy on the sample project"""
    print("Running dependapy with --no-pr flag...")
    result = subprocess.run(
        ["python", "-m", "dependapy.main", "--no-pr"],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    
    print("\nOutput:")
    print(result.stdout)
    
    if result.stderr:
        print("\nErrors:")
        print(result.stderr)
    
    # Check if the pyproject.toml file was modified
    with open(project_path / "pyproject.toml", "r") as f:
        content = f.read()
        print("\nUpdated pyproject.toml:")
        print(content)


if __name__ == "__main__":
    project_path = create_sample_project()
    run_dependapy(project_path)
