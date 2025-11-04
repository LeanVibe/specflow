"""Tests for CLI analyze command."""

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
This is a very fast and easy system that should work nicely.

## Features

### Feature 1: User Authentication
Users need to easily log in to the system quickly.

- Requirement 1: Support email/password login
"""
    prd_file = tmp_path / "test_prd.md"
    prd_file.write_text(prd_content)
    return prd_file


@pytest.fixture
def sample_prd_json_file(tmp_path: Path) -> Path:
    """Create a sample parsed PRD JSON file."""
    prd_data = {
        "prd_id": "12345678-1234-5678-1234-567812345678",
        "title": "Test PRD",
        "raw_content": "# Test PRD\n\nQuick feature...",
        "parsed_sections": [],
        "features": [
            {
                "feature_id": "87654321-4321-8765-4321-876543218765",
                "name": "Auth Feature",
                "description": "User authentication system",
                "requirements": [],
                "acceptance_criteria": [],
                "test_stubs": [],
                "edge_cases": [],
                "priority": "high",
                "complexity": "moderate",
                "tags": [],
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


def test_analyze_prd_file_success(sample_prd_file: Path) -> None:
    """CLI successfully analyzes PRD file."""
    result = runner.invoke(app, ["analyze", str(sample_prd_file)])

    assert result.exit_code == 0
    assert "Test PRD" in result.output or "Ambiguity" in result.output


def test_analyze_json_prd_file(sample_prd_json_file: Path) -> None:
    """CLI can analyze parsed PRD JSON file."""
    result = runner.invoke(app, ["analyze", str(sample_prd_json_file)])

    assert result.exit_code == 0


def test_analyze_file_not_found() -> None:
    """CLI handles missing file gracefully."""
    result = runner.invoke(app, ["analyze", "/nonexistent/file.md"])

    assert result.exit_code != 0


def test_analyze_with_ambiguity_flag(sample_prd_file: Path) -> None:
    """CLI can filter analysis by ambiguity option."""
    result = runner.invoke(
        app,
        ["analyze", str(sample_prd_file), "--show-ambiguities"],
    )

    assert result.exit_code == 0


def test_analyze_with_quality_flag(sample_prd_file: Path) -> None:
    """CLI can filter analysis by quality option."""
    result = runner.invoke(
        app,
        ["analyze", str(sample_prd_file), "--show-quality"],
    )

    assert result.exit_code == 0
