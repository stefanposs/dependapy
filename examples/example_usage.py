"""
Example script to demonstrate how to use dependapy by creating a random test project
"""

import os
import subprocess
import shutil
import random
import string
from pathlib import Path


def create_example_project(base_dir: Path) -> Path:
    """Create a complete example project with outdated dependencies."""
    # Use the given directory directly without creating subdirectories
    project_dir = base_dir
    project_dir.mkdir(parents=True, exist_ok=True)

    # Derive project name from the directory path
    project_name = project_dir.name

    # Create src directory
    src_dir = project_dir / "src" / project_name
    src_dir.mkdir(parents=True, exist_ok=True)

    # Create tests directory
    tests_dir = project_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    # Create pyproject.toml with outdated dependencies
    pyproject_content = """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
version = "0.1.0"
description = "A test project with outdated dependencies for testing dependapy"
readme = "README.md"
requires-python = ">=3.8"
authors = [
    {name = "Test Author", email = "test@example.com"},
]
keywords = ["example", "testing", "dependencies"]

dependencies = [
    "requests>=2.25.0",     # Current latest: 2.31.0
    "packaging>=20.0",      # Current latest: 23.2
    "fastapi>=0.95.0",      # Current latest: 0.104.1
    "sqlalchemy>=1.4.0",   # Current latest: 2.0.23
    "click>=8.0.0",         # Current latest: 8.1.7
    "pydantic>=1.10.0",    # Current latest: 2.5.0
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",       # Current latest: 7.4.3
    "black>=22.0.0",       # Current latest: 23.11.0
    "flake8>=5.0.0",       # Current latest: 6.1.0
]

[project.scripts]
example-cli = "{project_name}.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/{project_name}"]
"""
    # Replace project name in pyproject.toml
    pyproject_content = pyproject_content.replace("{project_name}", project_name)

    with open(project_dir / "pyproject.toml", "w") as f:
        f.write(pyproject_content)

    # Create README.md
    readme_content = f"""# {project_dir.name}

This is a temporary test project with **intentionally outdated dependencies** for testing dependapy.

## Dependencies

This project includes several **intentionally outdated** dependencies:

- `requests>=2.25.0` (latest: 2.31.0)
- `packaging>=20.0` (latest: 23.2)  
- `fastapi>=0.95.0` (latest: 0.104.1)
- `sqlalchemy>=1.4.0` (latest: 2.0.23)
- And more...

When you run dependapy on this project, it should detect and update these outdated dependencies.
"""

    with open(project_dir / "README.md", "w") as f:
        f.write(readme_content)

    # Create main module
    init_content = '''"""Example test project for dependapy."""

__version__ = "0.1.0"

from .main import hello_world, calculate_something

__all__ = ["hello_world", "calculate_something"]
'''

    with open(src_dir / "__init__.py", "w") as f:
        f.write(init_content)

    # Create main.py
    main_content = '''"""Main module for the example test project."""

import requests
from packaging.version import parse as parse_version
from sqlalchemy import create_engine
from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    """Example Pydantic model."""
    name: str
    email: str
    age: Optional[int] = None


def hello_world() -> str:
    """Return a simple greeting."""
    return "Hello, World from example-test-project!"


def calculate_something(x: int, y: int) -> int:
    """Calculate the sum of two numbers."""
    return x + y


def check_version(version_string: str) -> bool:
    """Check if a version string is valid using packaging."""
    try:
        parse_version(version_string)
        return True
    except Exception:
        return False


def make_request(url: str) -> dict:
    """Make a simple HTTP request using requests."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return {"status": "success", "status_code": response.status_code}
    except requests.RequestException as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    print(hello_world())
    print(f"2 + 3 = {calculate_something(2, 3)}")
    print(f"Is '1.2.3' a valid version? {check_version('1.2.3')}")
'''

    with open(src_dir / "main.py", "w") as f:
        f.write(main_content)

    # Create CLI module
    cli_content = '''"""Command-line interface for the example test project."""

import click
from .main import hello_world, calculate_something


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Example CLI application for testing dependapy."""
    pass


@cli.command()
def hello():
    """Print a greeting message."""
    click.echo(hello_world())


@cli.command()
@click.argument("x", type=int)
@click.argument("y", type=int)
def add(x: int, y: int):
    """Add two numbers together."""
    result = calculate_something(x, y)
    click.echo(f"{x} + {y} = {result}")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
'''

    with open(src_dir / "cli.py", "w") as f:
        f.write(cli_content)

    # Create test file
    test_content = f'''"""Tests for the example test project."""

import pytest
from {project_name}.main import hello_world, calculate_something, check_version


def test_hello_world():
    """Test the hello_world function."""
    result = hello_world()
    assert result == "Hello, World from example-test-project!"


def test_calculate_something():
    """Test the calculate_something function."""
    assert calculate_something(2, 3) == 5
    assert calculate_something(0, 0) == 0


def test_check_version():
    """Test the check_version function."""
    assert check_version("1.0.0") is True
    assert check_version("invalid") is False
'''

    with open(tests_dir / "__init__.py", "w") as f:
        f.write("# Test package")

    with open(tests_dir / "test_main.py", "w") as f:
        f.write(test_content)

    return project_dir


