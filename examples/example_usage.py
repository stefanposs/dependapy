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
description = "A sample project with outdated dependencies"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "requests>=2.25.0",
    "packaging>=23.0",
    "fastapi>=0.95.0",
    "sqlalchemy>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0", 
    "black>=23.1.0",
]
            """)
        
        # Create README.md
        readme_path = project_dir / "README.md"
        with open(readme_path, "w") as f:
            f.write("# Sample Project\n\nA test project for demonstrating dependapy with uv.")
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=project_dir, check=True)
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True)
        
        print(f"Sample project created at: {project_dir}")
        print(f"You can now run: cd {project_dir} && python -m dependapy.main --no-pr")
        
        return project_dir