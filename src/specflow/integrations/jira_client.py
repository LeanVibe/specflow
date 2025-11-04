"""Jira API client for creating and managing tickets."""

import asyncio
from typing import Any

import httpx

from specflow.integrations.exceptions import (
    JiraAPIError,
    ProjectNotFoundError,
    RateLimitError,
    TicketCreationError,
)
from specflow.integrations.oauth_handler import JiraOAuthHandler
from specflow.models import JiraTicket, TicketBatch, TicketDraft
from specflow.utils.logger import LoggerMixin


class JiraClient(LoggerMixin):
    """Client for Jira REST API v3.

    Handles ticket creation, project metadata fetching, and API communication
    with automatic retry logic and rate limit handling.
    """

    API_VERSION = "3"
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds

    def __init__(
        self,
        base_url: str,
        oauth_handler: JiraOAuthHandler,
        timeout: float = 30.0,
    ) -> None:
        """Initialize Jira API client.

        Args:
            base_url: Base URL of Jira instance (e.g., https://company.atlassian.net)
            oauth_handler: OAuth handler for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.oauth_handler = oauth_handler
        self.timeout = timeout

        self.logger.info(
            "Initialized Jira API client",
            extra={"base_url": self.base_url},
        )

    @property
    def api_base_url(self) -> str:
        """Get REST API base URL.

        Returns:
            Full API base URL with version
        """
        return f"{self.base_url}/rest/api/{self.API_VERSION}"

    async def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers with valid token.

        Returns:
            Dictionary with Authorization header

        Raises:
            JiraAuthError: If authentication fails
        """
        token = await self.oauth_handler.get_valid_token()
        return {
            "Authorization": f"Bearer {token.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request

        Returns:
            HTTP response

        Raises:
            RateLimitError: If rate limit is exceeded
            JiraAPIError: For other API errors
        """
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        headers = await self._get_auth_headers()

        # Merge custom headers if provided
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        retry_count = 0
        last_error: Exception | None = None

        while retry_count <= self.MAX_RETRIES:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        **kwargs,
                    )

                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", "60"))
                        self.logger.warning(
                            "Rate limit exceeded",
                            extra={"retry_after": retry_after},
                        )
                        raise RateLimitError(
                            f"Rate limit exceeded. Retry after {retry_after}s",
                            retry_after=retry_after,
                            status_code=429,
                        )

                    # Retry on server errors (5xx)
                    if response.status_code >= 500:
                        if retry_count < self.MAX_RETRIES:
                            delay = self.RETRY_DELAYS[retry_count]
                            self.logger.warning(
                                f"Server error {response.status_code}, retrying in {delay}s",
                                extra={
                                    "status_code": response.status_code,
                                    "retry": retry_count + 1,
                                },
                            )
                            await asyncio.sleep(delay)
                            retry_count += 1
                            continue
                        else:
                            raise JiraAPIError(
                                f"Request failed after {self.MAX_RETRIES} retries: "
                                f"HTTP {response.status_code}",
                                status_code=response.status_code,
                            )

                    return response

            except RateLimitError:
                raise
            except httpx.HTTPError as e:
                last_error = e
                if retry_count < self.MAX_RETRIES:
                    delay = self.RETRY_DELAYS[retry_count]
                    self.logger.warning(
                        f"Network error, retrying in {delay}s",
                        extra={"error": str(e), "retry": retry_count + 1},
                    )
                    await asyncio.sleep(delay)
                    retry_count += 1
                    continue
                else:
                    raise JiraAPIError(
                        f"Network error after {self.MAX_RETRIES} retries: {e}"
                    ) from e

        # Should not reach here, but handle edge case
        if last_error:
            raise JiraAPIError(f"Request failed: {last_error}") from last_error
        raise JiraAPIError("Request failed for unknown reason")

    async def get_project(self, project_key: str) -> dict[str, Any]:
        """Fetch project metadata from Jira.

        Args:
            project_key: Jira project key (e.g., 'PROJ')

        Returns:
            Project metadata dictionary

        Raises:
            ProjectNotFoundError: If project doesn't exist
            JiraAPIError: For other API errors
        """
        try:
            response = await self._make_request("GET", f"project/{project_key}")

            if response.status_code == 404:
                raise ProjectNotFoundError(
                    f"Project '{project_key}' not found",
                    status_code=404,
                )

            if response.status_code != 200:
                raise JiraAPIError(
                    f"Failed to fetch project: HTTP {response.status_code}",
                    status_code=response.status_code,
                )

            project = response.json()
            self.logger.info(
                "Fetched project metadata",
                extra={"project_key": project_key, "name": project.get("name")},
            )

            return project

        except (ProjectNotFoundError, RateLimitError):
            raise
        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to fetch project: {e}") from e

    async def get_issue_types(self, project_key: str) -> list[dict[str, Any]]:
        """Get available issue types for a project.

        Args:
            project_key: Jira project key

        Returns:
            List of issue type dictionaries

        Raises:
            JiraAPIError: If request fails
        """
        project = await self.get_project(project_key)
        issue_types = project.get("issueTypes", [])

        self.logger.debug(
            "Fetched issue types",
            extra={"project_key": project_key, "count": len(issue_types)},
        )

        return issue_types

    async def create_issue(
        self,
        project_key: str,
        ticket: TicketDraft,
    ) -> JiraTicket:
        """Create single Jira issue.

        Args:
            project_key: Jira project key
            ticket: Ticket draft to create

        Returns:
            Created Jira ticket

        Raises:
            TicketCreationError: If ticket creation fails
            RateLimitError: If rate limit exceeded
        """
        from specflow.integrations.ticket_converter import TicketConverter

        try:
            # Convert draft to Jira format
            issue_data = TicketConverter.draft_to_jira_format(ticket, project_key)

            self.logger.debug(
                "Creating Jira issue",
                extra={"project_key": project_key, "title": ticket.title},
            )

            # Create issue
            response = await self._make_request("POST", "issue", json=issue_data)

            if response.status_code not in (200, 201):
                error_data = response.json()
                error_msg = self._format_error_message(error_data)
                raise TicketCreationError(
                    f"Failed to create ticket in '{project_key}': {error_msg}",
                    status_code=response.status_code,
                )

            created = response.json()
            issue_key = created["key"]

            self.logger.info(
                "Created Jira issue",
                extra={"issue_key": issue_key, "project_key": project_key},
            )

            # Fetch full issue details
            issue_details = await self._get_issue_details(issue_key)

            # Convert to JiraTicket model
            jira_ticket = self._response_to_jira_ticket(
                issue_details, ticket.draft_id, project_key
            )

            return jira_ticket

        except (TicketCreationError, RateLimitError):
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error creating issue",
                extra={"error": str(e), "project_key": project_key},
            )
            raise TicketCreationError(f"Failed to create ticket: {e}") from e

    async def create_issues_bulk(
        self,
        project_key: str,
        tickets: list[TicketDraft],
    ) -> TicketBatch:
        """Bulk create Jira issues with error tracking.

        Args:
            project_key: Jira project key
            tickets: List of ticket drafts to create

        Returns:
            TicketBatch with results and failures
        """
        from uuid import uuid4

        batch = TicketBatch(
            prd_id=tickets[0].feature_id if tickets else uuid4(),
            project_key=project_key,
            drafts=tickets,
            status="in_progress",
        )

        self.logger.info(
            "Starting bulk ticket creation",
            extra={"project_key": project_key, "count": len(tickets)},
        )

        for ticket in tickets:
            try:
                jira_ticket = await self.create_issue(project_key, ticket)
                batch.created_tickets.append(jira_ticket)

            except Exception as e:
                error_msg = str(e)
                batch.failed_drafts.append((ticket.draft_id, error_msg))
                self.logger.error(
                    "Failed to create ticket in batch",
                    extra={
                        "draft_id": str(ticket.draft_id),
                        "title": ticket.title,
                        "error": error_msg,
                    },
                )

        batch.status = "completed"
        batch.completed_at = None  # Would set to datetime.utcnow() in real impl

        self.logger.info(
            "Completed bulk ticket creation",
            extra={
                "success": batch.success_count,
                "failed": batch.failed_count,
                "rate": f"{batch.success_rate:.1f}%",
            },
        )

        return batch

    async def _get_issue_details(self, issue_key: str) -> dict[str, Any]:
        """Fetch full issue details.

        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123')

        Returns:
            Full issue data dictionary
        """
        response = await self._make_request("GET", f"issue/{issue_key}")

        if response.status_code != 200:
            raise JiraAPIError(
                f"Failed to fetch issue details: HTTP {response.status_code}",
                status_code=response.status_code,
            )

        return response.json()

    def _response_to_jira_ticket(
        self,
        issue_data: dict[str, Any],
        draft_id: Any,
        project_key: str,
    ) -> JiraTicket:
        """Convert Jira API response to JiraTicket model.

        Args:
            issue_data: Issue data from Jira API
            draft_id: Source draft ID
            project_key: Project key

        Returns:
            JiraTicket model instance
        """
        fields = issue_data.get("fields", {})
        issue_key = issue_data.get("key", "UNKNOWN")
        ticket_id = issue_data.get("id", issue_key)  # Use key as fallback

        return JiraTicket(
            ticket_id=ticket_id,
            draft_id=draft_id,
            project_key=project_key,
            issue_key=issue_key,
            summary=fields.get("summary", ""),
            description_html=str(fields.get("description", "")),
            priority=fields.get("priority", {}).get("name", "Medium"),
            issue_type=fields.get("issuetype", {}).get("name", "Story"),
            status=fields.get("status", {}).get("name", "To Do"),
            assignee=fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
            reporter=fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
            labels=fields.get("labels", []),
            jira_url=f"{self.base_url}/browse/{issue_key}",
        )

    def _format_error_message(self, error_data: dict[str, Any]) -> str:
        """Format error message from Jira API response.

        Args:
            error_data: Error data from API

        Returns:
            Formatted error message
        """
        error_messages = error_data.get("errorMessages", [])
        errors = error_data.get("errors", {})

        parts = []
        if error_messages:
            parts.extend(error_messages)
        if errors:
            for field, msg in errors.items():
                parts.append(f"{field}: {msg}")

        return "; ".join(parts) if parts else "Unknown error"
