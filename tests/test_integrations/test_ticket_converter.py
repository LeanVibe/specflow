"""Tests for ticket converter."""

from uuid import uuid4

import pytest

from specflow.integrations.ticket_converter import TicketConverter
from specflow.models import TestCase, TicketDraft, TicketPriority, TicketType


@pytest.fixture
def basic_ticket_draft() -> TicketDraft:
    """Create basic ticket draft."""
    return TicketDraft(
        feature_id=uuid4(),
        ticket_type=TicketType.STORY,
        title="Implement user authentication",
        description="Add OAuth 2.0 authentication for users to sign in securely",
        acceptance_criteria=[
            "Users can sign in with Google",
            "Session persists for 30 days",
            "Users can sign out successfully",
        ],
        priority=TicketPriority.HIGH,
        labels=["authentication", "security"],
        story_points=5,
    )


@pytest.fixture
def ticket_with_test_cases() -> TicketDraft:
    """Create ticket draft with test cases."""
    return TicketDraft(
        feature_id=uuid4(),
        ticket_type=TicketType.TASK,
        title="Setup CI/CD pipeline",
        description="Configure automated testing and deployment",
        acceptance_criteria=[
            "Tests run on every PR",
            "Successful builds deploy to staging",
        ],
        test_cases=[
            TestCase(
                name="Test PR triggers CI",
                test_type="integration",
                description="Verify that creating a PR triggers the CI pipeline",
                given="A GitHub repository with CI configured",
                when="A pull request is created",
                then="CI pipeline starts automatically",
            ),
            TestCase(
                name="Test deployment to staging",
                test_type="e2e",
                description="Verify successful build deploys to staging",
                given="A successful build on main branch",
                when="Build completes",
                then="Application deploys to staging environment",
            ),
        ],
        priority=TicketPriority.MEDIUM,
    )


class TestDraftToJiraFormat:
    """Test conversion from TicketDraft to Jira API format."""

    def test_converts_basic_fields(self, basic_ticket_draft: TicketDraft) -> None:
        """Converts basic ticket fields to Jira format."""
        jira_data = TicketConverter.draft_to_jira_format(basic_ticket_draft, "PROJ")

        assert jira_data["fields"]["project"]["key"] == "PROJ"
        assert jira_data["fields"]["summary"] == "Implement user authentication"
        assert jira_data["fields"]["issuetype"]["name"] == "Story"
        assert "description" in jira_data["fields"]

    def test_converts_ticket_types_correctly(self) -> None:
        """Maps TicketType enum to Jira issue types."""
        test_cases = [
            (TicketType.STORY, "Story"),
            (TicketType.TASK, "Task"),
            (TicketType.BUG, "Bug"),
            (TicketType.EPIC, "Epic"),
        ]

        for ticket_type, expected_jira_type in test_cases:
            draft = TicketDraft(
                feature_id=uuid4(),
                ticket_type=ticket_type,
                title="Test ticket",
                description="Test description",
                acceptance_criteria=["AC1"],
            )

            jira_data = TicketConverter.draft_to_jira_format(draft, "PROJ")

            assert jira_data["fields"]["issuetype"]["name"] == expected_jira_type

    def test_converts_priority_levels(self) -> None:
        """Maps TicketPriority to Jira priority names."""
        priority_mapping = [
            (TicketPriority.HIGHEST, "Highest"),
            (TicketPriority.HIGH, "High"),
            (TicketPriority.MEDIUM, "Medium"),
            (TicketPriority.LOW, "Low"),
            (TicketPriority.LOWEST, "Lowest"),
        ]

        for ticket_priority, expected_jira_priority in priority_mapping:
            draft = TicketDraft(
                feature_id=uuid4(),
                ticket_type=TicketType.STORY,
                title="Test",
                description="Test",
                acceptance_criteria=["AC1"],
                priority=ticket_priority,
            )

            jira_data = TicketConverter.draft_to_jira_format(draft, "PROJ")

            assert jira_data["fields"]["priority"]["name"] == expected_jira_priority

    def test_includes_labels(self, basic_ticket_draft: TicketDraft) -> None:
        """Includes labels in Jira format."""
        jira_data = TicketConverter.draft_to_jira_format(basic_ticket_draft, "PROJ")

        assert "labels" in jira_data["fields"]
        assert "authentication" in jira_data["fields"]["labels"]
        assert "security" in jira_data["fields"]["labels"]

    def test_includes_story_points_when_present(self, basic_ticket_draft: TicketDraft) -> None:
        """Includes story points in custom field."""
        jira_data = TicketConverter.draft_to_jira_format(basic_ticket_draft, "PROJ")

        # Story points typically mapped to customfield_10016 in Jira
        assert any("customfield" in key for key in jira_data["fields"].keys())

    def test_handles_missing_optional_fields(self) -> None:
        """Handles ticket with minimal fields."""
        draft = TicketDraft(
            feature_id=uuid4(),
            ticket_type=TicketType.STORY,
            title="Minimal ticket",
            description="Basic description",
            acceptance_criteria=["Must work"],
        )

        jira_data = TicketConverter.draft_to_jira_format(draft, "PROJ")

        assert jira_data["fields"]["summary"] == "Minimal ticket"
        assert "description" in jira_data["fields"]


