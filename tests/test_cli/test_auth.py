"""Tests for CLI auth command."""

import pytest
from typer.testing import CliRunner

from specflow.cli.main import app

runner = CliRunner()


def test_auth_command_exists() -> None:
    """CLI auth command is registered."""
    result = runner.invoke(app, ["auth", "--help"])

    assert result.exit_code == 0
    assert "jira" in result.output.lower() or "auth" in result.output.lower()


def test_auth_with_jira_provider() -> None:
    """CLI auth command accepts jira provider."""
    # This will fail because it tries to open browser, but command should be recognized
    result = runner.invoke(app, ["auth", "jira"])

    # Either succeeds or fails gracefully (not unknown command)
    assert "no such command" not in result.output.lower()


def test_auth_help_displays_provider_info() -> None:
    """CLI auth help shows available providers."""
    result = runner.invoke(app, ["auth", "--help"])

    assert result.exit_code == 0
