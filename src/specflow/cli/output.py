"""Rich output formatting utilities for CLI."""


from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from specflow.models import PRD, AmbiguityIssue, QualityScore

console = Console()


def display_prd_summary(prd: PRD) -> None:
    """Display PRD summary in formatted table.

    Args:
        prd: PRD model to display summary for.
    """
    table = Table(title=f"PRD: {prd.title}", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Features", str(prd.feature_count))
    table.add_row("Requirements", str(prd.total_requirements))
    table.add_row("Completion %", f"{prd.completion_percentage:.1f}%")
    table.add_row("Created", prd.created_at.isoformat())

    console.print(table)


def display_features_summary(prd: PRD) -> None:
    """Display features in formatted table.

    Args:
        prd: PRD model containing features.
    """
    if not prd.features:
        console.print("[yellow]No features found in PRD[/yellow]")
        return

    table = Table(title="Features", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan")
    table.add_column("Requirements", style="green")
    table.add_column("Criteria", style="blue")
    table.add_column("Priority", style="magenta")

    for feature in prd.features:
        table.add_row(
            feature.name,
            str(feature.requirement_count),
            str(feature.acceptance_criteria_count),
            feature.priority.value,
        )

    console.print(table)


def display_ambiguity_issues(issues: list[AmbiguityIssue]) -> None:
    """Display ambiguity issues in formatted table.

    Args:
        issues: List of ambiguity issues.
    """
    if not issues:
        console.print("[green]✓ No ambiguity issues found![/green]")
        return

    table = Table(title="Ambiguity Issues", show_header=True, header_style="bold cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Severity", style="yellow")
    table.add_column("Issue", style="red")
    table.add_column("Suggestion", style="green")

    for issue in issues:
        # Color code severity
        severity_color = {
            "CRITICAL": "red",
            "HIGH": "yellow",
            "MEDIUM": "blue",
            "LOW": "cyan",
        }.get(issue.severity.value, "white")

        table.add_row(
            issue.issue_type.value,
            f"[{severity_color}]{issue.severity.value}[/{severity_color}]",
            issue.issue_description[:50] + "..." if len(issue.issue_description) > 50 else issue.issue_description,
            issue.suggestion[:50] + "..." if len(issue.suggestion) > 50 else issue.suggestion,
        )

    console.print(table)


def display_quality_scores(scores: list[QualityScore]) -> None:
    """Display quality scores in formatted table.

    Args:
        scores: List of quality scores.
    """
    if not scores:
        console.print("[yellow]No quality scores available[/yellow]")
        return

    table = Table(title="Quality Scores", show_header=True, header_style="bold cyan")
    table.add_column("Feature", style="cyan")
    table.add_column("Overall Score", style="green")
    table.add_column("Grade", style="blue")
    table.add_column("Status", style="magenta")

    for score in scores:
        # Color code score
        score_value = score.overall_score
        if score_value >= 80:
            score_color = "green"
        elif score_value >= 70:
            score_color = "yellow"
        else:
            score_color = "red"

        status = "[green]✓ Ready[/green]" if score.is_ready else "[red]✗ Not Ready[/red]"

        table.add_row(
            score.feature_id.hex[:8],
            f"[{score_color}]{score_value}/100[/{score_color}]",
            score.overall_grade,
            status,
        )

    console.print(table)


def display_progress(description: str, total: int) -> Progress:
    """Create a progress bar for operations.

    Args:
        description: Description for progress bar.
        total: Total number of items.

    Returns:
        Progress object for iteration.
    """
    return Progress(description=description, total=total)


def display_success(message: str) -> None:
    """Display success message.

    Args:
        message: Success message to display.
    """
    console.print(f"[green]✓ {message}[/green]")


def display_error(message: str) -> None:
    """Display error message.

    Args:
        message: Error message to display.
    """
    console.print(f"[red]✗ {message}[/red]")


def display_info(message: str) -> None:
    """Display info message.

    Args:
        message: Info message to display.
    """
    console.print(f"[blue]ℹ {message}[/blue]")


def display_warning(message: str) -> None:
    """Display warning message.

    Args:
        message: Warning message to display.
    """
    console.print(f"[yellow]⚠ {message}[/yellow]")
