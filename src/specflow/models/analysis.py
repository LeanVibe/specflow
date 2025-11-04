"""Pydantic models for PRD analysis (ambiguity detection, quality scoring)."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


class AmbiguityType(str, Enum):
    """Type of ambiguity detected in requirements."""

    VAGUE_TERM = "vague_term"  # e.g., "fast", "easy", "user-friendly"
    MISSING_METRIC = "missing_metric"  # e.g., "quickly" without defining how fast
    MISSING_CONTEXT = "missing_context"  # Unclear who, what, when, where
    UNCLEAR_DEPENDENCY = "unclear_dependency"  # Unclear relationships
    SUBJECTIVE_LANGUAGE = "subjective_language"  # "beautiful", "intuitive"
    INCOMPLETE_CONDITION = "incomplete_condition"  # Missing if/then/else cases


class SeverityLevel(str, Enum):
    """Severity level of detected issues."""

    CRITICAL = "critical"  # Blocks implementation
    HIGH = "high"  # Likely to cause confusion
    MEDIUM = "medium"  # Should be clarified
    LOW = "low"  # Nice to clarify


class AmbiguityIssue(BaseModel):
    """Single ambiguity or unclear requirement detected in PRD."""

    issue_id: UUID = Field(default_factory=uuid4)
    feature_id: UUID | None = Field(None, description="Feature where issue was found")
    requirement_id: UUID | None = Field(None, description="Specific requirement if applicable")
    ambiguity_type: AmbiguityType
    severity: SeverityLevel
    original_text: str = Field(..., description="The ambiguous text")
    explanation: str = Field(..., description="Why this is ambiguous")
    suggestion: str = Field(..., description="Suggested improvement")
    position: dict[str, int] = Field(
        default_factory=dict, description="Position in document (line, char)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AmbiguityReport(BaseModel):
    """Complete ambiguity analysis report for a PRD."""

    report_id: UUID = Field(default_factory=uuid4)
    prd_id: UUID = Field(..., description="PRD being analyzed")
    issues: list[AmbiguityIssue] = Field(default_factory=list, description="Detected ambiguities")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    ai_model_used: str = Field(..., description="AI model used for analysis")
    analysis_duration_seconds: float = Field(..., ge=0, description="Time taken for analysis")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_issues(self) -> int:
        """Total number of ambiguities detected."""
        return len(self.issues)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def critical_count(self) -> int:
        """Number of critical severity issues."""
        return sum(1 for issue in self.issues if issue.severity == SeverityLevel.CRITICAL)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def high_count(self) -> int:
        """Number of high severity issues."""
        return sum(1 for issue in self.issues if issue.severity == SeverityLevel.HIGH)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are critical issues that should block ticket creation."""
        return self.critical_count > 0

    def get_issues_by_severity(self, severity: SeverityLevel) -> list[AmbiguityIssue]:
        """Get all issues of a specific severity level.

        Args:
            severity: Severity level to filter by.

        Returns:
            List of issues matching the severity.
        """
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_type(self, ambiguity_type: AmbiguityType) -> list[AmbiguityIssue]:
        """Get all issues of a specific type.

        Args:
            ambiguity_type: Type to filter by.

        Returns:
            List of issues matching the type.
        """
        return [issue for issue in self.issues if issue.ambiguity_type == ambiguity_type]


class QualityCheckCategory(str, Enum):
    """Category of quality check."""

    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    TESTABILITY = "testability"
    FEASIBILITY = "feasibility"


class QualityCheck(BaseModel):
    """Individual quality check result."""

    check_id: UUID = Field(default_factory=uuid4)
    category: QualityCheckCategory
    check_name: str = Field(..., description="Name of the check")
    passed: bool = Field(..., description="Whether check passed")
    score: float = Field(..., ge=0, le=100, description="Score for this check (0-100)")
    details: str = Field(..., description="Details about the check result")
    recommendations: list[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )


