"""Tests for Jira OAuth handler."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from specflow.integrations.exceptions import (
    InvalidTokenError,
    JiraAuthError,
    TokenExpiredError,
)
from specflow.integrations.oauth_handler import JiraOAuthHandler
from specflow.integrations.oauth_models import OAuthToken


@pytest.fixture
def oauth_handler() -> JiraOAuthHandler:
    """Create OAuth handler for testing."""
    return JiraOAuthHandler(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="http://localhost:8000/callback",
    )


@pytest.fixture
def valid_token() -> OAuthToken:
    """Create valid OAuth token for testing."""
    return OAuthToken(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expires_in=3600,
        scope="read:jira-work write:jira-work",
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def expired_token() -> OAuthToken:
    """Create expired OAuth token for testing."""
    return OAuthToken(
        access_token="expired_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expires_in=3600,
        scope="read:jira-work write:jira-work",
        created_at=datetime.utcnow() - timedelta(hours=2),  # Expired 2 hours ago
    )


class TestOAuthHandlerInitialization:
    """Test OAuth handler initialization."""

    def test_initialization_with_valid_credentials(self) -> None:
        """OAuth handler initializes with valid credentials."""
        handler = JiraOAuthHandler(
            client_id="client_123",
            client_secret="secret_456",
            redirect_uri="http://localhost:8000/callback",
        )

        assert handler.client_id == "client_123"
        assert handler.client_secret == "secret_456"
        assert handler.redirect_uri == "http://localhost:8000/callback"

    def test_initialization_sets_correct_oauth_urls(self, oauth_handler: JiraOAuthHandler) -> None:
        """OAuth handler sets correct Atlassian OAuth URLs."""
        assert oauth_handler.authorization_url == "https://auth.atlassian.com/authorize"
        assert oauth_handler.token_url == "https://auth.atlassian.com/oauth/token"

    def test_initialization_with_custom_scopes(self) -> None:
        """OAuth handler accepts custom scopes."""
        handler = JiraOAuthHandler(
            client_id="client_123",
            client_secret="secret_456",
            redirect_uri="http://localhost:8000/callback",
            scopes="read:jira-work write:jira-work offline_access",
        )

        assert "offline_access" in handler.scopes


class TestAuthorizationURL:
    """Test authorization URL generation."""

    def test_get_authorization_url_returns_valid_url(
        self, oauth_handler: JiraOAuthHandler
    ) -> None:
        """Authorization URL contains all required parameters."""
        state = "random_state_123"
        url = oauth_handler.get_authorization_url(state=state)

        assert "https://auth.atlassian.com/authorize" in url
        assert f"client_id={oauth_handler.client_id}" in url
        assert f"state={state}" in url
        assert "response_type=code" in url
        assert "redirect_uri=" in url
        assert "scope=" in url

    def test_get_authorization_url_includes_audience(
        self, oauth_handler: JiraOAuthHandler
    ) -> None:
        """Authorization URL includes Jira API audience."""
        url = oauth_handler.get_authorization_url(state="test_state")

        assert "audience=api.atlassian.com" in url

    def test_get_authorization_url_with_prompt(self, oauth_handler: JiraOAuthHandler) -> None:
        """Authorization URL includes prompt parameter."""
        url = oauth_handler.get_authorization_url(state="test_state", prompt="consent")

        assert "prompt=consent" in url


class TestTokenExchange:
    """Test authorization code exchange for access token."""

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(
        self, oauth_handler: JiraOAuthHandler, httpx_mock: MagicMock
    ) -> None:
        """Successfully exchange authorization code for access token."""
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

        token = await oauth_handler.exchange_code_for_token(code="auth_code_123")

        assert token.access_token == "new_access_token"
        assert token.refresh_token == "new_refresh_token"
        assert token.expires_in == 3600
        assert token.token_type == "Bearer"
        assert not token.is_expired

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_with_invalid_code(
        self, oauth_handler: JiraOAuthHandler, httpx_mock: MagicMock
    ) -> None:
        """Exchange fails with invalid authorization code."""
        httpx_mock.add_response(
            method="POST",
            url="https://auth.atlassian.com/oauth/token",
            json={"error": "invalid_grant", "error_description": "Invalid authorization code"},
            status_code=400,
        )

        with pytest.raises(JiraAuthError) as exc_info:
            await oauth_handler.exchange_code_for_token(code="invalid_code")

        assert "invalid authorization code" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_network_error(
        self, oauth_handler: JiraOAuthHandler
    ) -> None:
        """Exchange handles network errors gracefully."""
        with patch.object(AsyncClient, "post", side_effect=Exception("Network error")):
            with pytest.raises(JiraAuthError) as exc_info:
                await oauth_handler.exchange_code_for_token(code="auth_code_123")

            assert "network" in str(exc_info.value).lower() or "error" in str(
                exc_info.value
            ).lower()


class TestTokenRefresh:
    """Test token refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, oauth_handler: JiraOAuthHandler, httpx_mock: MagicMock
    ) -> None:
        """Successfully refresh expired access token."""
        httpx_mock.add_response(
            method="POST",
            url="https://auth.atlassian.com/oauth/token",
            json={
                "access_token": "refreshed_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read:jira-work write:jira-work",
            },
            status_code=200,
        )

        new_token = await oauth_handler.refresh_token(refresh_token="old_refresh_token")

        assert new_token.access_token == "refreshed_access_token"
        assert new_token.refresh_token == "new_refresh_token"
        assert not new_token.is_expired

    @pytest.mark.asyncio
    async def test_refresh_token_with_invalid_refresh_token(
        self, oauth_handler: JiraOAuthHandler, httpx_mock: MagicMock
    ) -> None:
        """Refresh fails with invalid refresh token."""
        httpx_mock.add_response(
            method="POST",
            url="https://auth.atlassian.com/oauth/token",
            json={"error": "invalid_grant", "error_description": "Invalid refresh token"},
            status_code=400,
        )

        with pytest.raises(InvalidTokenError) as exc_info:
            await oauth_handler.refresh_token(refresh_token="invalid_refresh_token")

        assert "invalid refresh token" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_refresh_token_with_expired_refresh_token(
        self, oauth_handler: JiraOAuthHandler, httpx_mock: MagicMock
    ) -> None:
        """Refresh fails with expired refresh token."""
        httpx_mock.add_response(
            method="POST",
            url="https://auth.atlassian.com/oauth/token",
            json={
                "error": "invalid_grant",
                "error_description": "Refresh token has expired",
            },
            status_code=400,
        )

        with pytest.raises(TokenExpiredError) as exc_info:
            await oauth_handler.refresh_token(refresh_token="expired_refresh_token")

        assert "expired" in str(exc_info.value).lower()


