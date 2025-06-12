"""
Constants and sentinel values for dependapy
"""

from typing import Final


# Sentinel value to use instead of None
class SentinelType:
    """Sentinel type for representing missing or undefined values"""

    def __repr__(self) -> str:
        return "<SENTINEL>"

    def __bool__(self) -> bool:
        """Sentinel evaluates to False in boolean context"""
        return False


# Sentinel singleton to use instead of None
SENTINEL: Final[SentinelType] = SentinelType()

# Standard branch name for dependency updates
DEFAULT_BRANCH_NAME: Final[str] = "dependapy/dependency-updates"

# Default timeouts
DEFAULT_API_TIMEOUT: Final[int] = 10

# Configuration constants
NUM_LATEST_PYTHON_VERSIONS: Final[int] = 3

# API URLs
PYTHON_EOL_API_URL: Final[str] = "https://endoflife.date/api/python.json"
PYPI_API_URL_TEMPLATE: Final[str] = "https://pypi.org/pypi/{package_name}/json"
