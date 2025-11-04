"""OAuth-related API routes."""


from fastapi import APIRouter, HTTPException

from specflow.api.schemas import OAuthStatusResponse

router = APIRouter()


@router.get("/jira/authorize")
async def jira_authorize() -> dict[str, str]:
    """Redirect to Jira OAuth authorization.

    Returns:
        Authorization URL and state.

    Raises:
        HTTPException: If OAuth not configured.
    """
    raise HTTPException(
        status_code=501,
        detail="OAuth authorization not yet implemented. Configure Jira OAuth credentials first.",
    )


@router.get("/jira/callback")
async def jira_callback(code: str, state: str) -> dict[str, str]:
    """Handle OAuth callback from Jira.

    Args:
        code: Authorization code.
        state: State parameter for CSRF protection.

    Returns:
        Success message.

    Raises:
        HTTPException: If OAuth exchange fails.
    """
    raise HTTPException(
        status_code=501,
        detail="OAuth callback not yet implemented.",
    )


@router.get("/jira/status", response_model=OAuthStatusResponse)
async def jira_status() -> OAuthStatusResponse:
    """Check Jira OAuth connection status.

    Returns:
        OAuth connection status.
    """
    # Placeholder - would check actual token in production
    return OAuthStatusResponse(
        is_connected=False,
        platform="jira",
        expires_at=None,
        scopes=[],
        user_info=None,
    )