def main():
    """Create a random test project and run dependapy on it."""
    # Generate random project name
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    project_name = f"test_project_{random_suffix}"

    # Create project in examples directory
    examples_dir = Path(__file__).parent
    temp_dir = examples_dir / project_name

    # Check if directory already exists and create a new name if needed
    while temp_dir.exists():
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        project_name = f"test_project_{random_suffix}"
        temp_dir = examples_dir / project_name

    try:
        print(f"🏗️  Creating example project in: {temp_dir}")
        project_dir = create_example_project(temp_dir)

        print(f"✅ Example project created at: {project_dir}")
        print(f"📁 Project directory: {project_dir.absolute()}")

        # List the created files
        print("\n📋 Created files:")
        for file_path in sorted(project_dir.rglob("*")):
            if file_path.is_file():
                relative_path = file_path.relative_to(project_dir)
                print(f"   {relative_path}")

        # Change to the project directory
        original_dir = Path.cwd()
        os.chdir(project_dir)

        try:
            # Run dependapy using the parent project's uv environment
            print("\n🚀 Running dependapy analysis...")
            # Get the absolute path to the parent dependapy project
            dependapy_root = Path(__file__).parent.parent

            # Run dependapy from the parent project directory using the full path
            cmd = [
                "uv",
                "run",
                "--directory",
                str(dependapy_root),
                "python",
                "-m",
                "dependapy.main",
                "--repo-path",
                str(project_dir),
                "--no-pr",
            ]
            print(f"Executing command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True, cwd=str(dependapy_root)
            )

            print("✅ Dependapy analysis completed successfully!")
            print("\n📋 Output:")
            print(result.stdout)

            if result.stderr:
                print("\n⚠️  Warnings/Errors:")
                print(result.stderr)

        except subprocess.CalledProcessError as e:
            print(f"❌ Dependapy failed with exit code {e.returncode}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return e.returncode
        except FileNotFoundError:
            print("❌ Could not find 'uv' command. Please make sure uv is installed.")
            print("Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
            return 1
        finally:
            # Change back to original directory
            os.chdir(original_dir)

        print(f"\n📝 You can manually inspect the project at: {project_dir.absolute()}")
        print("💡 To create a PR, set GITHUB_TOKEN and run without --no-pr flag")
        print(f"🗂️  The test project is permanently stored at: {temp_dir}")

        # Ask if user wants to keep or delete the test project
        try:
            keep = input("\n❓ Keep the test project? [y/N]: ").lower().strip()
            if keep not in ["y", "yes"]:
                print("🧹 Cleaning up test project...")
                shutil.rmtree(temp_dir)
                print("✅ Test project cleaned up")
            else:
                print(f"📁 Test project kept at: {temp_dir}")
                print(
                    f"💡 You can run dependapy on it again with: cd {temp_dir} && uv run --directory /Users/stefanposs/Repos/dependapy python -m dependapy.main --repo-path . --no-pr"
                )
        except KeyboardInterrupt:
            print(f"\n📁 Test project kept at: {temp_dir}")

    except Exception as e:
        print(f"❌ Error creating or running test project: {e}")
        # Clean up on error
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
