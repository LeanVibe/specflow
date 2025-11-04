"""Parse command for SpecFlow CLI."""

import json
from pathlib import Path
from typing import Optional

import typer

from specflow.cli.output import display_error, display_features_summary, display_info, display_prd_summary, display_success
from specflow.parsers.markdown import MarkdownParser
from specflow.parsers.base import InvalidFormatError, ParseFailureError
from specflow.utils.logger import LoggerMixin


class ParseCommand(LoggerMixin):
    """Parse PRD files into structured format."""

    def parse_prd(
        self,
        file_path: Path = typer.Argument(..., help="Path to PRD file"),
        format: str = typer.Option("markdown", help="PRD format (markdown)"),
        output: Optional[Path] = typer.Option(None, help="Save parsed PRD to JSON"),
    ) -> None:
        """Parse a PRD file into structured format.

        Args:
            file_path: Path to PRD file to parse.
            format: Format of the PRD file (markdown).
            output: Optional path to save parsed PRD as JSON.
        """
        # Validate file exists
        if not file_path.exists():
            display_error(f"File not found: {file_path}")
            raise typer.Exit(1)

        # Read file content
        try:
            content = file_path.read_text()
        except Exception as e:
            display_error(f"Failed to read file: {e}")
            raise typer.Exit(1)

        # Validate content is not empty
        if not content or not content.strip():
            display_error("PRD file is empty")
            raise typer.Exit(1)

        # Parse based on format
        try:
            if format.lower() == "markdown":
                parser = MarkdownParser()
                prd = parser.parse(content)
            else:
                display_error(f"Unsupported format: {format}")
                raise typer.Exit(1)

            # Display parsed PRD
            display_prd_summary(prd)
            display_features_summary(prd)

            # Save to JSON if requested
            if output:
                try:
                    output_data = prd.model_dump_json()
                    output.write_text(output_data)
                    display_success(f"Parsed PRD saved to {output}")
                except Exception as e:
                    display_error(f"Failed to save output: {e}")
                    raise typer.Exit(1)

            display_success(f"Successfully parsed {prd.feature_count} features")

        except InvalidFormatError as e:
            display_error(f"Invalid format: {e}")
            raise typer.Exit(1)
        except ParseFailureError as e:
            display_error(f"Parse failed: {e}")
            raise typer.Exit(1)
        except Exception as e:
            display_error(f"Unexpected error: {e}")
            self.logger.error(f"Parse error: {e}", exc_info=True)
            raise typer.Exit(1)


# Create command instance
_parse_cmd = ParseCommand()


def parse(
    file_path: Path = typer.Argument(..., help="Path to PRD file"),
    format: str = typer.Option("markdown", help="PRD format (markdown)"),
    output: Optional[Path] = typer.Option(None, help="Save parsed PRD to JSON"),
) -> None:
    """Parse a PRD file into structured format."""
    _parse_cmd.parse_prd(file_path, format, output)