class TestDescriptionFormatting:
    """Test description formatting with acceptance criteria and test cases."""

    def test_formats_description_with_acceptance_criteria(
        self, basic_ticket_draft: TicketDraft
    ) -> None:
        """Formats description with acceptance criteria section."""
        formatted = TicketConverter.format_description(basic_ticket_draft)

        assert "OAuth 2.0 authentication" in formatted
        assert "Acceptance Criteria" in formatted or "acceptance criteria" in formatted.lower()
        assert "Users can sign in with Google" in formatted

    def test_formats_description_with_test_cases(
        self, ticket_with_test_cases: TicketDraft
    ) -> None:
        """Formats description with test cases section."""
        formatted = TicketConverter.format_description(ticket_with_test_cases)

        assert "automated testing" in formatted
        assert "Test PR triggers CI" in formatted
        assert "Test deployment to staging" in formatted

    def test_formats_test_cases_with_given_when_then(
        self, ticket_with_test_cases: TicketDraft
    ) -> None:
        """Includes Given-When-Then clauses in formatted output."""
        formatted = TicketConverter.format_description(ticket_with_test_cases)

        assert "Given" in formatted or "given" in formatted.lower()
        assert "When" in formatted or "when" in formatted.lower()
        assert "Then" in formatted or "then" in formatted.lower()

    def test_uses_jira_markdown_format(self, basic_ticket_draft: TicketDraft) -> None:
        """Uses Jira markdown syntax for formatting."""
        formatted = TicketConverter.format_description(basic_ticket_draft)

        # Should use Jira markdown (h2, bullets, etc.)
        # Jira uses h2. for headers, * for bullets
        assert "h2." in formatted or "h3." in formatted or "*" in formatted

    def test_handles_empty_acceptance_criteria(self) -> None:
        """Handles ticket with no acceptance criteria."""
        draft = TicketDraft(
            feature_id=uuid4(),
            ticket_type=TicketType.TASK,
            title="Simple task",
            description="Do something",
            acceptance_criteria=[],
        )

        formatted = TicketConverter.format_description(draft)

        assert "Do something" in formatted
        # Should not crash, just omit AC section

    def test_handles_empty_test_cases(self, basic_ticket_draft: TicketDraft) -> None:
        """Handles ticket with no test cases."""
        formatted = TicketConverter.format_description(basic_ticket_draft)

        assert "OAuth 2.0 authentication" in formatted
        # Should not crash, just omit test cases section


class TestPriorityMapping:
    """Test priority level mapping."""

    def test_maps_all_priority_levels(self) -> None:
        """All TicketPriority values map to valid Jira priorities."""
        priorities = [
            TicketPriority.HIGHEST,
            TicketPriority.HIGH,
            TicketPriority.MEDIUM,
            TicketPriority.LOW,
            TicketPriority.LOWEST,
        ]

        for priority in priorities:
            jira_priority = TicketConverter.map_priority(priority)

            assert isinstance(jira_priority, str)
            assert len(jira_priority) > 0
            assert jira_priority in ["Highest", "High", "Medium", "Low", "Lowest"]


class TestIssueTypeMapping:
    """Test issue type mapping."""

    def test_maps_all_issue_types(self) -> None:
        """All TicketType values map to valid Jira issue types."""
        types = [
            TicketType.STORY,
            TicketType.TASK,
            TicketType.BUG,
            TicketType.EPIC,
        ]

        for ticket_type in types:
            jira_type = TicketConverter.map_issue_type(ticket_type)

            assert isinstance(jira_type, str)
            assert len(jira_type) > 0
            assert jira_type in ["Story", "Task", "Bug", "Epic", "Sub-task"]


class TestCustomFields:
    """Test custom field handling."""

    def test_includes_custom_fields_from_draft(self) -> None:
        """Includes custom fields from draft in Jira format."""
        draft = TicketDraft(
            feature_id=uuid4(),
            ticket_type=TicketType.STORY,
            title="Custom fields test",
            description="Test",
            acceptance_criteria=["AC1"],
            custom_fields={
                "customfield_10001": "Sprint 1",
                "customfield_10002": ["Component A", "Component B"],
            },
        )

        jira_data = TicketConverter.draft_to_jira_format(draft, "PROJ")

        assert "customfield_10001" in jira_data["fields"]
        assert jira_data["fields"]["customfield_10001"] == "Sprint 1"
        assert "customfield_10002" in jira_data["fields"]