class QualityScore(BaseModel):
    """Definition of Ready score for a feature or PRD.

    Score components:
    - Completeness: Has all required fields (40%)
    - Clarity: No major ambiguities (30%)
    - Testability: Has testable acceptance criteria (20%)
    - Feasibility: Is implementable with current info (10%)
    """

    score_id: UUID = Field(default_factory=uuid4)
    feature_id: UUID | None = Field(None, description="Feature being scored")
    prd_id: UUID = Field(..., description="PRD being scored")
    checks: list[QualityCheck] = Field(default_factory=list, description="Individual check results")
    overall_score: float = Field(..., ge=0, le=100, description="Overall quality score (0-100)")
    is_ready: bool = Field(..., description="Whether feature meets Definition of Ready (>=80)")
    blocking_issues: list[str] = Field(
        default_factory=list, description="Issues that must be resolved"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Recommended improvements"
    )
    scored_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def grade(self) -> str:
        """Letter grade for the quality score.

        Returns:
            A (90-100), B (80-89), C (70-79), D (60-69), F (0-59)
        """
        if self.overall_score >= 90:
            return "A"
        elif self.overall_score >= 80:
            return "B"
        elif self.overall_score >= 70:
            return "C"
        elif self.overall_score >= 60:
            return "D"
        return "F"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are blocking issues."""
        return len(self.blocking_issues) > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completeness_score(self) -> float:
        """Get completeness category score."""
        completeness_checks = [
            check for check in self.checks if check.category == QualityCheckCategory.COMPLETENESS
        ]
        if not completeness_checks:
            return 0.0
        return sum(check.score for check in completeness_checks) / len(completeness_checks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def clarity_score(self) -> float:
        """Get clarity category score."""
        clarity_checks = [check for check in self.checks if check.category == QualityCheckCategory.CLARITY]
        if not clarity_checks:
            return 0.0
        return sum(check.score for check in clarity_checks) / len(clarity_checks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def testability_score(self) -> float:
        """Get testability category score."""
        testability_checks = [
            check for check in self.checks if check.category == QualityCheckCategory.TESTABILITY
        ]
        if not testability_checks:
            return 0.0
        return sum(check.score for check in testability_checks) / len(testability_checks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def feasibility_score(self) -> float:
        """Get feasibility category score."""
        feasibility_checks = [
            check for check in self.checks if check.category == QualityCheckCategory.FEASIBILITY
        ]
        if not feasibility_checks:
            return 0.0
        return sum(check.score for check in feasibility_checks) / len(feasibility_checks)


class DependencyGraph(BaseModel):
    """Dependency graph for features and requirements.

    Used to determine optimal creation order for tickets.
    """

    graph_id: UUID = Field(default_factory=uuid4)
    prd_id: UUID = Field(..., description="PRD being analyzed")
    nodes: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Feature/requirement nodes with metadata"
    )
    edges: list[tuple[str, str]] = Field(
        default_factory=list, description="Dependency edges (from_id, to_id)"
    )
    topological_order: list[str] = Field(
        default_factory=list, description="Ordered list of node IDs (dependencies first)"
    )
    cycles: list[list[str]] = Field(
        default_factory=list, description="Circular dependencies detected"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_cycles(self) -> bool:
        """Check if graph has circular dependencies."""
        return len(self.cycles) > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def node_count(self) -> int:
        """Total number of nodes in graph."""
        return len(self.nodes)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def edge_count(self) -> int:
        """Total number of edges (dependencies) in graph."""
        return len(self.edges)


class AnalysisSummary(BaseModel):
    """Complete analysis summary for a PRD including all metrics."""

    summary_id: UUID = Field(default_factory=uuid4)
    prd_id: UUID = Field(..., description="PRD being summarized")
    ambiguity_report: AmbiguityReport
    quality_scores: list[QualityScore] = Field(
        default_factory=list, description="Quality scores for each feature"
    )
    dependency_graph: DependencyGraph
    overall_readiness: float = Field(..., ge=0, le=100, description="Overall readiness score")
    recommended_ticket_order: list[UUID] = Field(
        default_factory=list, description="Recommended feature order for ticket creation"
    )
    estimated_implementation_days: float = Field(..., ge=0, description="Total estimated days")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_ready_for_tickets(self) -> bool:
        """Check if PRD is ready for ticket creation.

        Returns:
            True if overall readiness >= 80 and no critical ambiguities.
        """
        return self.overall_readiness >= 80 and not self.ambiguity_report.has_blocking_issues

    @computed_field  # type: ignore[prop-decorator]
    @property
    def average_quality_score(self) -> float:
        """Average quality score across all features."""
        if not self.quality_scores:
            return 0.0
        return sum(score.overall_score for score in self.quality_scores) / len(self.quality_scores)
