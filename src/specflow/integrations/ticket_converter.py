"""Convert TicketDraft to Jira API format."""

from typing import Any

from specflow.models import TicketDraft, TicketPriority, TicketType


class TicketConverter:
    """Convert SpecFlow ticket drafts to Jira API format.

    Handles mapping of ticket types, priorities, and formatting of
    descriptions with acceptance criteria and test cases.
    """

    # Jira story points field (commonly customfield_10016, may vary)
    STORY_POINTS_FIELD = "customfield_10016"

    @staticmethod
    def draft_to_jira_format(draft: TicketDraft, project_key: str) -> dict[str, Any]:
        """Convert TicketDraft to Jira API request format.

        Args:
            draft: Ticket draft to convert
            project_key: Jira project key

        Returns:
            Dictionary formatted for Jira API /issue endpoint
        """
        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": draft.title,
            "description": TicketConverter.format_description(draft),
            "issuetype": {"name": TicketConverter.map_issue_type(draft.ticket_type)},
            "priority": {"name": TicketConverter.map_priority(draft.priority)},
        }

        # Add labels if present
        if draft.labels:
            fields["labels"] = draft.labels

        # Add story points if present
        if draft.story_points is not None:
            fields[TicketConverter.STORY_POINTS_FIELD] = draft.story_points

        # Add assignee if present
        if draft.assignee:
            fields["assignee"] = {"name": draft.assignee}

        # Add epic link if present
        if draft.epic_link:
            # Epic link is typically customfield_10014, but may vary
            fields["customfield_10014"] = draft.epic_link

        # Add any custom fields from draft
        if draft.custom_fields:
            fields.update(draft.custom_fields)

        return {"fields": fields}

    @staticmethod
    def format_description(draft: TicketDraft) -> str:
        """Format ticket description with acceptance criteria and test cases.

        Uses Jira markdown format for proper rendering.

        Args:
            draft: Ticket draft to format

        Returns:
            Formatted description string in Jira markdown
        """
        parts = []

        # Main description
        parts.append(draft.description)
        parts.append("")  # Blank line

        # Acceptance Criteria section
        if draft.acceptance_criteria:
            parts.append("h3. Acceptance Criteria")
            parts.append("")
            for criterion in draft.acceptance_criteria:
                parts.append(f"* {criterion}")
            parts.append("")  # Blank line

        # Test Cases section
        if draft.test_cases:
            parts.append("h3. Test Cases")
            parts.append("")

            for test in draft.test_cases:
                parts.append(f"h4. {test.name}")
                parts.append(f"*Type:* {test.test_type}")
                parts.append(f"*Description:* {test.description}")
                parts.append("")

                # Add Given-When-Then if present
                if test.given or test.when or test.then:
                    if test.given:
                        parts.append(f"*Given:* {test.given}")
                    if test.when:
                        parts.append(f"*When:* {test.when}")
                    if test.then:
                        parts.append(f"*Then:* {test.then}")
                    parts.append("")

        return "\n".join(parts)

    @staticmethod
    def map_priority(priority: TicketPriority) -> str:
        """Map TicketPriority to Jira priority name.

        Args:
            priority: TicketPriority enum value

        Returns:
            Jira priority name
        """
        mapping = {
            TicketPriority.HIGHEST: "Highest",
            TicketPriority.HIGH: "High",
            TicketPriority.MEDIUM: "Medium",
            TicketPriority.LOW: "Low",
            TicketPriority.LOWEST: "Lowest",
        }
        return mapping.get(priority, "Medium")

    @staticmethod
    def map_issue_type(ticket_type: TicketType) -> str:
        """Map TicketType to Jira issue type name.

        Args:
            ticket_type: TicketType enum value

        Returns:
            Jira issue type name
        """
        mapping = {
            TicketType.STORY: "Story",
            TicketType.TASK: "Task",
            TicketType.BUG: "Bug",
            TicketType.EPIC: "Epic",
            TicketType.SUBTASK: "Sub-task",
        }
        return mapping.get(ticket_type, "Story")
