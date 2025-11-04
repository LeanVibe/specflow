"""Generate command for SpecFlow CLI."""

import json
from pathlib import Path

import typer

from specflow.cli.output import (
    display_error,
    display_info,
    display_success,
    display_warning,
)
from specflow.models import PRD, TicketDraft, TicketPriority, TicketType
from specflow.utils.logger import LoggerMixin


class GenerateCommand(LoggerMixin):
    """Generate Jira tickets from PRD."""

    def generate_tickets(
        self,
        prd_file: Path = typer.Argument(..., help="Path to parsed PRD JSON"),
        project_key: str = typer.Option(..., help="Jira project key"),
        dry_run: bool = typer.Option(False, help="Preview tickets without creating"),
    ) -> None:
        """Generate Jira tickets from PRD.

        Args:
            prd_file: Path to parsed PRD JSON file.
            project_key: Jira project key for ticket creation.
            dry_run: If True, preview tickets without creating them.
        """
        # Validate file exists
        if not prd_file.exists():
            display_error(f"File not found: {prd_file}")
            raise typer.Exit(1)

        # Load PRD from JSON
        try:
            content = prd_file.read_text()
            data = json.loads(content)
            prd = PRD.model_validate(data)
        except json.JSONDecodeError as e:
            display_error(f"Invalid JSON file: {e}")
            raise typer.Exit(1)
        except Exception as e:
            display_error(f"Failed to load PRD: {e}")
            raise typer.Exit(1)

        if not prd.features:
            display_warning("No features found in PRD")
            raise typer.Exit(0)

        # Convert features to ticket drafts
        try:
            drafts = []

            display_info(f"Converting {len(prd.features)} features to tickets...")

            for feature in prd.features:
                draft = TicketDraft(
                    feature_id=feature.feature_id,
                    title=feature.name,
                    description=feature.description,
                    acceptance_criteria=feature.acceptance_criteria,
                    ticket_type=TicketType.STORY,
                    priority=TicketPriority.MEDIUM,
                    labels=feature.tags,
                )
                drafts.append(draft)

            # Display preview
            display_info(f"\nPreview: {len(drafts)} tickets to create\n")
            for draft in drafts:
                display_success(f"[{draft.ticket_type.value}] {draft.title}")
                if draft.description:
                    description = (
                        draft.description[:80] + "..."
                        if len(draft.description) > 80
                        else draft.description
                    )
                    display_info(f"  Description: {description}")

            if dry_run:
                display_success("Dry-run complete. No tickets created.")
            else:
                display_warning("Ticket creation not yet implemented in CLI")
                display_info("Use REST API to create tickets in Jira")

        except Exception as e:
            display_error(f"Failed to generate tickets: {e}")
            self.logger.error(f"Generate error: {e}", exc_info=True)
            raise typer.Exit(1)

        display_success(f"Generated {len(drafts)} ticket preview(s)")


# Create command instance
_generate_cmd = GenerateCommand()


def generate(
    prd_file: Path = typer.Argument(..., help="Path to parsed PRD JSON"),
    project_key: str = typer.Option(..., help="Jira project key"),
    dry_run: bool = typer.Option(False, help="Preview tickets without creating"),
) -> None:
    """Generate Jira tickets from PRD."""
    _generate_cmd.generate_tickets(prd_file, project_key, dry_run)
