"""Analyze command for SpecFlow CLI."""

import json
from pathlib import Path

import typer

from specflow.cli.output import (
    display_ambiguity_issues,
    display_error,
    display_info,
    display_prd_summary,
    display_quality_scores,
    display_success,
    display_warning,
)
from specflow.intelligence.analyzer import AmbiguityAnalyzer
from specflow.intelligence.scorer import QualityScorer
from specflow.models import PRD
from specflow.parsers.markdown import MarkdownParser
from specflow.parsers.base import InvalidFormatError, ParseFailureError
from specflow.utils.logger import LoggerMixin


class AnalyzeCommand(LoggerMixin):
    """Analyze PRDs for quality and ambiguities."""

    def analyze_prd(
        self,
        prd_file: Path = typer.Argument(..., help="Path to PRD file or JSON"),
        show_ambiguities: bool = typer.Option(True, "--show-ambiguities/--no-ambiguities", help="Show ambiguity issues"),
        show_quality: bool = typer.Option(True, "--show-quality/--no-quality", help="Show quality scores"),
    ) -> None:
        """Analyze PRD for quality and ambiguities.

        Args:
            prd_file: Path to PRD file (markdown or JSON).
            show_ambiguities: Whether to show ambiguity analysis.
            show_quality: Whether to show quality scores.
        """
        # Validate file exists
        if not prd_file.exists():
            display_error(f"File not found: {prd_file}")
            raise typer.Exit(1)

        # Load PRD
        try:
            prd = self._load_prd(prd_file)
        except Exception as e:
            display_error(f"Failed to load PRD: {e}")
            self.logger.error(f"Load error: {e}", exc_info=True)
            raise typer.Exit(1)

        display_prd_summary(prd)

        # Run ambiguity analysis if requested
        if show_ambiguities:
            try:
                display_info("Analyzing ambiguities...")
                analyzer = AmbiguityAnalyzer()
                report = analyzer.detect_ambiguities(prd)
                issues = report.issues

                display_ambiguity_issues(issues)
                if issues:
                    display_warning(f"Found {len(issues)} ambiguity issue(s)")

            except Exception as e:
                display_warning(f"Ambiguity analysis failed: {e}")
                self.logger.error(f"Ambiguity analysis error: {e}", exc_info=True)

        # Run quality scoring if requested
        if show_quality:
            try:
                display_info("Calculating quality scores...")
                scorer = QualityScorer()
                scores = []
                for feature in prd.features:
                    score = scorer.score_readiness(feature, prd.prd_id)
                    scores.append(score)

                display_quality_scores(scores)
                ready_count = sum(1 for s in scores if s.is_ready)
                display_success(f"{ready_count}/{len(scores)} features ready for implementation")

            except Exception as e:
                display_warning(f"Quality scoring failed: {e}")
                self.logger.error(f"Quality scoring error: {e}", exc_info=True)

        display_success("Analysis complete")

    def _load_prd(self, prd_file: Path) -> PRD:
        """Load PRD from file.

        Args:
            prd_file: Path to PRD file (markdown or JSON).

        Returns:
            Loaded PRD model.

        Raises:
            ValueError: If file format is not supported.
        """
        content = prd_file.read_text()

        # Check if it's JSON
        if prd_file.suffix.lower() == ".json":
            try:
                data = json.loads(content)
                return PRD.model_validate(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")
            except Exception as e:
                raise ValueError(f"Invalid PRD JSON: {e}")

        # Try markdown
        if prd_file.suffix.lower() == ".md":
            parser = MarkdownParser()
            return parser.parse(content)

        # Try to auto-detect
        if content.strip().startswith("{"):
            try:
                data = json.loads(content)
                return PRD.model_validate(data)
            except json.JSONDecodeError:
                pass

        # Fall back to markdown
        parser = MarkdownParser()
        return parser.parse(content)


# Create command instance
_analyze_cmd = AnalyzeCommand()


def analyze(
    prd_file: Path = typer.Argument(..., help="Path to PRD file or JSON"),
    show_ambiguities: bool = typer.Option(True, "--show-ambiguities/--no-ambiguities", help="Show ambiguity issues"),
    show_quality: bool = typer.Option(True, "--show-quality/--no-quality", help="Show quality scores"),
) -> None:
    """Analyze PRD for quality and ambiguities."""
    _analyze_cmd.analyze_prd(prd_file, show_ambiguities, show_quality)
