"""Pydantic models for Product Requirements Documents (PRDs)."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


class RequirementType(str, Enum):
    """Type of requirement within a feature."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"
    EDGE_CASE = "edge_case"


class ComplexityLevel(str, Enum):
    """Complexity estimation for a feature."""

    TRIVIAL = "trivial"  # < 1 day
    SIMPLE = "simple"  # 1-3 days
    MODERATE = "moderate"  # 3-5 days
    COMPLEX = "complex"  # 1-2 weeks
    VERY_COMPLEX = "very_complex"  # 2+ weeks


class PriorityLevel(str, Enum):
    """Priority level for features and requirements."""

    CRITICAL = "critical"  # P0
    HIGH = "high"  # P1
    MEDIUM = "medium"  # P2
    LOW = "low"  # P3


class Requirement(BaseModel):
    """Individual requirement within a feature."""

    requirement_id: UUID = Field(default_factory=uuid4)
    description: str = Field(..., min_length=1, description="Clear description of the requirement")
    requirement_type: RequirementType = RequirementType.FUNCTIONAL
    priority: PriorityLevel = PriorityLevel.MEDIUM
    dependencies: list[UUID] = Field(default_factory=list, description="IDs of dependent requirements")
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="Specific acceptance criteria in Given/When/Then format"
    )
    edge_cases: list[str] = Field(default_factory=list, description="Edge cases to consider")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_acceptance_criteria(self) -> bool:
        """Check if requirement has acceptance criteria defined."""
        return len(self.acceptance_criteria) > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_blocked(self) -> bool:
        """Check if requirement is blocked by dependencies."""
        return len(self.dependencies) > 0


class Feature(BaseModel):
    """Feature within a PRD containing multiple requirements."""

    feature_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, description="Feature name")
    description: str = Field(..., min_length=1, description="Detailed feature description")
    user_story: str | None = Field(None, description="User story in 'As a...I want...So that' format")
    requirements: list[Requirement] = Field(default_factory=list, description="List of requirements")
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Feature-level acceptance criteria (aggregated from requirements)",
    )
    test_stubs: list[str] = Field(default_factory=list, description="Generated test case templates")
    priority: PriorityLevel = PriorityLevel.MEDIUM
    complexity: ComplexityLevel = ComplexityLevel.MODERATE
    estimated_days: float | None = Field(None, ge=0, description="Estimated development time in days")
    dependencies: list[UUID] = Field(default_factory=list, description="IDs of dependent features")
    tags: list[str] = Field(default_factory=list, description="Feature tags for categorization")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def requirement_count(self) -> int:
        """Total number of requirements in this feature."""
        return len(self.requirements)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def acceptance_criteria_count(self) -> int:
        """Total number of acceptance criteria."""
        return len(self.acceptance_criteria)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_complete(self) -> bool:
        """Check if feature has complete definition.

        A feature is considered complete if it has:
        - Name and description
        - At least one requirement
        - Acceptance criteria
        """
        return (
            bool(self.name)
            and bool(self.description)
            and len(self.requirements) > 0
            and len(self.acceptance_criteria) > 0
        )

    def calculate_priority_score(self) -> int:
        """Calculate numeric priority score (higher = more important).

        Returns:
            Priority score: Critical=4, High=3, Medium=2, Low=1
        """
        priority_scores = {
            PriorityLevel.CRITICAL: 4,
            PriorityLevel.HIGH: 3,
            PriorityLevel.MEDIUM: 2,
            PriorityLevel.LOW: 1,
        }
        return priority_scores[self.priority]


class PRDMetadata(BaseModel):
    """Metadata about the PRD document."""

    author: str | None = None
    version: str = "1.0"
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    source_format: str | None = Field(None, description="Original format: markdown, notion, gdocs")
    source_url: str | None = Field(None, description="URL of source document if applicable")
    tags: list[str] = Field(default_factory=list, description="Document tags")
    custom_fields: dict[str, Any] = Field(default_factory=dict, description="Custom metadata fields")


class PRDSection(BaseModel):
    """Section within a PRD document."""

    section_id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, description="Section title")
    content: str = Field(..., description="Section content")
    subsections: list["PRDSection"] = Field(default_factory=list, description="Nested subsections")
    order: int = Field(default=0, description="Section order in document")


class PRD(BaseModel):
    """Complete Product Requirements Document model."""

    prd_id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, description="PRD title")
    raw_content: str = Field(..., description="Original raw content of the PRD")
    parsed_sections: list[PRDSection] = Field(default_factory=list, description="Structured sections")
    features: list[Feature] = Field(default_factory=list, description="Extracted features")
    metadata: PRDMetadata = Field(default_factory=PRDMetadata, description="Document metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def feature_count(self) -> int:
        """Total number of features in the PRD."""
        return len(self.features)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_requirements(self) -> int:
        """Total number of requirements across all features."""
        return sum(feature.requirement_count for feature in self.features)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completion_percentage(self) -> float:
        """Percentage of features that are complete.

        Returns:
            Completion percentage (0-100).
        """
        if not self.features:
            return 0.0
        complete_count = sum(1 for feature in self.features if feature.is_complete)
        return (complete_count / len(self.features)) * 100

    def get_features_by_priority(self, priority: PriorityLevel) -> list[Feature]:
        """Get all features with specific priority level.

        Args:
            priority: Priority level to filter by.

        Returns:
            List of features matching the priority.
        """
        return [feature for feature in self.features if feature.priority == priority]

    def get_critical_features(self) -> list[Feature]:
        """Get all critical priority features.

        Returns:
            List of critical features.
        """
        return self.get_features_by_priority(PriorityLevel.CRITICAL)

    def get_feature_by_id(self, feature_id: UUID) -> Feature | None:
        """Get feature by its ID.

        Args:
            feature_id: UUID of the feature.

        Returns:
            Feature if found, None otherwise.
        """
        for feature in self.features:
            if feature.feature_id == feature_id:
                return feature
        return None
