"""Tests for Jira API client."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from specflow.integrations.exceptions import (
    JiraAPIError,
    ProjectNotFoundError,
    RateLimitError,
    TicketCreationError,
)
from specflow.integrations.jira_client import JiraClient
from specflow.integrations.oauth_handler import JiraOAuthHandler
from specflow.integrations.oauth_models import OAuthToken
from specflow.models import TicketDraft, TicketPriority, TicketType


@pytest.fixture
def oauth_handler() -> JiraOAuthHandler:
    """Create OAuth handler with valid token."""
    handler = JiraOAuthHandler(
        client_id="test_client",
        client_secret="test_secret",
        redirect_uri="http://localhost:8000/callback",
    )
    token = OAuthToken(
        access_token="test_access_token",
        refresh_token="test_refresh",
        token_type="Bearer",
        expires_in=3600,
        scope="read:jira-work write:jira-work",
    )
    handler.store_token(token)
    return handler


@pytest.fixture
def jira_client(oauth_handler: JiraOAuthHandler) -> JiraClient:
    """Create Jira client for testing."""
    return JiraClient(
        base_url="https://test-instance.atlassian.net",
        oauth_handler=oauth_handler,
    )


@pytest.fixture
def sample_ticket_draft() -> TicketDraft:
    """Create sample ticket draft."""
    return TicketDraft(
        feature_id=uuid4(),
        ticket_type=TicketType.STORY,
        title="Implement user authentication",
        description="Add OAuth 2.0 authentication for users",
        acceptance_criteria=[
            "Users can sign in with Google",
            "Session persists for 30 days",
            "Users can sign out",
        ],
        priority=TicketPriority.HIGH,
        labels=["authentication", "security"],
        story_points=5,
    )


class TestJiraClientInitialization:
    """Test Jira client initialization."""

    def test_initialization_with_valid_config(
        self, oauth_handler: JiraOAuthHandler
    ) -> None:
        """Jira client initializes with valid configuration."""
        client = JiraClient(
            base_url="https://mycompany.atlassian.net",
            oauth_handler=oauth_handler,
        )

        assert client.base_url == "https://mycompany.atlassian.net"
        assert client.oauth_handler == oauth_handler

    def test_initialization_sets_api_base_url(self, jira_client: JiraClient) -> None:
        """Jira client constructs correct API base URL."""
        assert jira_client.api_base_url == "https://test-instance.atlassian.net/rest/api/3"

    def test_initialization_with_trailing_slash(
        self, oauth_handler: JiraOAuthHandler
    ) -> None:
        """Jira client handles base URL with trailing slash."""
        client = JiraClient(
            base_url="https://mycompany.atlassian.net/",
            oauth_handler=oauth_handler,
        )

        assert client.base_url == "https://mycompany.atlassian.net"
        assert client.api_base_url == "https://mycompany.atlassian.net/rest/api/3"


class TestProjectOperations:
    """Test project-related API operations."""

    @pytest.mark.asyncio
    async def test_get_project_success(
        self, jira_client: JiraClient, httpx_mock: MagicMock
    ) -> None:
        """Successfully fetch project metadata."""
        httpx_mock.add_response(
            method="GET",
            url="https://test-instance.atlassian.net/rest/api/3/project/PROJ",
            json={
                "id": "10000",
                "key": "PROJ",
                "name": "My Project",
                "projectTypeKey": "software",
            },
            status_code=200,
        )

        project = await jira_client.get_project(project_key="PROJ")

        assert project["key"] == "PROJ"
        assert project["name"] == "My Project"

    @pytest.mark.asyncio
    async def test_get_project_not_found(
        self, jira_client: JiraClient, httpx_mock: MagicMock
    ) -> None:
        """Raises error when project not found."""
        httpx_mock.add_response(
            method="GET",
            url="https://test-instance.atlassian.net/rest/api/3/project/NOTFOUND",
            json={"errorMessages": ["Project does not exist"]},
            status_code=404,
        )

        with pytest.raises(ProjectNotFoundError) as exc_info:
            await jira_client.get_project(project_key="NOTFOUND")

        assert "NOTFOUND" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_issue_types_success(
        self, jira_client: JiraClient, httpx_mock: MagicMock
    ) -> None:
        """Successfully fetch issue types for project."""
        httpx_mock.add_response(
            method="GET",
            url="https://test-instance.atlassian.net/rest/api/3/project/PROJ",
            json={
                "issueTypes": [
                    {"id": "10001", "name": "Story", "subtask": False},
                    {"id": "10002", "name": "Task", "subtask": False},
                    {"id": "10003", "name": "Bug", "subtask": False},
                ]
            },
            status_code=200,
        )

        issue_types = await jira_client.get_issue_types(project_key="PROJ")

        assert len(issue_types) == 3
        assert any(it["name"] == "Story" for it in issue_types)


class TestTicketCreation:
    """Test single ticket creation."""

    @pytest.mark.asyncio
    async def test_create_issue_success(
        self, jira_client: JiraClient, sample_ticket_draft: TicketDraft, httpx_mock: MagicMock
    ) -> None:
        """Successfully create Jira issue."""
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            json={
                "id": "10001",
                "key": "PROJ-123",
                "self": "https://test-instance.atlassian.net/rest/api/3/issue/10001",
            },
            status_code=201,
        )

        # Mock GET request for created issue details
        httpx_mock.add_response(
            method="GET",
            url="https://test-instance.atlassian.net/rest/api/3/issue/PROJ-123",
            json={
                "id": "10001",
                "key": "PROJ-123",
                "fields": {
                    "summary": sample_ticket_draft.title,
                    "description": {"type": "doc", "content": []},
                    "issuetype": {"name": "Story"},
                    "priority": {"name": "High"},
                    "status": {"name": "To Do"},
                },
            },
            status_code=200,
        )

        jira_ticket = await jira_client.create_issue(
            project_key="PROJ", ticket=sample_ticket_draft
        )

        assert jira_ticket.issue_key == "PROJ-123"
        assert jira_ticket.project_key == "PROJ"
        assert jira_ticket.draft_id == sample_ticket_draft.draft_id

    @pytest.mark.asyncio
    async def test_create_issue_with_invalid_project(
        self, jira_client: JiraClient, sample_ticket_draft: TicketDraft, httpx_mock: MagicMock
    ) -> None:
        """Raises error when creating issue in invalid project."""
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            json={"errorMessages": ["Project does not exist"]},
            status_code=404,
        )

        with pytest.raises(TicketCreationError) as exc_info:
            await jira_client.create_issue(project_key="INVALID", ticket=sample_ticket_draft)

        assert "INVALID" in str(exc_info.value) or "not exist" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_issue_with_validation_error(
        self, jira_client: JiraClient, sample_ticket_draft: TicketDraft, httpx_mock: MagicMock
    ) -> None:
        """Handles validation errors from Jira API."""
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            json={
                "errors": {
                    "summary": "Summary is required",
                    "issuetype": "Issue type is invalid",
                }
            },
            status_code=400,
        )

        with pytest.raises(TicketCreationError) as exc_info:
            await jira_client.create_issue(project_key="PROJ", ticket=sample_ticket_draft)

        error_msg = str(exc_info.value).lower()
        assert "validation" in error_msg or "required" in error_msg or "invalid" in error_msg


class TestBulkTicketCreation:
    """Test bulk ticket creation with transaction handling."""

    @pytest.mark.asyncio
    async def test_create_issues_bulk_all_success(
        self, jira_client: JiraClient, httpx_mock: MagicMock
    ) -> None:
        """Successfully create all tickets in batch."""
        drafts = [
            TicketDraft(
                feature_id=uuid4(),
                ticket_type=TicketType.STORY,
                title=f"Feature {i}",
                description=f"Description {i}",
                acceptance_criteria=["AC1", "AC2"],
                priority=TicketPriority.MEDIUM,
            )
            for i in range(3)
        ]

        # Mock successful creation for all tickets
        for i, draft in enumerate(drafts):
            httpx_mock.add_response(
                method="POST",
                url="https://test-instance.atlassian.net/rest/api/3/issue",
                json={
                    "id": f"1000{i}",
                    "key": f"PROJ-{i+1}",
                    "self": f"https://test-instance.atlassian.net/rest/api/3/issue/1000{i}",
                },
                status_code=201,
            )

            httpx_mock.add_response(
                method="GET",
                url=f"https://test-instance.atlassian.net/rest/api/3/issue/PROJ-{i+1}",
                json={
                    "key": f"PROJ-{i+1}",
                    "fields": {
                        "summary": draft.title,
                        "issuetype": {"name": "Story"},
                        "priority": {"name": "Medium"},
                        "status": {"name": "To Do"},
                    },
                },
                status_code=200,
            )

        batch = await jira_client.create_issues_bulk(project_key="PROJ", tickets=drafts)

        assert batch.success_count == 3
        assert batch.failed_count == 0
        assert batch.status == "completed"

    @pytest.mark.asyncio
    async def test_create_issues_bulk_partial_failure(
        self, jira_client: JiraClient, httpx_mock: MagicMock
    ) -> None:
        """Handles partial failure in bulk creation."""
        drafts = [
            TicketDraft(
                feature_id=uuid4(),
                ticket_type=TicketType.STORY,
                title=f"Feature {i}",
                description=f"Description {i}",
                acceptance_criteria=["AC1"],
                priority=TicketPriority.MEDIUM,
            )
            for i in range(3)
        ]

        # First ticket succeeds
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            json={"id": "10001", "key": "PROJ-1", "self": "https://test.atlassian.net/..."},
            status_code=201,
        )
        httpx_mock.add_response(
            method="GET",
            url="https://test-instance.atlassian.net/rest/api/3/issue/PROJ-1",
            json={
                "key": "PROJ-1",
                "fields": {
                    "summary": "Feature 0",
                    "issuetype": {"name": "Story"},
                    "status": {"name": "To Do"},
                },
            },
            status_code=200,
        )

        # Second ticket fails
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            json={"errorMessages": ["Validation failed"]},
            status_code=400,
        )

        # Third ticket succeeds
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            json={"id": "10003", "key": "PROJ-3", "self": "https://test.atlassian.net/..."},
            status_code=201,
        )
        httpx_mock.add_response(
            method="GET",
            url="https://test-instance.atlassian.net/rest/api/3/issue/PROJ-3",
            json={
                "key": "PROJ-3",
                "fields": {
                    "summary": "Feature 2",
                    "issuetype": {"name": "Story"},
                    "status": {"name": "To Do"},
                },
            },
            status_code=200,
        )

        batch = await jira_client.create_issues_bulk(project_key="PROJ", tickets=drafts)

        assert batch.success_count == 2
        assert batch.failed_count == 1
        assert batch.has_failures
        assert batch.status == "completed"


class TestRateLimiting:
    """Test rate limit handling."""

    @pytest.mark.asyncio
    async def test_handles_rate_limit_with_retry_after(
        self, jira_client: JiraClient, sample_ticket_draft: TicketDraft, httpx_mock: MagicMock
    ) -> None:
        """Handles rate limit error with Retry-After header."""
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            status_code=429,
            headers={"Retry-After": "60"},
        )

        with pytest.raises(RateLimitError) as exc_info:
            await jira_client.create_issue(project_key="PROJ", ticket=sample_ticket_draft)

        assert exc_info.value.retry_after == 60
        assert exc_info.value.status_code == 429


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retries_on_server_error(
        self, jira_client: JiraClient, sample_ticket_draft: TicketDraft, httpx_mock: MagicMock
    ) -> None:
        """Retries request on 5xx server errors."""
        # First two attempts fail with 500
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            status_code=500,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            status_code=500,
        )

        # Third attempt succeeds
        httpx_mock.add_response(
            method="POST",
            url="https://test-instance.atlassian.net/rest/api/3/issue",
            json={"id": "10001", "key": "PROJ-123", "self": "https://test.atlassian.net/..."},
            status_code=201,
        )
        httpx_mock.add_response(
            method="GET",
            url="https://test-instance.atlassian.net/rest/api/3/issue/PROJ-123",
            json={
                "key": "PROJ-123",
                "fields": {
                    "summary": sample_ticket_draft.title,
                    "issuetype": {"name": "Story"},
                    "status": {"name": "To Do"},
                },
            },
            status_code=200,
        )

        with patch("asyncio.sleep", return_value=None):  # Skip actual sleep
            jira_ticket = await jira_client.create_issue(
                project_key="PROJ", ticket=sample_ticket_draft
            )

        assert jira_ticket.issue_key == "PROJ-123"

    @pytest.mark.asyncio
    async def test_fails_after_max_retries(
        self, jira_client: JiraClient, sample_ticket_draft: TicketDraft, httpx_mock: MagicMock
    ) -> None:
        """Fails after exceeding max retry attempts."""
        # All attempts fail with 500
        for _ in range(4):  # Initial + 3 retries
            httpx_mock.add_response(
                method="POST",
                url="https://test-instance.atlassian.net/rest/api/3/issue",
                status_code=500,
            )

        with patch("asyncio.sleep", return_value=None):
            with pytest.raises(JiraAPIError) as exc_info:
                await jira_client.create_issue(project_key="PROJ", ticket=sample_ticket_draft)

            assert "max retries" in str(exc_info.value).lower() or "500" in str(exc_info.value)


class TestAuthenticationHeaders:
    """Test authentication header handling."""

    @pytest.mark.asyncio
    async def test_includes_bearer_token_in_request(
        self, jira_client: JiraClient, httpx_mock: MagicMock
    ) -> None:
        """Includes Bearer token in Authorization header."""
        httpx_mock.add_response(
            method="GET",
            url="https://test-instance.atlassian.net/rest/api/3/project/PROJ",
            json={"key": "PROJ", "name": "Project"},
            status_code=200,
        )

        await jira_client.get_project(project_key="PROJ")

        # Verify the request included the Authorization header
        requests = httpx_mock.get_requests()
        assert len(requests) > 0
        assert "Authorization" in requests[0].headers
        assert requests[0].headers["Authorization"] == "Bearer test_access_token"
