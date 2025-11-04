"""Configuration management using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"
    secret_key: SecretStr = Field(default="dev-secret-key-change-in-production")

    # API Server
    host: str = "0.0.0.0"
    port: int = 8000

    # AI Provider
    ai_provider: Literal["openai", "anthropic", "gemini"] = "openai"
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None

    # Jira Integration
    jira_client_id: str | None = None
    jira_client_secret: SecretStr | None = None
    jira_redirect_uri: str = "http://localhost:8000/api/integrations/jira/callback"
    jira_scopes: str = "read:jira-work write:jira-work offline_access"

    # Linear Integration
    linear_api_key: SecretStr | None = None

    # Asana Integration
    asana_client_id: str | None = None
    asana_client_secret: SecretStr | None = None

    # Notion Integration
    notion_api_key: SecretStr | None = None

    # Google Docs Integration
    google_docs_credentials_file: str = "credentials.json"
    google_docs_token_file: str = "token.json"

    # Database
    database_url: str = "sqlite:///./specflow.db"

    # Security
    session_secret: SecretStr = Field(default="dev-session-secret-change-in-production")
    token_encryption_key: SecretStr | None = None

    # Feature Flags
    enable_notion_parser: bool = True
    enable_gdocs_parser: bool = True
    enable_linear_integration: bool = False
    enable_asana_integration: bool = False

    # Rate Limiting
    rate_limit_per_minute: int = 60
    jira_api_rate_limit: int = 100

    # Monitoring (Optional)
    sentry_dsn: str | None = None
    posthog_api_key: str | None = None

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.env == "production"

    def get_ai_api_key(self) -> SecretStr:
        """Get the API key for the configured AI provider."""
        if self.ai_provider == "openai" and self.openai_api_key:
            return self.openai_api_key
        if self.ai_provider == "anthropic" and self.anthropic_api_key:
            return self.anthropic_api_key
        if self.ai_provider == "gemini" and self.gemini_api_key:
            return self.gemini_api_key
        raise ValueError(f"No API key configured for provider: {self.ai_provider}")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Singleton Settings instance loaded from environment.
    """
    return Settings()
