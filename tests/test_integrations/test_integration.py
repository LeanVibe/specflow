"""End-to-end integration tests for Jira workflow."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from specflow.integrations import JiraClient, JiraOAuthHandler, TicketConverter
from specflow.integrations.oauth_models import OAuthToken
from specflow.models import TicketDraft, TicketPriority, TicketType


@pytest.fixture
def mock_oauth_token() -> OAuthToken:
    """Create mock OAuth token."""
    return OAuthToken(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expires_in=3600,
        scope="read:jira-work write:jira-work",
    )


@pytest.fixture
def oauth_handler_with_token(mock_oauth_token: OAuthToken) -> JiraOAuthHandler:
    """Create OAuth handler with stored token."""
    handler = JiraOAuthHandler(
        client_id="test_client",
        client_secret="test_secret",
        redirect_uri="http://localhost:8000/callback",
    )
    handler.store_token(mock_oauth_token)
    return handler


@pytest.fixture
def jira_client(oauth_handler_with_token: JiraOAuthHandler) -> JiraClient:
    """Create configured Jira client."""
    return JiraClient(
        base_url="https://test-company.atlassian.net",
        oauth_handler=oauth_handler_with_token,
    )


@pytest.fixture
def sample_drafts() -> list[TicketDraft]:
    """Create sample ticket drafts for testing."""
    feature_id = uuid4()
    return [
        TicketDraft(
            feature_id=feature_id,
            ticket_type=TicketType.EPIC,
            title="User Management System",
            description="Implement complete user management with authentication and authorization",
            acceptance_criteria=[
                "Users can register and login",
                "Admin can manage user permissions",
                "User sessions are secure",
            ],
            priority=TicketPriority.HIGHEST,
            labels=["user-management", "security"],
        ),
        TicketDraft(
            feature_id=feature_id,
            ticket_type=TicketType.STORY,
            title="Implement OAuth 2.0 authentication",
            description="Add OAuth 2.0 authentication for third-party sign-in",
            acceptance_criteria=[
                "Users can sign in with Google",
                "Users can sign in with GitHub",
                "Sessions persist for 30 days",
            ],
            priority=TicketPriority.HIGH,
            labels=["authentication", "oauth"],
            story_points=8,
        ),
        TicketDraft(
            feature_id=feature_id,
            ticket_type=TicketType.TASK,
            title="Setup authentication database tables",
            description="Create database schema for user authentication",
            acceptance_criteria=[
                "Users table created",
                "OAuth tokens table created",
                "Proper indexes applied",
            ],
            priority=TicketPriority.MEDIUM,
            labels=["database", "setup"],
            story_points=3,
        ),
    ]


class TestOAuthFlow:
    """Test complete OAuth authentication flow."""

    def test_generate_authorization_url(self) -> None:
        """Generate authorization URL for user redirect."""
        handler = JiraOAuthHandler(
            client_id="test_client_123",
            client_secret="test_secret_456",
            redirect_uri="http://localhost:8000/callback",
        )

        state = handler.generate_state()
        auth_url = handler.get_authorization_url(state=state)

        assert "https://auth.atlassian.com/authorize" in auth_url
        assert "client_id=test_client_123" in auth_url
        assert f"state={state}" in auth_url
        assert "response_type=code" in auth_url

    @pytest.mark.asyncio
    async def test_complete_oauth_flow(self, httpx_mock: MagicMock) -> None:
        """Complete OAuth flow: authorize → exchange code → store token."""
        handler = JiraOAuthHandler(
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:8000/callback",
        )

        # Step 1: Generate authorization URL
        state = handler.generate_state()
        auth_url = handler.get_authorization_url(state)
        assert "authorize" in auth_url

        # Step 2: Mock token exchange
        httpx_mock.add_response(
            method="POST",
            url="https://auth.atlassian.com/oauth/token",
            json={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read:jira-work write:jira-work",
            },
            status_code=200,
        )

        # Exchange authorization code for token
        token = await handler.exchange_code_for_token(code="auth_code_from_callback")

        # Step 3: Store token
        handler.store_token(token)

        assert handler.get_token() is not None
        assert handler.get_token().access_token == "new_access_token"


class TestTicketConversion:
    """Test ticket draft to Jira format conversion."""

    def test_convert_single_draft_to_jira_format(self, sample_drafts: list[TicketDraft]) -> None:
        """Convert single ticket draft to Jira API format."""
        epic_draft = sample_drafts[0]  # Epic

        jira_data = TicketConverter.draft_to_jira_format(epic_draft, project_key="PROJ")

        assert jira_data["fields"]["project"]["key"] == "PROJ"
        assert jira_data["fields"]["summary"] == "User Management System"
        assert jira_data["fields"]["issuetype"]["name"] == "Epic"
        assert jira_data["fields"]["priority"]["name"] == "Highest"
        assert "user-management" in jira_data["fields"]["labels"]

    def test_format_description_with_acceptance_criteria(
        self, sample_drafts: list[TicketDraft]
    ) -> None:
        """Format description includes acceptance criteria in Jira markdown."""
        story_draft = sample_drafts[1]  # Story

        formatted_desc = TicketConverter.format_description(story_draft)

        assert "OAuth 2.0 authentication" in formatted_desc
        assert "Acceptance Criteria" in formatted_desc or "h3." in formatted_desc
        assert "sign in with Google" in formatted_desc


class TestEndToEndTicketCreation:
    """Test complete flow: OAuth → Convert → Create ticket."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_single_ticket_end_to_end(
        self,
        jira_client: JiraClient,
        sample_drafts: list[TicketDraft],
        httpx_mock: MagicMock,
    ) -> None:
        """Complete flow: authenticate → convert → create ticket in Jira."""
        story_draft = sample_drafts[1]  # OAuth story

        # Mock Jira API responses
        httpx_mock.add_response(
            method="POST",
            url="https://test-company.atlassian.net/rest/api/3/issue",
            json={
                "id": "10001",
                "key": "PROJ-42",
                "self": "https://test-company.atlassian.net/rest/api/3/issue/10001",
            },
            status_code=201,
        )

        httpx_mock.add_response(
            method="GET",
            url="https://test-company.atlassian.net/rest/api/3/issue/PROJ-42",
            json={
                "id": "10001",
                "key": "PROJ-42",
                "fields": {
                    "summary": story_draft.title,
                    "description": "OAuth implementation",
                    "issuetype": {"name": "Story"},
                    "priority": {"name": "High"},
                    "status": {"name": "To Do"},
                    "labels": ["authentication", "oauth"],
                },
            },
            status_code=200,
        )

        # Create ticket
        jira_ticket = await jira_client.create_issue(project_key="PROJ", ticket=story_draft)

        assert jira_ticket.issue_key == "PROJ-42"
        assert jira_ticket.project_key == "PROJ"
        assert jira_ticket.summary == story_draft.title
        assert jira_ticket.draft_id == story_draft.draft_id
        assert "https://test-company.atlassian.net/browse/PROJ-42" in jira_ticket.jira_url

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_multiple_tickets_bulk(
        self,
        jira_client: JiraClient,
        sample_drafts: list[TicketDraft],
        httpx_mock: MagicMock,
    ) -> None:
        """Create multiple tickets in bulk with transaction tracking."""
        # Mock responses for each ticket
        for i, draft in enumerate(sample_drafts):
            httpx_mock.add_response(
                method="POST",
                url="https://test-company.atlassian.net/rest/api/3/issue",
                json={
                    "id": f"1000{i}",
                    "key": f"PROJ-{i+1}",
                    "self": f"https://test-company.atlassian.net/rest/api/3/issue/1000{i}",
                },
                status_code=201,
            )

            httpx_mock.add_response(
                method="GET",
                url=f"https://test-company.atlassian.net/rest/api/3/issue/PROJ-{i+1}",
                json={
                    "id": f"1000{i}",
                    "key": f"PROJ-{i+1}",
                    "fields": {
                        "summary": draft.title,
                        "issuetype": {"name": draft.ticket_type.value.capitalize()},
                        "priority": {"name": draft.priority.value.capitalize()},
                        "status": {"name": "To Do"},
                    },
                },
                status_code=200,
            )

        # Create tickets in bulk
        batch = await jira_client.create_issues_bulk(project_key="PROJ", tickets=sample_drafts)

        assert batch.success_count == 3
        assert batch.failed_count == 0
        assert batch.success_rate == 100.0
        assert batch.status == "completed"
        assert len(batch.created_tickets) == 3

        # Verify all tickets created
        issue_keys = [ticket.issue_key for ticket in batch.created_tickets]
        assert "PROJ-1" in issue_keys
        assert "PROJ-2" in issue_keys
        assert "PROJ-3" in issue_keys


