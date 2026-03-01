# Domain Layer — Innerster Ring
# Keine externen Abhängigkeiten außer stdlib + packaging

from dependapy.domain.errors import (
    BranchExistsError,
    ConfigurationError,
    DomainError,
    PackageNotFoundError,
    PolicyError,
    PolicyNotFoundError,
    PolicyValidationError,
    PRCreationError,
    ProjectError,
    ProjectParseError,
    ProjectWriteError,
    PushRejectedError,
    RegistryError,
    RegistryNetworkError,
    RegistryTimeoutError,
    VCSError,
)
from dependapy.domain.models import Dependency, PlannedUpdate, PlanStatus, Project, UpdatePlan
from dependapy.domain.result import Err, Ok, Result, collect_results
from dependapy.domain.services import (
    compute_update_type,
    create_update_plan,
    determine_target_version,
)
from dependapy.domain.value_objects import (
    ConstraintOperator,
    PackageSpec,
    UpdateType,
    Version,
    VersionConstraint,
)
from dependapy.domain.vcs_types import PRRequest, PRResult, RepoInfo

__all__ = [
    "BranchExistsError",
    "ConfigurationError",
    "ConstraintOperator",
    "Dependency",
    "DomainError",
    "Err",
    "Ok",
    "PRCreationError",
    "PRRequest",
    "PRResult",
    "PackageNotFoundError",
    "PackageSpec",
    "PlanStatus",
    "PlannedUpdate",
    "PolicyError",
    "PolicyNotFoundError",
    "PolicyValidationError",
    "Project",
    "ProjectError",
    "ProjectParseError",
    "ProjectWriteError",
    "PushRejectedError",
    "RegistryError",
    "RegistryNetworkError",
    "RegistryTimeoutError",
    "RepoInfo",
    "Result",
    "UpdatePlan",
    "UpdateType",
    "VCSError",
    "Version",
    "VersionConstraint",
    "collect_results",
    "compute_update_type",
    "create_update_plan",
    "determine_target_version",
]
