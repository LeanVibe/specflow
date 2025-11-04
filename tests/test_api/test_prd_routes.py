"""Tests for PRD API routes."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    from specflow.api.main import app

    return TestClient(app)


@pytest.fixture
def sample_markdown_prd() -> str:
    """Sample markdown PRD content."""
    return """# User Authentication System

## Overview
Implement a secure user authentication system with email/password login.

## Features

### Feature 1: User Registration
**Description:** Allow new users to register with email and password.

**User Story:** As a new user, I want to create an account so that I can access the platform.

**Requirements:**
- Email validation
- Password strength requirements (min 8 chars, 1 uppercase, 1 number)
- Email confirmation required

**Acceptance Criteria:**
- User can register with valid email and password
- System validates email format
- System enforces password requirements
- Confirmation email sent successfully

### Feature 2: User Login
**Description:** Allow existing users to login with credentials.

**User Story:** As a registered user, I want to login so that I can access my account.

**Requirements:**
- Email/password authentication
- Session management
- Remember me functionality

**Acceptance Criteria:**
- User can login with valid credentials
- Invalid credentials show error message
- Session persists across page reloads
"""


# ============================================================================
# POST /api/prd/parse Tests
# ============================================================================


def test_parse_prd_markdown_success(client: TestClient, sample_markdown_prd: str) -> None:
    """POST /api/prd/parse successfully parses markdown PRD."""
    response = client.post(
        "/api/prd/parse", json={"content": sample_markdown_prd, "format": "markdown"}
    )

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "prd_id" in data
    assert data["title"] == "User Authentication System"
    assert data["feature_count"] >= 2
    assert data["total_requirements"] >= 4
    assert isinstance(data["completion_percentage"], (int, float))
    assert "features" in data
    assert isinstance(data["features"], list)
    assert len(data["features"]) >= 2


def test_parse_prd_extracts_features_correctly(
    client: TestClient, sample_markdown_prd: str
) -> None:
    """POST /api/prd/parse correctly extracts feature information."""
    response = client.post(
        "/api/prd/parse", json={"content": sample_markdown_prd, "format": "markdown"}
    )

    assert response.status_code == 200
    data = response.json()

    # Check first feature
    feature = data["features"][0]
    assert "feature_id" in feature
    assert "name" in feature
    assert "description" in feature
    assert "requirement_count" in feature
    assert "acceptance_criteria_count" in feature
    assert "priority" in feature
    assert "complexity" in feature


def test_parse_prd_empty_content_fails(client: TestClient) -> None:
    """POST /api/prd/parse rejects empty content."""
    response = client.post("/api/prd/parse", json={"content": "", "format": "markdown"})

    assert response.status_code == 422  # Validation error


def test_parse_prd_invalid_format_fails(client: TestClient) -> None:
    """POST /api/prd/parse rejects invalid format."""
    response = client.post(
        "/api/prd/parse", json={"content": "test content", "format": "invalid_format"}
    )

    assert response.status_code == 422  # Validation error


def test_parse_prd_unsupported_format_returns_error(client: TestClient) -> None:
    """POST /api/prd/parse returns error for unsupported but valid format."""
    response = client.post(
        "/api/prd/parse", json={"content": "test content", "format": "notion"}
    )

    # Should fail with proper error message (not yet supported)
    assert response.status_code == 400
    assert "not yet supported" in response.json()["detail"].lower()


def test_parse_prd_with_metadata(client: TestClient, sample_markdown_prd: str) -> None:
    """POST /api/prd/parse accepts optional metadata."""
    response = client.post(
        "/api/prd/parse",
        json={
            "content": sample_markdown_prd,
            "format": "markdown",
            "metadata": {"author": "Test User", "version": "1.0"},
        },
    )

    assert response.status_code == 200


def test_parse_prd_returns_created_timestamp(
    client: TestClient, sample_markdown_prd: str
) -> None:
    """POST /api/prd/parse returns creation timestamp."""
    response = client.post(
        "/api/prd/parse", json={"content": sample_markdown_prd, "format": "markdown"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "created_at" in data
    assert isinstance(data["created_at"], str)


# ============================================================================
# GET /api/prd/{prd_id} Tests
# ============================================================================


def test_get_prd_success(client: TestClient, sample_markdown_prd: str) -> None:
    """GET /api/prd/{prd_id} retrieves parsed PRD."""
    # First create a PRD
    create_response = client.post(
        "/api/prd/parse", json={"content": sample_markdown_prd, "format": "markdown"}
    )
    prd_id = create_response.json()["prd_id"]

    # Then retrieve it
    response = client.get(f"/api/prd/{prd_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["prd_id"] == prd_id
    assert data["title"] == "User Authentication System"


def test_get_prd_not_found(client: TestClient) -> None:
    """GET /api/prd/{prd_id} returns 404 for nonexistent PRD."""
    fake_uuid = str(uuid4())
    response = client.get(f"/api/prd/{fake_uuid}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_prd_invalid_uuid_format(client: TestClient) -> None:
    """GET /api/prd/{prd_id} rejects invalid UUID format."""
    response = client.get("/api/prd/not-a-uuid")

    assert response.status_code == 422


# ============================================================================
# POST /api/prd/{prd_id}/analyze Tests
# ============================================================================


def test_analyze_prd_success(client: TestClient, sample_markdown_prd: str) -> None:
    """POST /api/prd/{prd_id}/analyze returns analysis results."""
    # First create a PRD
    create_response = client.post(
        "/api/prd/parse", json={"content": sample_markdown_prd, "format": "markdown"}
    )
    prd_id = create_response.json()["prd_id"]

    # Then analyze it
    response = client.post(f"/api/prd/{prd_id}/analyze")

    assert response.status_code == 200
    data = response.json()

    # Validate analysis response structure
    assert data["prd_id"] == prd_id
    assert "ambiguity_count" in data
    assert "critical_issues" in data
    assert "warnings" in data
    assert "average_quality_score" in data
    assert "ambiguity_issues" in data
    assert "feature_quality_scores" in data
    assert "analyzed_at" in data


def test_analyze_prd_returns_ambiguity_issues(
    client: TestClient, sample_markdown_prd: str
) -> None:
    """POST /api/prd/{prd_id}/analyze detects ambiguities."""
    create_response = client.post(
        "/api/prd/parse", json={"content": sample_markdown_prd, "format": "markdown"}
    )
    prd_id = create_response.json()["prd_id"]

    response = client.post(f"/api/prd/{prd_id}/analyze")

    assert response.status_code == 200
    data = response.json()

    # Check ambiguity issues structure
    if data["ambiguity_count"] > 0:
        issue = data["ambiguity_issues"][0]
        assert "issue_type" in issue
        assert "severity" in issue
        assert "location" in issue
        assert "description" in issue
        assert "suggestion" in issue


def test_analyze_prd_returns_quality_scores(
    client: TestClient, sample_markdown_prd: str
) -> None:
    """POST /api/prd/{prd_id}/analyze returns feature quality scores."""
    create_response = client.post(
        "/api/prd/parse", json={"content": sample_markdown_prd, "format": "markdown"}
    )
    prd_id = create_response.json()["prd_id"]

    response = client.post(f"/api/prd/{prd_id}/analyze")

    assert response.status_code == 200
    data = response.json()

    # Check quality scores structure
    assert len(data["feature_quality_scores"]) > 0
    score = data["feature_quality_scores"][0]
    assert "feature_id" in score
    assert "feature_name" in score
    assert "overall_score" in score
    assert "completeness_score" in score
    assert "clarity_score" in score
    assert "testability_score" in score
    assert "is_ready" in score
    assert "missing_elements" in score


def test_analyze_prd_not_found(client: TestClient) -> None:
    """POST /api/prd/{prd_id}/analyze returns 404 for nonexistent PRD."""
    fake_uuid = str(uuid4())
    response = client.post(f"/api/prd/{fake_uuid}/analyze")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_analyze_prd_calculates_average_quality(
    client: TestClient, sample_markdown_prd: str
) -> None:
    """POST /api/prd/{prd_id}/analyze calculates average quality score."""
    create_response = client.post(
        "/api/prd/parse", json={"content": sample_markdown_prd, "format": "markdown"}
    )
    prd_id = create_response.json()["prd_id"]

    response = client.post(f"/api/prd/{prd_id}/analyze")

    assert response.status_code == 200
    data = response.json()

    # Average quality should be between 0 and 100
    assert 0 <= data["average_quality_score"] <= 100
