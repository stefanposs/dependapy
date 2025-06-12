"""
Updater module for updating pyproject.toml files
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from dependapy.analyzer import FileAnalysisResult
from dependapy.constants import SENTINEL, SentinelType

logger = logging.getLogger("dependapy.updater")


@dataclass
class UpdateResult:
    """Result of updating a pyproject.toml file"""

    file_path: Path
    modified: bool


def update_dependencies(
    analysis_results: list[FileAnalysisResult],
) -> list[UpdateResult] | SentinelType:
    """Update dependencies in pyproject.toml files based on analysis results"""
    if not analysis_results:
        logger.warning("No analysis results provided, nothing to update")
        return SENTINEL

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
            # Continue with next file, but add a failed result
            update_results.append(UpdateResult(file_path=file_path, modified=False))
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
            # The pattern accounts for possible inline comments after the version
            pattern = (
                f"([\"']?{re.escape(package_name)}[\"']?\\s*(?:>=|==)\\s*)"
                f"([\"']?){re.escape(current_version)}([\"']?)([^\\n]*)"
            )

            # Replace with the new version, preserving the capture groups for quotes and comments
            def get_replacement(match, version=new_version) -> str:
                prefix = match.group(1)  # package name and operator
                quote_start = match.group(2)  # opening quote
                quote_end = match.group(3)  # closing quote
                comment = match.group(4) or ""  # comment part (if any)
                return f"{prefix}{quote_start}{version}{quote_end}{comment}"

            content = re.sub(pattern, get_replacement, content)

            logger.info(
                "Updated %s: %s -> %s", package_name, current_version, new_version
            )
            modified = True

        # Write back the file if modifications were made
        if modified:
            try:
                with file_path.open("w", encoding="utf-8") as f:
                    f.write(content)
                logger.info("Successfully updated %s", file_path)
            except Exception:
                logger.exception("Failed to write updated content to %s", file_path)
                # Mark as not modified since write failed
                modified = False

        update_results.append(UpdateResult(file_path=file_path, modified=modified))

    return update_results
