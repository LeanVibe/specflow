"""Markdown PRD parser implementation.

Parses Markdown documents into structured PRD models by extracting:
- Title from H1 headers
- Sections from H2 headers
- Features from H3 headers
- Requirements from bullet/numbered lists
- Acceptance criteria and edge cases from labeled sections
"""

import re

from specflow.models import (
    PRD,
    Feature,
    PRDMetadata,
    PRDSection,
    Requirement,
    RequirementType,
)
from specflow.parsers.base import InvalidFormatError, ParseFailureError
from specflow.utils.logger import LoggerMixin


class MarkdownParser(LoggerMixin):
    """Parser for Markdown-formatted PRD documents."""

    def parse(self, content: str | dict) -> PRD:
        """Parse markdown content into structured PRD.

        Args:
            content: Markdown string to parse.

        Returns:
            Structured PRD model.

        Raises:
            InvalidFormatError: If content is not valid markdown or missing required elements.
            ParseFailureError: If parsing fails unexpectedly.
        """
        if not self.validate_format(content):
            raise InvalidFormatError("Content must be a non-empty markdown string")

        if not isinstance(content, str):
            raise InvalidFormatError("Markdown parser expects string content")

        try:
            # Extract title (first H1)
            title = self._extract_title(content)
            if not title:
                raise InvalidFormatError("PRD must have a title (H1 header)")

            # Parse document structure
            sections = self._parse_sections(content)

            # Extract features from content
            features = self._extract_features(content)

            # Build PRD model
            prd = PRD(
                title=title,
                raw_content=content,
                parsed_sections=sections,
                features=features,
                metadata=PRDMetadata(
                    source_format="markdown",
                    version="1.0",
                ),
            )

            self.log_info(
                f"Parsed markdown PRD: {title}",
                features=len(features),
                sections=len(sections),
            )

            return prd

        except (InvalidFormatError, ParseFailureError):
            raise
        except Exception as e:
            self.log_error(f"Unexpected error parsing markdown: {e}", exc_info=True)
            raise ParseFailureError(f"Failed to parse markdown: {e}") from e

    def validate_format(self, content: str | dict) -> bool:
        """Validate if content is valid markdown.

        Args:
            content: Content to validate.

        Returns:
            True if content is a non-empty string.
        """
        return isinstance(content, str) and len(content.strip()) > 0

    def _extract_title(self, content: str) -> str:
        """Extract title from first H1 header.

        Args:
            content: Markdown content.

        Returns:
            Title text without the # symbol.
        """
        # Match first H1: # Title
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_sections(self, content: str) -> list[PRDSection]:
        """Parse document into hierarchical sections.

        Args:
            content: Markdown content.

        Returns:
            List of PRDSection objects with hierarchy.
        """
        sections: list[PRDSection] = []

        # Find all H2 sections (## Header)
        h2_pattern = r"^##\s+(.+)$"
        h2_matches = list(re.finditer(h2_pattern, content, re.MULTILINE))

        for i, match in enumerate(h2_matches):
            title = match.group(1).strip()
            start = match.end()

            # Content until next H2 or end of document
            if i + 1 < len(h2_matches):
                end = h2_matches[i + 1].start()
            else:
                end = len(content)

            section_content = content[start:end].strip()

            sections.append(
                PRDSection(
                    title=title,
                    content=section_content,
                    order=i,
                )
            )

        return sections

    def _extract_features(self, content: str) -> list[Feature]:
        """Extract features from markdown content.

        Features are identified as H3 headers (###) under a Features section,
        or any H3 that looks like a feature description.

        Args:
            content: Markdown content.

        Returns:
            List of Feature objects.
        """
        features: list[Feature] = []

        # Find all H3 headers (### Feature)
        h3_pattern = r"^###\s+(.+)$"
        h3_matches = list(re.finditer(h3_pattern, content, re.MULTILINE))

        for i, match in enumerate(h3_matches):
            feature_title = match.group(1).strip()

            # Get content until next H3 or H2
            start = match.end()
            end = len(content)

            # Find next H2 or H3
            next_header = re.search(r"^##", content[start:], re.MULTILINE)
            if next_header:
                end = start + next_header.start()
            else:
                # Look for next H3
                if i + 1 < len(h3_matches):
                    end = h3_matches[i + 1].start()

            feature_content = content[start:end].strip()

            # Extract feature description (first paragraph)
            description = self._extract_description(feature_content)

            # Extract requirements
            requirements = self._extract_requirements(feature_content)

            # Extract acceptance criteria
            acceptance_criteria = self._extract_acceptance_criteria(feature_content)

            # Extract edge cases
            edge_cases = self._extract_edge_cases(feature_content)

            feature = Feature(
                name=feature_title,
                description=description or "No description provided",
                requirements=requirements,
                acceptance_criteria=acceptance_criteria,
                edge_cases=edge_cases,
            )

            features.append(feature)

        return features

    def _extract_description(self, content: str) -> str:
        """Extract feature description (first paragraph before any headers).

        Args:
            content: Feature content.

        Returns:
            Description text.
        """
        # Get text before first **Requirements** or **Acceptance Criteria**
        match = re.search(
            r"^(.*?)\*\*(?:Requirements|Acceptance Criteria|Edge Cases):",
            content,
            re.DOTALL | re.MULTILINE,
        )

        if match:
            return match.group(1).strip()

        # If no labeled sections, take first paragraph
        paragraphs = content.split("\n\n")
        return paragraphs[0].strip() if paragraphs else ""

    def _extract_requirements(self, content: str) -> list[Requirement]:
        """Extract requirements from **Requirements:** section.

        Args:
            content: Feature content.

        Returns:
            List of Requirement objects.
        """
        requirements: list[Requirement] = []

        # Find **Requirements:** section
        req_pattern = r"\*\*Requirements:\*\*\s*\n((?:[-*\d.].*\n?)+)"
        match = re.search(req_pattern, content, re.MULTILINE)

        if not match:
            return requirements

        req_text = match.group(1)

        # Extract bullet points or numbered items
        # Match: - Item, * Item, 1. Item, 1) Item
        items = re.findall(r"^[-*\d.)\s]+(.+)$", req_text, re.MULTILINE)

        for item in items:
            if item.strip():
                requirements.append(
                    Requirement(
                        description=item.strip(),
                        requirement_type=RequirementType.FUNCTIONAL,
                    )
                )

        return requirements

    def _extract_acceptance_criteria(self, content: str) -> list[str]:
        """Extract acceptance criteria from **Acceptance Criteria:** section.

        Args:
            content: Feature content.

        Returns:
            List of acceptance criteria strings.
        """
        # Find **Acceptance Criteria:** section
        ac_pattern = r"\*\*Acceptance Criteria:\*\*\s*\n((?:[-*\d.].*\n?)+)"
        match = re.search(ac_pattern, content, re.MULTILINE)

        if not match:
            return []

        ac_text = match.group(1)

        # Extract bullet points
        items = re.findall(r"^[-*\d.)\s]+(.+)$", ac_text, re.MULTILINE)

        return [item.strip() for item in items if item.strip()]

    def _extract_edge_cases(self, content: str) -> list[str]:
        """Extract edge cases from **Edge Cases:** section.

        Args:
            content: Feature content.

        Returns:
            List of edge case strings.
        """
        # Find **Edge Cases:** section
        ec_pattern = r"\*\*Edge Cases:\*\*\s*\n((?:[-*\d.].*\n?)+)"
        match = re.search(ec_pattern, content, re.MULTILINE)

        if not match:
            return []

        ec_text = match.group(1)

        # Extract bullet points
        items = re.findall(r"^[-*\d.)\s]+(.+)$", ec_text, re.MULTILINE)

        return [item.strip() for item in items if item.strip()]
