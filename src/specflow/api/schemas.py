"""FastAPI request and response schemas for SpecFlow API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from specflow.models import (
    ComplexityLevel,
    PriorityLevel,
    TicketPriority,
    TicketType,
)

# ============================================================================
# PRD Schemas
# ============================================================================


class PRDParseRequest(BaseModel):
    """Request to parse PRD content into structured format."""

    content: str = Field(..., min_length=1, description="Raw PRD content to parse")
    format: str = Field(
        default="markdown",
        pattern="^(markdown|notion|gdocs)$",
        description="Format of the PRD content",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata about the PRD"
    )


class FeatureSchema(BaseModel):
    """Feature schema for API responses."""

    feature_id: UUID
    name: str
    description: str
    user_story: str | None
    requirement_count: int
    acceptance_criteria_count: int
    priority: PriorityLevel
    complexity: ComplexityLevel
    estimated_days: float | None
    is_complete: bool
    tags: list[str]


class PRDResponse(BaseModel):
    """Response with parsed PRD information."""

    prd_id: UUID
    title: str
    feature_count: int
    total_requirements: int
    completion_percentage: float
    features: list[FeatureSchema]
    created_at: datetime


class PRDAnalysisRequest(BaseModel):
    """Request to analyze PRD for quality and ambiguities."""

    prd_id: UUID


class AmbiguityIssueSchema(BaseModel):
    """Schema for ambiguity issues in API responses."""

    issue_type: str
    severity: str
    location: str
    description: str
    suggestion: str


class FeatureQualitySchema(BaseModel):
    """Schema for feature quality scores."""

    feature_id: UUID
    feature_name: str
    overall_score: float
    completeness_score: float
    clarity_score: float
    testability_score: float
    is_ready: bool
    missing_elements: list[str]


class PRDAnalysisResponse(BaseModel):
    """Response with PRD analysis results."""

    prd_id: UUID
    ambiguity_count: int
    critical_issues: int
    warnings: int
    average_quality_score: float
    ambiguity_issues: list[AmbiguityIssueSchema]
    feature_quality_scores: list[FeatureQualitySchema]
    analyzed_at: datetime


# ============================================================================
# Ticket Schemas
# ============================================================================


class TicketPreviewRequest(BaseModel):
    """Request to preview tickets without creating in Jira."""

    prd_id: UUID = Field(..., description="PRD ID to generate tickets from")
    project_key: str = Field(..., pattern="^[A-Z0-9]+$", description="Jira project key")
    feature_ids: list[UUID] | None = Field(
        None, description="Specific feature IDs to convert (None = all features)"
    )


class TestCaseSchema(BaseModel):
    """Test case schema for API responses."""

    test_id: UUID
    name: str
    test_type: str
    description: str
    given: str | None
    when: str | None
    then: str | None


class TicketDraftSchema(BaseModel):
    """Ticket draft schema for API responses."""

    draft_id: UUID
    feature_id: UUID
    ticket_type: TicketType
    title: str
    description: str
    acceptance_criteria: list[str]
    test_cases: list[TestCaseSchema]
    priority: TicketPriority
    labels: list[str]
    story_points: int | None
    is_complete_draft: bool


class TicketPreviewResponse(BaseModel):
    """Response with ticket preview information."""

    preview_id: UUID
    prd_id: UUID
    project_key: str
    drafts: list[TicketDraftSchema]
    ticket_count: int
    estimated_create_time: float
    warnings: list[str]
    has_warnings: bool
    created_at: datetime


class TicketCreateRequest(BaseModel):
    """Request to create tickets in Jira."""

    prd_id: UUID = Field(..., description="PRD ID to create tickets from")
    project_key: str = Field(..., pattern="^[A-Z0-9]+$", description="Jira project key")
    feature_ids: list[UUID] | None = Field(
        None, description="Specific feature IDs to create tickets for (None = all)"
    )
    assignee: str | None = Field(None, description="Default assignee username/email")
    epic_link: str | None = Field(None, description="Link to parent epic")
    labels: list[str] = Field(default_factory=list, description="Additional labels to add")


class JiraTicketSchema(BaseModel):
    """Created Jira ticket schema for API responses."""

    ticket_id: str
    draft_id: UUID
    issue_key: str
    summary: str
    priority: str
    issue_type: str
    status: str
    jira_url: str
    created_at: datetime


class TicketBatchResponse(BaseModel):
    """Response with batch ticket creation results."""

    batch_id: UUID
    prd_id: UUID
    project_key: str
    total_count: int
    success_count: int
    failed_count: int
    success_rate: float
    status: str
    created_tickets: list[JiraTicketSchema]
    failed_drafts: list[dict[str, str]]
    is_complete: bool
    has_failures: bool
    created_at: datetime
    completed_at: datetime | None


# ============================================================================
# OAuth Schemas
# ============================================================================


class OAuthAuthorizeResponse(BaseModel):
    """Response with OAuth authorization URL."""

    authorization_url: str
    state: str
    expires_at: datetime


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request with authorization code."""

    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="State parameter for CSRF protection")


class OAuthTokenResponse(BaseModel):
    """Response with OAuth token information."""

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    refresh_token: str | None


class OAuthStatusResponse(BaseModel):
    """Response with OAuth connection status."""

    is_connected: bool
    platform: str
    expires_at: datetime | None
    scopes: list[str]
    user_info: dict[str, Any] | None


# ============================================================================
# Error Schemas
# ============================================================================


class ErrorDetail(BaseModel):
    """Detailed error information."""

    field: str | None = None
    message: str
    code: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str
    message: str
    details: list[ErrorDetail] | None = None
    request_id: str | None = None


# ============================================================================
# Health Check Schema
# ============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
