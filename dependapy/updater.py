"""
Updater module for updating pyproject.toml files
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from dependapy.analyzer import FileAnalysisResult

logger = logging.getLogger("dependapy.updater")


@dataclass
class UpdateResult:
    """Result of updating a pyproject.toml file"""

    file_path: Path
    modified: bool


def update_dependencies(analysis_results: list[FileAnalysisResult]) -> list[UpdateResult]:
    """Update dependencies in pyproject.toml files based on analysis results"""
    update_results = []

    for result in analysis_results:
        file_path = result.file_path
        modified = False

        try:
            # Read the current file content
            with file_path.open("r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            logger.exception("Failed to read %s", file_path)
            continue

        # Update Python version requirement if needed
        if result.python_update:
            current = result.python_update.current_constraint
            new = result.python_update.recommended_constraint
            content = content.replace(
                f'requires-python = "{current}"',
                f'requires-python = "{new}"',
            )
            logger.info("Updated Python requirement: %s -> %s", current, new)
            modified = True

        # Update package versions
        for update in result.package_updates:
            package_name = update.package_name
            current_version = update.current_version
            new_version = update.latest_version

            # Pattern to match the current version while preserving indentation and format
            # We need to ensure we only update the correct dependency
            pattern = (
                f'(["\']?{re.escape(package_name)}["\']?\\s*(?:>=|==)\\s*)'
                f'["\']?{re.escape(current_version)}["\']?'
            )

            # Replace with the new version, preserving the capture group
            def get_replacement(match, version=new_version) -> str:
                return f"{match.group(1)}{version}"
            content = re.sub(pattern, get_replacement, content)

            logger.info("Updated %s: %s -> %s", package_name, current_version, new_version)
            modified = True

        # Write back the file if modifications were made
        if modified:
            try:
                with file_path.open("w", encoding="utf-8") as f:
                    f.write(content)
                logger.info("Successfully updated %s", file_path)
            except Exception:
                logger.exception("Failed to write updated content to %s", file_path)
                continue

        update_results.append(UpdateResult(file_path=file_path, modified=modified))

    return update_results
