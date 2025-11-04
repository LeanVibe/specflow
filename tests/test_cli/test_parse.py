"""Tests for CLI parse command."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specflow.cli.main import app

runner = CliRunner()


@pytest.fixture
def sample_prd_file(tmp_path: Path) -> Path:
    """Create a sample PRD markdown file."""
    prd_content = """# Test PRD

## Overview
This is a test PRD for CLI parsing.

## Features

### Feature 1: User Authentication
Users need to log in with email and password.

- Requirement 1: Support email/password login
- Requirement 2: Show error messages for invalid credentials

### Feature 2: User Profile
Users need to manage their profiles.

- Requirement 1: Update profile information
- Requirement 2: Upload profile picture
"""
    prd_file = tmp_path / "test_prd.md"
    prd_file.write_text(prd_content)
    return prd_file


def test_parse_markdown_file_success(sample_prd_file: Path) -> None:
    """CLI successfully parses markdown PRD file."""
    result = runner.invoke(app, ["parse", str(sample_prd_file)])

    assert result.exit_code == 0
    assert "Test PRD" in result.output
    assert "Features" in result.output


def test_parse_file_not_found() -> None:
    """CLI handles missing file gracefully."""
    result = runner.invoke(app, ["parse", "/nonexistent/file.md"])

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "error" in result.output.lower()


def test_parse_with_output_option(sample_prd_file: Path, tmp_path: Path) -> None:
    """CLI can save parsed PRD to JSON file."""
    output_file = tmp_path / "output.json"
    result = runner.invoke(
        app,
        ["parse", str(sample_prd_file), "--output", str(output_file)],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    # Verify output is valid JSON
    with open(output_file) as f:
        data = json.load(f)
        assert "title" in data
        assert data["title"] == "Test PRD"


def test_parse_empty_file(tmp_path: Path) -> None:
    """CLI handles empty PRD file."""
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("")

    result = runner.invoke(app, ["parse", str(empty_file)])

    assert result.exit_code != 0


def test_parse_with_format_option_markdown(sample_prd_file: Path) -> None:
    """CLI respects format option for markdown."""
    result = runner.invoke(
        app,
        ["parse", str(sample_prd_file), "--format", "markdown"],
    )

    assert result.exit_code == 0


def test_parse_displays_features(sample_prd_file: Path) -> None:
    """CLI displays parsed features in output."""
    result = runner.invoke(app, ["parse", str(sample_prd_file)])

    assert result.exit_code == 0
    # Should show feature count in output
    assert "Features" in result.output or "1" in result.output
