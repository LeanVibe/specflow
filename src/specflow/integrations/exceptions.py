"""Custom exceptions for Jira integration."""


class JiraIntegrationError(Exception):
    """Base exception for all Jira integration errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize Jira integration error.

        Args:
            message: Error message
            status_code: Optional HTTP status code
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class JiraAuthError(JiraIntegrationError):
    """Authentication or authorization error with Jira."""

    pass


class JiraAPIError(JiraIntegrationError):
    """Error communicating with Jira API."""

    pass


class RateLimitError(JiraIntegrationError):
    """Jira API rate limit exceeded."""

    def __init__(
        self, message: str, retry_after: int | None = None, status_code: int | None = None
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            status_code: Optional HTTP status code
        """
        super().__init__(message, status_code)
        self.retry_after = retry_after


class TokenExpiredError(JiraAuthError):
    """OAuth token has expired."""

    pass


class InvalidTokenError(JiraAuthError):
    """OAuth token is invalid or malformed."""

    pass


class ProjectNotFoundError(JiraAPIError):
    """Jira project not found."""

    pass


class TicketCreationError(JiraAPIError):
    """Failed to create Jira ticket."""

    pass
