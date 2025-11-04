"""SpecFlow CLI main application."""

import typer
from rich.console import Console

from specflow.cli.commands.analyze import analyze
from specflow.cli.commands.auth import authenticate
from specflow.cli.commands.generate import generate
from specflow.cli.commands.parse import parse

# Initialize Typer app
app = typer.Typer(
    name="specflow",
    help="Transform PRDs into production-ready Jira tickets in 15 minutes",
    no_args_is_help=True,
)

# Initialize console
console = Console()

# Register commands
app.command(name="parse", help="Parse a PRD file into structured format")(parse)
app.command(name="analyze", help="Analyze PRD for quality and ambiguities")(analyze)
app.command(name="generate", help="Generate Jira tickets from PRD")(generate)
app.command(name="auth", help="Authenticate with external services")(authenticate)


@app.command(name="version", help="Show SpecFlow version")
def version() -> None:
    """Show SpecFlow version."""
    console.print("[cyan]SpecFlow[/cyan] [green]v0.1.0[/green]")


@app.command(name="help", help="Show help information")
def show_help() -> None:
    """Show detailed help information."""
    console.print(
        """
[bold cyan]SpecFlow CLI[/bold cyan]

Transform PRDs into production-ready Jira tickets in 15 minutes.

[bold]Commands:[/bold]

  [cyan]parse[/cyan]       Parse a PRD file into structured format
  [cyan]analyze[/cyan]     Analyze PRD for quality and ambiguities
  [cyan]generate[/cyan]    Generate Jira tickets from PRD
  [cyan]auth[/cyan]        Authenticate with external services
  [cyan]version[/cyan]     Show SpecFlow version

[bold]Usage Examples:[/bold]

  # Parse a markdown PRD file
  specflow parse path/to/prd.md

  # Parse and save as JSON
  specflow parse path/to/prd.md --output parsed.json

  # Analyze a PRD for quality
  specflow analyze parsed.json

  # Generate Jira tickets (dry-run)
  specflow generate parsed.json --project-key PROJ --dry-run

  # Authenticate with Jira
  specflow auth jira

[bold]Documentation:[/bold]

  For more information, visit: https://specflow.dev
"""
    )


if __name__ == "__main__":
    app()
