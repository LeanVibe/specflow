"""Base parser protocol for PRD document parsing.

All PRD parsers (Markdown, Notion, Google Docs) must implement this protocol.
"""

from typing import Protocol, runtime_checkable

from specflow.models import PRD


@runtime_checkable
class BasePRDParser(Protocol):
    """Protocol defining the interface for all PRD parsers.

    Parsers extract structured data from various document formats and
    convert them into our internal PRD model.
    """

    def parse(self, content: str | dict) -> PRD:
        """Parse document content into a structured PRD.

        Args:
            content: Raw content to parse. Can be:
                - str: For markdown/text formats
                - dict: For API responses (Notion, Google Docs)

        Returns:
            Structured PRD model with features and requirements.

        Raises:
            ValueError: If content is invalid or cannot be parsed.
        """
        ...

    def validate_format(self, content: str | dict) -> bool:
        """Validate if content matches expected format.

        Args:
            content: Content to validate.

        Returns:
            True if content can be parsed by this parser.
        """
        ...


class ParserError(Exception):
    """Base exception for parser errors."""

    pass


class InvalidFormatError(ParserError):
    """Raised when content format is invalid."""

    pass


class ParseFailureError(ParserError):
    """Raised when parsing fails unexpectedly."""

    pass
