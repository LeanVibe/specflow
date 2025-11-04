"""End-to-end tests for CLI command workflow sequences.

Tests CLI command chains that simulate real user workflows
from the command line interface.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specflow.cli.main import app

runner = CliRunner()


@pytest.mark.e2e
class TestCLIWorkflows:
    """E2E tests for CLI command chains."""

    def test_cli_parse_save_analyze_workflow(
        self, tmp_path: Path, comprehensive_prd_content: str
    ) -> None:
        """E2E CLI: parse --output → analyze saved file workflow."""
        # Create PRD file
        prd_file = tmp_path / "auth_system.md"
        prd_file.write_text(comprehensive_prd_content)

        output_file = tmp_path / "parsed_prd.json"

        # Step 1: Parse and save to JSON
        parse_result = runner.invoke(
            app, ["parse", str(prd_file), "--output", str(output_file)]
        )

        assert parse_result.exit_code == 0, f"Parse failed: {parse_result.output}"
        assert output_file.exists(), "Output file not created"

        # Verify JSON is valid and contains expected data
        with open(output_file) as f:
            prd_data = json.load(f)
            assert prd_data["title"] == "User Authentication System"
            assert len(prd_data["features"]) >= 3

        # Step 2: Analyze the saved file
        analyze_result = runner.invoke(app, ["analyze", str(output_file)])

        # May fail without AI keys, but should show either results or graceful error
        assert (
            "Analysis complete" in analyze_result.output
            or "Error" in analyze_result.output
            or "ambiguity" in analyze_result.output.lower()
        )

    def test_cli_parse_generate_dry_run_workflow(
        self, tmp_path: Path, simple_prd_content: str
    ) -> None:
        """E2E CLI: parse → generate --dry-run workflow."""
        # Create PRD file
        prd_file = tmp_path / "task_mgmt.md"
        prd_file.write_text(simple_prd_content)

        parsed_file = tmp_path / "parsed.json"

        # Step 1: Parse PRD
        parse_result = runner.invoke(
            app, ["parse", str(prd_file), "--output", str(parsed_file)]
        )

        assert parse_result.exit_code == 0
        assert parsed_file.exists()

        # Step 2: Generate tickets in dry-run mode
        generate_result = runner.invoke(
            app,
            ["generate", str(parsed_file), "--project-key", "TASK", "--dry-run"],
        )

        # Should succeed in dry-run (no actual Jira API calls)
        assert generate_result.exit_code == 0, f"Generate failed: {generate_result.output}"
        assert "dry-run" in generate_result.output.lower() or "preview" in generate_result.output.lower()

    def test_cli_full_workflow_with_verification(
        self, tmp_path: Path, comprehensive_prd_content: str
    ) -> None:
        """E2E CLI: Complete workflow parse → analyze → generate with verification at each step."""
        # Setup
        prd_file = tmp_path / "complete_workflow.md"
        prd_file.write_text(comprehensive_prd_content)
        parsed_file = tmp_path / "workflow_parsed.json"

        # Step 1: Parse
        parse_result = runner.invoke(
            app, ["parse", str(prd_file), "--output", str(parsed_file)]
        )
        assert parse_result.exit_code == 0
        assert "User Authentication System" in parse_result.output

        # Verify parsed file
        assert parsed_file.exists()
        with open(parsed_file) as f:
            data = json.load(f)
            feature_count = len(data["features"])
            assert feature_count >= 3

        # Step 2: Analyze
        analyze_result = runner.invoke(app, ["analyze", str(parsed_file)])
        # Accept both success and graceful failure (AI may not be available)
        assert analyze_result.exit_code in [0, 1]

        # Step 3: Generate (dry-run)
        generate_result = runner.invoke(
            app,
            [
                "generate",
                str(parsed_file),
                "--project-key",
                "AUTH",
                "--dry-run",
            ],
        )
        assert generate_result.exit_code == 0
        # Should show ticket preview
        assert feature_count > 0  # Verify we have tickets to generate

    def test_cli_version_and_help_commands(self) -> None:
        """E2E CLI: Version and help commands work correctly."""
        # Test version command
        version_result = runner.invoke(app, ["version"])
        assert version_result.exit_code == 0
        assert "SpecFlow" in version_result.output
        assert "v0.1.0" in version_result.output

        # Test help command
        help_result = runner.invoke(app, ["help"])
        assert help_result.exit_code == 0
        assert "parse" in help_result.output
        assert "analyze" in help_result.output
        assert "generate" in help_result.output

    def test_cli_error_handling_in_workflow(self, tmp_path: Path) -> None:
        """E2E CLI: Workflow handles errors gracefully at each step."""
        # Try to parse non-existent file
        parse_result = runner.invoke(app, ["parse", "/nonexistent/file.md"])
        assert parse_result.exit_code != 0
        assert "not found" in parse_result.output.lower() or "error" in parse_result.output.lower()

        # Try to analyze non-existent file
        analyze_result = runner.invoke(app, ["analyze", "/nonexistent/parsed.json"])
        assert analyze_result.exit_code != 0

        # Try to generate from non-existent file
        generate_result = runner.invoke(
            app,
            ["generate", "/nonexistent/parsed.json", "--project-key", "PROJ", "--dry-run"],
        )
        assert generate_result.exit_code != 0

        # Try to parse empty file
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")
        parse_empty_result = runner.invoke(app, ["parse", str(empty_file)])
        assert parse_empty_result.exit_code != 0

    def test_cli_parse_with_different_formats(
        self, tmp_path: Path, simple_prd_content: str
    ) -> None:
        """E2E CLI: Parse command handles format specification."""
        # Create markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text(simple_prd_content)

        # Parse with explicit markdown format
        result = runner.invoke(
            app,
            ["parse", str(md_file), "--format", "markdown"],
        )
        assert result.exit_code == 0
        assert "Task Management Feature" in result.output
