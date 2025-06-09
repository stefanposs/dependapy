"""
Updater module for updating pyproject.toml files
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dependapy.analyzer import FileAnalysisResult

logger = logging.getLogger("dependapy.updater")

@dataclass
class UpdateResult:
    """Result of updating a pyproject.toml file"""
    file_path: Path
    modified: bool

def update_dependencies(analysis_results: List[FileAnalysisResult]) -> List[UpdateResult]:
    """Update dependencies in pyproject.toml files based on analysis results"""
    update_results = []
    
    for result in analysis_results:
        file_path = result.file_path
        modified = False
        
        # Read the file content
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            continue
            
        original_content = content
        
        # Update Python version if needed
        if result.python_update:
            logger.info(f"Updating Python version in {file_path}")
            old_constraint = result.python_update.current_constraint
            new_constraint = result.python_update.recommended_constraint
            
            # Handle quoted and unquoted requires-python
            content = re.sub(
                rf'requires-python\s*=\s*["\']?{re.escape(old_constraint)}["\']?',
                f'requires-python = "{new_constraint}"',
                content
            )
            
        # Update package versions
        for update in result.package_updates:
            package = update.package_name
            old_version = update.current_version
            new_version = update.latest_version
            logger.info(f"Updating {package} from {old_version} to {new_version} in {file_path}")
            
            # Pattern to match the package in dependencies
            # This covers both quoted "package>=version" and unquoted package>=version formats
            pattern = rf'(["\']?{re.escape(package)}["\']?\s*(?:>=|==)\s*)(?:{re.escape(old_version)})'
            replacement = f"\\1{new_version}"
            content = re.sub(pattern, replacement, content)
        
        # Check if content was modified
        if content != original_content:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                modified = True
                logger.info(f"Successfully updated {file_path}")
            except Exception as e:
                logger.error(f"Failed to write updates to {file_path}: {e}")
                continue
        
        update_results.append(UpdateResult(file_path=file_path, modified=modified))
    
    # Filter to only return results that were actually modified
    return [result for result in update_results if result.modified]