class TestErrorHandling:
    """Test error handling in integration flow."""

    @pytest.mark.asyncio
    async def test_handles_authentication_failure(self) -> None:
        """Handle authentication failure when no token is stored."""
        from specflow.integrations.exceptions import JiraAuthError

        # Create handler without token
        handler = JiraOAuthHandler(
            client_id="test",
            client_secret="secret",
            redirect_uri="http://localhost:8000/callback",
        )

        # Try to get valid token without storing one first
        with pytest.raises(JiraAuthError) as exc_info:
            await handler.get_valid_token()

        assert "no token" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handles_project_not_found(
        self, jira_client: JiraClient, httpx_mock: MagicMock
    ) -> None:
        """Handle project not found error."""
        from specflow.integrations.exceptions import ProjectNotFoundError

        httpx_mock.add_response(
            method="GET",
            url="https://test-company.atlassian.net/rest/api/3/project/NOTFOUND",
            json={"errorMessages": ["Project does not exist"]},
            status_code=404,
        )

        with pytest.raises(ProjectNotFoundError):
            await jira_client.get_project(project_key="NOTFOUND")


class TestConfigurationValidation:
    """Test configuration and setup validation."""

    def test_oauth_handler_initialization(self) -> None:
        """OAuth handler initializes with correct configuration."""
        handler = JiraOAuthHandler(
            client_id="client_123",
            client_secret="secret_456",
            redirect_uri="http://localhost:8000/callback",
            scopes="read:jira-work write:jira-work offline_access",
        )

        assert handler.client_id == "client_123"
        assert "offline_access" in handler.scopes

    def test_jira_client_configuration(self, oauth_handler_with_token: JiraOAuthHandler) -> None:
        """Jira client configures API endpoints correctly."""
        client = JiraClient(
            base_url="https://mycompany.atlassian.net",
            oauth_handler=oauth_handler_with_token,
        )

        assert client.api_base_url == "https://mycompany.atlassian.net/rest/api/3"
        assert client.timeout == 30.0
