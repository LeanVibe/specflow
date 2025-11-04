"""Pytest configuration and shared fixtures."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from specflow.models import (
    ComplexityLevel,
    Feature,
    PRD,
    PRDMetadata,
    PRDSection,
    PriorityLevel,
    Requirement,
    RequirementType,
    TicketDraft,
    TicketPriority,
    TicketType,
)


@pytest.fixture
def sample_requirement() -> Requirement:
    """Create a sample requirement for testing."""
    return Requirement(
        requirement_id=uuid4(),
        description="User must be able to log in with email and password",
        requirement_type=RequirementType.FUNCTIONAL,
        priority=PriorityLevel.HIGH,
        acceptance_criteria=[
            "Given a valid email and password, when user submits login form, then user is authenticated",
            "Given invalid credentials, when user submits login form, then error message is displayed",
        ],
        edge_cases=["Empty email field", "SQL injection attempts", "Very long passwords"],
    )


@pytest.fixture
def sample_feature(sample_requirement: Requirement) -> Feature:
    """Create a sample feature for testing."""
    return Feature(
        feature_id=uuid4(),
        name="User Authentication",
        description="Allow users to securely log in and log out of the application",
        user_story="As a user, I want to log in securely so that I can access my personalized content",
        requirements=[sample_requirement],
        acceptance_criteria=[
            "User can log in with valid credentials",
            "User can log out successfully",
            "Invalid login attempts are handled gracefully",
        ],
        test_stubs=[
            "test_login_with_valid_credentials",
            "test_login_with_invalid_credentials",
            "test_logout_clears_session",
        ],
        priority=PriorityLevel.CRITICAL,
        complexity=ComplexityLevel.MODERATE,
        estimated_days=5.0,
        tags=["security", "authentication", "mvp"],
    )


@pytest.fixture
def sample_prd(sample_feature: Feature) -> PRD:
    """Create a sample PRD for testing."""
    return PRD(
        prd_id=uuid4(),
        title="MVP Authentication System",
        raw_content="# Authentication System\n\nWe need user authentication...",
        parsed_sections=[
            PRDSection(
                title="Overview",
                content="Authentication system for secure user access",
                order=0,
            ),
            PRDSection(
                title="Features",
                content="Login, logout, password reset",
                order=1,
            ),
        ],
        features=[sample_feature],
        metadata=PRDMetadata(
            author="Product Manager",
            version="1.0",
            source_format="markdown",
            tags=["mvp", "security"],
        ),
    )


@pytest.fixture
def sample_ticket_draft() -> TicketDraft:
    """Create a sample ticket draft for testing."""
    return TicketDraft(
        feature_id=uuid4(),
        ticket_type=TicketType.STORY,
        title="Implement user login with email and password",
        description="Users need to be able to log in securely using their email and password.",
        acceptance_criteria=[
            "Given valid credentials, user can log in successfully",
            "Given invalid credentials, appropriate error is shown",
            "Login form validates email format",
        ],
        test_cases=[],
        priority=TicketPriority.HIGH,
        labels=["authentication", "security", "mvp"],
        story_points=5,
    )


@pytest.fixture
def uuid_sample() -> UUID:
    """Provide a consistent UUID for testing."""
    return UUID("12345678-1234-5678-1234-567812345678")
