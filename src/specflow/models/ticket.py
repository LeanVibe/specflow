"""Pydantic models for ticket management (Jira, Linear, etc.)."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


class TicketType(str, Enum):
    """Type of ticket in issue tracking systems."""

    STORY = "story"
    TASK = "task"
    BUG = "bug"
    EPIC = "epic"
    SUBTASK = "subtask"


class TicketPriority(str, Enum):
    """Ticket priority levels (Jira-compatible)."""

    HIGHEST = "highest"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    LOWEST = "lowest"


class TicketStatus(str, Enum):
    """Ticket status in workflow."""

    DRAFT = "draft"  # Not yet created
    TODO = "todo"  # Created but not started
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


class IntegrationPlatform(str, Enum):
    """Supported integration platforms."""

    JIRA = "jira"
    LINEAR = "linear"
    ASANA = "asana"
    AZURE_DEVOPS = "azure_devops"


class TestCase(BaseModel):
    """Test case template for a ticket."""

    test_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Test case name")
    test_type: str = Field(..., description="Type: unit, integration, e2e")
    description: str = Field(..., description="Test case description")
    given: str | None = Field(None, description="Given clause (precondition)")
    when: str | None = Field(None, description="When clause (action)")
    then: str | None = Field(None, description="Then clause (expected outcome)")


class TicketDraft(BaseModel):
    """Draft ticket before creation in external system.

    This model represents a ticket that has been generated but not yet
    pushed to Jira/Linear/etc. Allows for preview and editing before creation.
    """

    draft_id: UUID = Field(default_factory=uuid4)
    feature_id: UUID = Field(..., description="Source feature ID from PRD")
    ticket_type: TicketType = TicketType.STORY
    title: str = Field(..., min_length=1, max_length=255, description="Ticket title/summary")
    description: str = Field(..., description="Detailed ticket description (supports markdown)")
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="List of acceptance criteria"
    )
    test_cases: list[TestCase] = Field(default_factory=list, description="Test case templates")
    priority: TicketPriority = TicketPriority.MEDIUM
    labels: list[str] = Field(default_factory=list, description="Ticket labels/tags")
    story_points: int | None = Field(None, ge=0, description="Estimated story points")
    assignee: str | None = Field(None, description="Username or email of assignee")
    epic_link: str | None = Field(None, description="Link to parent epic")
    dependencies: list[UUID] = Field(default_factory=list, description="Dependent draft IDs")
    custom_fields: dict[str, Any] = Field(default_factory=dict, description="Platform-specific fields")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_acceptance_criteria(self) -> bool:
        """Check if ticket has acceptance criteria."""
        return len(self.acceptance_criteria) > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_test_cases(self) -> bool:
        """Check if ticket has test cases."""
        return len(self.test_cases) > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_complete_draft(self) -> bool:
        """Check if draft has all required fields for creation."""
        return (
            bool(self.title)
            and bool(self.description)
            and len(self.acceptance_criteria) > 0
            and len(self.test_cases) > 0
        )

    def to_description_html(self) -> str:
        """Convert draft to HTML description for ticket creation.

        Returns:
            HTML formatted description with AC and test cases.
        """
        html_parts = [f"<h2>Description</h2><p>{self.description}</p>"]

        if self.acceptance_criteria:
            html_parts.append("<h2>Acceptance Criteria</h2><ul>")
            for criterion in self.acceptance_criteria:
                html_parts.append(f"<li>{criterion}</li>")
            html_parts.append("</ul>")

        if self.test_cases:
            html_parts.append("<h2>Test Cases</h2><ul>")
            for test in self.test_cases:
                html_parts.append(f"<li><strong>{test.name}</strong>: {test.description}</li>")
            html_parts.append("</ul>")

        return "\n".join(html_parts)


class JiraTicket(BaseModel):
    """Created Jira ticket with all fields.

    This model represents a ticket that has been successfully created in Jira.
    It includes both the draft data and Jira-specific fields.
    """

    ticket_id: str = Field(..., description="Jira ticket ID (e.g., 'PROJ-123')")
    draft_id: UUID = Field(..., description="Source draft ID")
    project_key: str = Field(..., description="Jira project key")
    issue_key: str = Field(..., description="Full issue key (project-number)")
    summary: str = Field(..., description="Ticket summary/title")
    description_html: str = Field(..., description="HTML formatted description")
    acceptance_criteria: list[str] = Field(default_factory=list)
    test_cases: list[TestCase] = Field(default_factory=list)
    priority: str = Field(default="Medium")
    issue_type: str = Field(default="Story")
    status: str = Field(default="To Do")
    labels: list[str] = Field(default_factory=list)
    assignee: str | None = None
    reporter: str | None = None
    story_points: int | None = None
    epic_link: str | None = None
    sprint: str | None = Field(None, description="Sprint name or ID")
    components: list[str] = Field(default_factory=list, description="Jira components")
    fix_versions: list[str] = Field(default_factory=list, description="Target fix versions")
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    jira_url: str = Field(..., description="Direct URL to ticket in Jira")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_id(self) -> str:
        """Get display-friendly ticket ID."""
        return self.issue_key


class TicketBatch(BaseModel):
    """Batch of tickets for bulk creation with transaction handling."""

    batch_id: UUID = Field(default_factory=uuid4)
    prd_id: UUID = Field(..., description="Source PRD ID")
    platform: IntegrationPlatform = IntegrationPlatform.JIRA
    project_key: str = Field(..., description="Target project key")
    drafts: list[TicketDraft] = Field(..., min_length=1, description="Ticket drafts to create")
    created_tickets: list[JiraTicket] = Field(default_factory=list, description="Successfully created")
    failed_drafts: list[tuple[UUID, str]] = Field(
        default_factory=list, description="Failed drafts with error messages"
    )
    status: str = Field(default="pending", description="Batch status: pending, in_progress, completed, failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_count(self) -> int:
        """Total number of tickets in batch."""
        return len(self.drafts)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success_count(self) -> int:
        """Number of successfully created tickets."""
        return len(self.created_tickets)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_count(self) -> int:
        """Number of failed ticket creations."""
        return len(self.failed_drafts)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success_rate(self) -> float:
        """Success rate as percentage.

        Returns:
            Success rate 0-100%.
        """
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_complete(self) -> bool:
        """Check if batch processing is complete."""
        return self.status in ("completed", "failed")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_failures(self) -> bool:
        """Check if any tickets failed to create."""
        return len(self.failed_drafts) > 0


class TicketPreview(BaseModel):
    """Preview of tickets before creation for user review."""

    preview_id: UUID = Field(default_factory=uuid4)
    prd_id: UUID = Field(..., description="Source PRD ID")
    drafts: list[TicketDraft] = Field(..., description="Drafts to preview")
    estimated_create_time: float = Field(..., description="Estimated creation time in seconds")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ticket_count(self) -> int:
        """Number of tickets in preview."""
        return len(self.drafts)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_warnings(self) -> bool:
        """Check if there are validation warnings."""
        return len(self.warnings) > 0
