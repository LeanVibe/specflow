"""OAuth models for Jira integration."""

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field, computed_field


class OAuthToken(BaseModel):
    """OAuth 2.0 token with metadata."""

    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str = Field(..., description="OAuth refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token lifetime in seconds", gt=0)
    scope: str = Field(..., description="Token scope")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Token creation time")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def expires_at(self) -> datetime:
        """Calculate token expiration timestamp.

        Returns:
            Datetime when token expires.
        """
        return self.created_at + timedelta(seconds=self.expires_in)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_expired(self) -> bool:
        """Check if token is expired.

        Returns:
            True if token is expired or expires in <60s (safety buffer).
        """
        now = datetime.utcnow()
        # Add 60s buffer for safety
        return now >= (self.expires_at - timedelta(seconds=60))

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override to exclude computed fields from serialization."""
        data = super().model_dump(**kwargs)
        # Remove computed fields if present
        data.pop("expires_at", None)
        data.pop("is_expired", None)
        return data


class OAuthState(BaseModel):
    """OAuth state parameter for CSRF protection."""

    state: str = Field(..., description="Random state value")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    redirect_path: str | None = Field(None, description="Path to redirect after OAuth")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_expired(self) -> bool:
        """Check if state is expired (>10 minutes old).

        Returns:
            True if state is too old.
        """
        now = datetime.utcnow()
        return now >= (self.created_at + timedelta(minutes=10))
