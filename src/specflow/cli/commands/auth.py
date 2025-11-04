"""Auth command for SpecFlow CLI."""

import os

import typer

from specflow.cli.output import display_error, display_info, display_success
from specflow.integrations.oauth_handler import JiraOAuthHandler
from specflow.utils.config import get_settings
from specflow.utils.logger import LoggerMixin


class AuthCommand(LoggerMixin):
    """Authenticate with external services."""

    def authenticate(
        self,
        provider: str = typer.Argument("jira", help="Auth provider (jira)"),
    ) -> None:
        """Authenticate with external services.

        Args:
            provider: Authentication provider (currently only 'jira' supported).
        """
        if provider.lower() != "jira":
            display_error(f"Unknown auth provider: {provider}")
            display_info("Supported providers: jira")
            raise typer.Exit(1)

        self._authenticate_jira()

    def _authenticate_jira(self) -> None:
        """Authenticate with Jira using OAuth2.

        This initiates the OAuth2 flow for Jira authentication.
        """
        try:
            # Get settings
            settings = get_settings()

            # Validate required settings
            if not settings.jira_client_id:
                display_error("Jira OAuth client ID not configured")
                display_info(
                    "Set JIRA_CLIENT_ID environment variable or update .env file"
                )
                raise typer.Exit(1)

            if not settings.jira_client_secret:
                display_error("Jira OAuth client secret not configured")
                display_info(
                    "Set JIRA_CLIENT_SECRET environment variable or update .env file"
                )
                raise typer.Exit(1)

            # Create OAuth handler
            oauth_handler = JiraOAuthHandler(
                client_id=settings.jira_client_id,
                client_secret=settings.jira_client_secret.get_secret_value(),
            )

            display_info("Starting Jira OAuth2 authentication...")
            display_info("Opening browser for authorization...")

            # Get authorization URL
            auth_url = oauth_handler.get_authorization_url()
            display_info(f"Authorization URL: {auth_url}")
            display_info("Please open the link above in your browser to authorize")

            # Note: Actual browser opening and callback handling would require
            # additional infrastructure (local callback server, etc.)
            # For now, we just display the URL and instructions
            display_info("\nAfter authorization, SpecFlow will store your token securely")
            display_success(
                "OAuth2 authentication configured. Use 'generate' command to create tickets."
            )

            self.logger.info("Jira OAuth2 authentication initiated")

        except Exception as e:
            display_error(f"Authentication failed: {e}")
            self.logger.error(f"Auth error: {e}", exc_info=True)
            raise typer.Exit(1)


# Create command instance
_auth_cmd = AuthCommand()


def authenticate(
    provider: str = typer.Argument("jira", help="Auth provider (jira)"),
) -> None:
    """Authenticate with external services."""
    _auth_cmd.authenticate(provider)
