"""Tests for Markdown PRD parser."""

import pytest

from specflow.parsers.base import InvalidFormatError
from specflow.parsers.markdown import MarkdownParser


class TestMarkdownParser:
    """Test suite for Markdown parser."""

    def test_parse_simple_prd(self) -> None:
        """Parser handles simple PRD with title and features."""
        content = """# Authentication System

## Overview
Secure user authentication for the platform.

## Features

### Feature 1: User Login
Allow users to log in with email and password.

**Requirements:**
- User can enter email and password
- System validates credentials
- User is redirected to dashboard on success

**Acceptance Criteria:**
- Given valid credentials, user is authenticated
- Given invalid credentials, error message is displayed
"""

        parser = MarkdownParser()
        prd = parser.parse(content)

        assert prd.title == "Authentication System"
        assert len(prd.parsed_sections) >= 2  # Overview + Features
        assert len(prd.features) == 1

        feature = prd.features[0]
        assert "User Login" in feature.name
        assert "email and password" in feature.description
        assert len(feature.requirements) == 3
        assert len(feature.acceptance_criteria) == 2

    def test_parse_multiple_features(self) -> None:
        """Parser extracts multiple features correctly."""
        content = """# Product Dashboard

## Features

### Feature 1: Analytics View
View key metrics.

**Requirements:**
- Display charts
- Show KPIs

### Feature 2: Export Data
Export data to CSV.

**Requirements:**
- Generate CSV file
- Download to local machine
"""

        parser = MarkdownParser()
        prd = parser.parse(content)

        assert len(prd.features) == 2
        assert "Analytics View" in prd.features[0].name
        assert "Export Data" in prd.features[1].name

    def test_parse_nested_sections(self) -> None:
        """Parser handles nested section hierarchy."""
        content = """# Project Title

## Section 1
Content 1

### Subsection 1.1
Nested content

## Section 2
Content 2
"""

        parser = MarkdownParser()
        prd = parser.parse(content)

        assert prd.title == "Project Title"
        assert len(prd.parsed_sections) >= 2

    def test_parse_requirements_from_bullets(self) -> None:
        """Parser extracts requirements from bullet points."""
        content = """# Test PRD

## Features

### Feature: User Profile

**Requirements:**
- Requirement 1
- Requirement 2
- Requirement 3
"""

        parser = MarkdownParser()
        prd = parser.parse(content)

        feature = prd.features[0]
        assert len(feature.requirements) == 3
        assert feature.requirements[0].description == "Requirement 1"

    def test_parse_requirements_from_numbered_list(self) -> None:
        """Parser extracts requirements from numbered lists."""
        content = """# Test PRD

## Features

### Feature: API Integration

**Requirements:**
1. Connect to external API
2. Handle authentication
3. Parse response data
"""

        parser = MarkdownParser()
        prd = parser.parse(content)

        feature = prd.features[0]
        assert len(feature.requirements) == 3
        assert "Connect to external API" in feature.requirements[0].description

    def test_parse_acceptance_criteria(self) -> None:
        """Parser extracts acceptance criteria separately."""
        content = """# Test PRD

## Features

### Feature: Login

**Acceptance Criteria:**
- Given valid email, user can login
- Given invalid email, error is shown
"""

        parser = MarkdownParser()
        prd = parser.parse(content)

        feature = prd.features[0]
        assert len(feature.acceptance_criteria) == 2
        assert "valid email" in feature.acceptance_criteria[0]

    def test_parse_prd_without_features_section(self) -> None:
        """Parser handles PRD without explicit Features section."""
        content = """# Simple PRD

## Overview
Just an overview, no features yet.
"""

        parser = MarkdownParser()
        prd = parser.parse(content)

        assert prd.title == "Simple PRD"
        assert len(prd.features) == 0
        assert len(prd.parsed_sections) >= 1

    def test_parse_empty_content_raises_error(self) -> None:
        """Parser raises error for empty content."""
        parser = MarkdownParser()

        with pytest.raises(InvalidFormatError):
            parser.parse("")

    def test_parse_no_title_raises_error(self) -> None:
        """Parser raises error when no H1 title found."""
        content = "## Section\nNo title here"

        parser = MarkdownParser()

        with pytest.raises(InvalidFormatError):
            parser.parse(content)

    def test_validate_format_valid_markdown(self) -> None:
        """Validator accepts valid markdown."""
        content = "# Title\n\n## Section\n\nContent"
        parser = MarkdownParser()

        assert parser.validate_format(content) is True

    def test_validate_format_invalid_content(self) -> None:
        """Validator rejects invalid content."""
        parser = MarkdownParser()

        assert parser.validate_format("") is False
        assert parser.validate_format({"not": "markdown"}) is False

    def test_parse_preserves_metadata(self) -> None:
        """Parser captures metadata in PRD."""
        content = """# API Integration

## Overview
REST API integration.
"""

        parser = MarkdownParser()
        prd = parser.parse(content)

        assert prd.metadata.source_format == "markdown"
        assert prd.metadata.version == "1.0"
        assert prd.raw_content == content

    def test_parse_complex_real_world_prd(self) -> None:
        """Parser handles realistic PRD with multiple sections and features."""
        content = """# E-commerce Checkout System

## Overview
Complete checkout flow for e-commerce platform.

## Background
Current checkout has 40% abandonment rate. Need to streamline.

## Features

### Feature 1: Guest Checkout
Allow users to checkout without creating account.

**Requirements:**
- Guest can enter shipping address
- Guest can enter payment details
- Order confirmation sent to email
- Optional account creation after purchase

**Acceptance Criteria:**
- Given guest user, can complete purchase without login
- Given valid payment, order is processed
- Given invalid payment, clear error message shown

**Edge Cases:**
- Duplicate email addresses
- International shipping addresses

### Feature 2: Saved Payment Methods
Users can save payment methods for future purchases.

**Requirements:**
- User can add credit card
- User can remove credit card
- User can set default payment method
- Payment details are encrypted

**Acceptance Criteria:**
- Given saved payment method, user can checkout with one click
- Given multiple payment methods, user can select which to use

## Non-Functional Requirements
- Page load time < 2 seconds
- PCI DSS compliance
- Support 1000 concurrent checkouts
"""

        parser = MarkdownParser()
        prd = parser.parse(content)

        # Validate overall structure
        assert prd.title == "E-commerce Checkout System"
        assert len(prd.features) == 2
        assert len(prd.parsed_sections) >= 4

        # Validate first feature
        feature1 = prd.features[0]
        assert "Guest Checkout" in feature1.name
        assert len(feature1.requirements) == 4
        assert len(feature1.acceptance_criteria) == 3
        assert len(feature1.edge_cases) == 2
        assert "Duplicate email" in feature1.edge_cases[0]

        # Validate second feature
        feature2 = prd.features[1]
        assert "Saved Payment Methods" in feature2.name
        assert len(feature2.requirements) == 4
        assert "encrypted" in feature2.requirements[3].description.lower()
