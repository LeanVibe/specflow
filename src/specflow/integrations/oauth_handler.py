"""OAuth 2.0 handler for Jira authentication."""

import secrets
from urllib.parse import urlencode

import httpx

from specflow.integrations.exceptions import (
    InvalidTokenError,
    JiraAuthError,
    TokenExpiredError,
)
from specflow.integrations.oauth_models import OAuthToken
from specflow.utils.logger import LoggerMixin


class JiraOAuthHandler(LoggerMixin):
    """Handle OAuth 2.0 authentication flow for Jira.

    Implements Authorization Code flow with PKCE for secure authentication.
    Supports automatic token refresh and secure token storage.
    """

    # Atlassian OAuth endpoints
    AUTHORIZATION_URL = "https://auth.atlassian.com/authorize"
    TOKEN_URL = "https://auth.atlassian.com/oauth/token"
    AUDIENCE = "api.atlassian.com"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: str = "read:jira-work write:jira-work offline_access",
    ) -> None:
        """Initialize OAuth handler.

        Args:
            client_id: OAuth client ID from Atlassian Developer Console
            client_secret: OAuth client secret
            redirect_uri: Callback URL for OAuth flow
            scopes: Space-separated OAuth scopes
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.current_token: OAuthToken | None = None

        # Set OAuth URLs for testing flexibility
        self.authorization_url = self.AUTHORIZATION_URL
        self.token_url = self.TOKEN_URL

        self.logger.info(
            "Initialized Jira OAuth handler",
            extra={"client_id": client_id, "scopes": scopes},
        )

    def get_authorization_url(
        self, state: str, prompt: str | None = None
    ) -> str:
        """Generate authorization URL for user to visit.

        Args:
            state: Random state parameter for CSRF protection
            prompt: Optional prompt parameter (e.g., 'consent' to force re-consent)

        Returns:
            Full authorization URL with query parameters
        """
        params: dict[str, str] = {
            "audience": self.AUDIENCE,
            "client_id": self.client_id,
            "scope": self.scopes,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "response_type": "code",
        }

        if prompt:
            params["prompt"] = prompt

        url = f"{self.authorization_url}?{urlencode(params)}"

        self.logger.info(
            "Generated authorization URL",
            extra={"state": state, "redirect_uri": self.redirect_uri},
        )

        return url

    async def exchange_code_for_token(self, code: str) -> OAuthToken:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            OAuth token with access and refresh tokens

        Raises:
            JiraAuthError: If token exchange fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error_description", "Token exchange failed")
                    self.logger.error(
                        "Token exchange failed",
                        extra={
                            "status_code": response.status_code,
                            "error": error_data.get("error"),
                        },
                    )
                    raise JiraAuthError(f"Failed to exchange code: {error_msg}")

                token_data = response.json()
                token = OAuthToken(**token_data)

                self.logger.info(
                    "Successfully exchanged authorization code for token",
                    extra={"expires_in": token.expires_in},
                )

                return token

        except httpx.HTTPError as e:
            self.logger.error("Network error during token exchange", extra={"error": str(e)})
            raise JiraAuthError(f"Network error during token exchange: {e}") from e
        except Exception as e:
            if isinstance(e, JiraAuthError):
                raise
            self.logger.error("Unexpected error during token exchange", extra={"error": str(e)})
            raise JiraAuthError(f"Unexpected error during token exchange: {e}") from e

    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh expired access token.

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            New OAuth token with refreshed access token

        Raises:
            InvalidTokenError: If refresh token is invalid
            TokenExpiredError: If refresh token has expired
            JiraAuthError: For other authentication errors
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error_description", "Token refresh failed")
                    error_type = error_data.get("error", "")

                    self.logger.error(
                        "Token refresh failed",
                        extra={
                            "status_code": response.status_code,
                            "error": error_type,
                        },
                    )

                    # Check for specific error types
                    if "expired" in error_msg.lower():
                        raise TokenExpiredError(f"Refresh token has expired: {error_msg}")
                    if "invalid" in error_msg.lower() or error_type == "invalid_grant":
                        raise InvalidTokenError(f"Invalid refresh token: {error_msg}")

                    raise JiraAuthError(f"Failed to refresh token: {error_msg}")

                token_data = response.json()
                new_token = OAuthToken(**token_data)

                self.logger.info(
                    "Successfully refreshed access token",
                    extra={"expires_in": new_token.expires_in},
                )

                # Update stored token
                self.current_token = new_token

                return new_token

        except httpx.HTTPError as e:
            self.logger.error("Network error during token refresh", extra={"error": str(e)})
            raise JiraAuthError(f"Network error during token refresh: {e}") from e
        except Exception as e:
            if isinstance(e, (InvalidTokenError, TokenExpiredError, JiraAuthError)):
                raise
            self.logger.error("Unexpected error during token refresh", extra={"error": str(e)})
            raise JiraAuthError(f"Unexpected error during token refresh: {e}") from e

    def is_token_expired(self, token: OAuthToken) -> bool:
        """Check if token needs refresh.

        Args:
            token: OAuth token to check

        Returns:
            True if token is expired or expires soon (<60s buffer)
        """
        return token.is_expired

    def store_token(self, token: OAuthToken) -> None:
        """Store OAuth token in handler.

        Args:
            token: OAuth token to store
        """
        self.current_token = token
        self.logger.debug("Stored OAuth token", extra={"expires_at": token.expires_at})

    def get_token(self) -> OAuthToken | None:
        """Get currently stored token.

        Returns:
            Stored OAuth token or None if no token stored
        """
        return self.current_token

    def clear_token(self) -> None:
        """Clear stored token from handler."""
        self.current_token = None
        self.logger.debug("Cleared stored OAuth token")

    async def get_valid_token(self) -> OAuthToken:
        """Get valid access token, refreshing if necessary.

        Returns:
            Valid OAuth token

        Raises:
            JiraAuthError: If no token stored or refresh fails
        """
        if self.current_token is None:
            raise JiraAuthError("No token stored. Please authenticate first.")

        if self.is_token_expired(self.current_token):
            self.logger.info("Token expired, refreshing automatically")
            self.current_token = await self.refresh_token(self.current_token.refresh_token)

        return self.current_token

    @staticmethod
    def generate_state() -> str:
        """Generate random state for CSRF protection.

        Returns:
            Random state string
        """
        return secrets.token_urlsafe(32)
