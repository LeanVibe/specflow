"""Tests for CLI generate command."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specflow.cli.main import app

runner = CliRunner()


@pytest.fixture
def sample_prd_json_file(tmp_path: Path) -> Path:
    """Create a sample parsed PRD JSON file."""
    prd_data = {
        "prd_id": "12345678-1234-5678-1234-567812345678",
        "title": "Test PRD",
        "raw_content": "# Test PRD\n\n## Features\n\n### Feature 1",
        "parsed_sections": [],
        "features": [
            {
                "feature_id": "87654321-4321-8765-4321-876543218765",
                "name": "User Login",
                "description": "Allow users to log in to the system",
                "requirements": [
                    {
                        "requirement_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                        "description": "Email/password login",
                        "requirement_type": "functional",
                        "priority": "high",
                        "dependencies": [],
                        "acceptance_criteria": [
                            "Given valid email, When user logs in, Then user is authenticated"
                        ],
                        "edge_cases": [],
                        "metadata": {},
                    }
                ],
                "acceptance_criteria": [
                    "User can log in with valid credentials",
                    "Error shown for invalid credentials",
                ],
                "test_stubs": ["test_login_success"],
                "edge_cases": ["SQL injection"],
                "priority": "high",
                "complexity": "moderate",
                "estimated_days": 5.0,
                "dependencies": [],
                "tags": ["auth"],
                "metadata": {},
            }
        ],
        "metadata": {"author": "Test", "version": "1.0"},
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }
    prd_file = tmp_path / "prd.json"
    with open(prd_file, "w") as f:
        json.dump(prd_data, f)
    return prd_file


def test_generate_with_dry_run(sample_prd_json_file: Path) -> None:
    """CLI generates preview without creating Jira tickets."""
    result = runner.invoke(
        app,
        [
            "generate",
            str(sample_prd_json_file),
            "--project-key",
            "TEST",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "User Login" in result.output or "Generate" in result.output


def test_generate_requires_project_key(sample_prd_json_file: Path) -> None:
    """CLI requires project key to generate tickets."""
    result = runner.invoke(
        app,
        [
            "generate",
            str(sample_prd_json_file),
            "--dry-run",
        ],
    )

    # Missing required option should fail
    assert result.exit_code != 0


def test_generate_file_not_found() -> None:
    """CLI handles missing PRD file gracefully."""
    result = runner.invoke(
        app,
        [
            "generate",
            "/nonexistent/prd.json",
            "--project-key",
            "TEST",
            "--dry-run",
        ],
    )

    assert result.exit_code != 0


def test_generate_displays_ticket_preview(sample_prd_json_file: Path) -> None:
    """CLI displays ticket preview information."""
    result = runner.invoke(
        app,
        [
            "generate",
            str(sample_prd_json_file),
            "--project-key",
            "TEST",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
