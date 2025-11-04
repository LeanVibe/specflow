"""Jira integration module for SpecFlow."""

from specflow.integrations.exceptions import (
    InvalidTokenError,
    JiraAPIError,
    JiraAuthError,
    JiraIntegrationError,
    ProjectNotFoundError,
    RateLimitError,
    TicketCreationError,
    TokenExpiredError,
)
from specflow.integrations.jira_client import JiraClient
from specflow.integrations.oauth_handler import JiraOAuthHandler
from specflow.integrations.oauth_models import OAuthState, OAuthToken
from specflow.integrations.ticket_converter import TicketConverter

__all__ = [
    # OAuth
    "JiraOAuthHandler",
    "OAuthToken",
    "OAuthState",
    # Jira Client
    "JiraClient",
    # Ticket Converter
    "TicketConverter",
    # Exceptions
    "JiraIntegrationError",
    "JiraAuthError",
    "JiraAPIError",
    "RateLimitError",
    "TokenExpiredError",
    "InvalidTokenError",
    "ProjectNotFoundError",
    "TicketCreationError",
]