class TestTokenValidation:
    """Test token validation and expiry checks."""

    def test_is_token_expired_with_valid_token(
        self, oauth_handler: JiraOAuthHandler, valid_token: OAuthToken
    ) -> None:
        """Valid token is not expired."""
        assert not oauth_handler.is_token_expired(valid_token)

    def test_is_token_expired_with_expired_token(
        self, oauth_handler: JiraOAuthHandler, expired_token: OAuthToken
    ) -> None:
        """Expired token is detected."""
        assert oauth_handler.is_token_expired(expired_token)

    def test_is_token_expired_with_soon_to_expire_token(
        self, oauth_handler: JiraOAuthHandler
    ) -> None:
        """Token expiring in <60s is considered expired (safety buffer)."""
        soon_expired = OAuthToken(
            access_token="soon_expired",
            refresh_token="test_refresh",
            token_type="Bearer",
            expires_in=3600,
            scope="read:jira-work",
            created_at=datetime.utcnow() - timedelta(seconds=3550),  # Expires in 10s
        )

        assert oauth_handler.is_token_expired(soon_expired)


class TestTokenStorage:
    """Test token storage and retrieval."""

    def test_store_token_saves_token(
        self, oauth_handler: JiraOAuthHandler, valid_token: OAuthToken
    ) -> None:
        """Token can be stored in handler."""
        oauth_handler.store_token(valid_token)

        assert oauth_handler.current_token == valid_token

    def test_get_token_returns_stored_token(
        self, oauth_handler: JiraOAuthHandler, valid_token: OAuthToken
    ) -> None:
        """Stored token can be retrieved."""
        oauth_handler.store_token(valid_token)
        retrieved_token = oauth_handler.get_token()

        assert retrieved_token == valid_token

    def test_get_token_returns_none_when_no_token(self, oauth_handler: JiraOAuthHandler) -> None:
        """Returns None when no token is stored."""
        assert oauth_handler.get_token() is None

    def test_clear_token_removes_stored_token(
        self, oauth_handler: JiraOAuthHandler, valid_token: OAuthToken
    ) -> None:
        """Stored token can be cleared."""
        oauth_handler.store_token(valid_token)
        oauth_handler.clear_token()

        assert oauth_handler.get_token() is None


class TestAutoTokenRefresh:
    """Test automatic token refresh before expiry."""

    @pytest.mark.asyncio
    async def test_get_valid_token_returns_current_token_if_valid(
        self, oauth_handler: JiraOAuthHandler, valid_token: OAuthToken
    ) -> None:
        """Returns current token if it's still valid."""
        oauth_handler.store_token(valid_token)

        token = await oauth_handler.get_valid_token()

        assert token == valid_token

    @pytest.mark.asyncio
    async def test_get_valid_token_refreshes_expired_token(
        self, oauth_handler: JiraOAuthHandler, expired_token: OAuthToken, httpx_mock: MagicMock
    ) -> None:
        """Automatically refreshes expired token."""
        oauth_handler.store_token(expired_token)

        httpx_mock.add_response(
            method="POST",
            url="https://auth.atlassian.com/oauth/token",
            json={
                "access_token": "refreshed_token",
                "refresh_token": "new_refresh",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read:jira-work",
            },
            status_code=200,
        )

        token = await oauth_handler.get_valid_token()

        assert token.access_token == "refreshed_token"
        assert not token.is_expired

    @pytest.mark.asyncio
    async def test_get_valid_token_raises_when_no_token_stored(
        self, oauth_handler: JiraOAuthHandler
    ) -> None:
        """Raises error when no token is stored."""
        with pytest.raises(JiraAuthError) as exc_info:
            await oauth_handler.get_valid_token()

        assert "no token" in str(exc_info.value).lower()
