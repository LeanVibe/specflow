"""Tests for ticket API routes."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    from specflow.api.main import app

    return TestClient(app)


@pytest.fixture
def sample_prd_id(client: TestClient) -> str:
    """Create a sample PRD and return its ID."""
    prd_content = """# Test Feature

## Features

### Feature 1: User Login
**Description:** Allow users to log in.

**Requirements:**
- Email validation
- Password authentication

**Acceptance Criteria:**
- User can login with valid credentials
- Invalid credentials show error
"""
    response = client.post(
        "/api/prd/parse", json={"content": prd_content, "format": "markdown"}
    )
    return response.json()["prd_id"]


# ============================================================================
# POST /api/tickets/preview Tests
# ============================================================================


def test_preview_tickets_success(client: TestClient, sample_prd_id: str) -> None:
    """POST /api/tickets/preview returns ticket drafts."""
    response = client.post(
        "/api/tickets/preview",
        json={"prd_id": sample_prd_id, "project_key": "PROJ"},
    )

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "preview_id" in data
    assert data["prd_id"] == sample_prd_id
    assert data["project_key"] == "PROJ"
    assert "drafts" in data
    assert "ticket_count" in data
    assert data["ticket_count"] >= 1
    assert "estimated_create_time" in data
    assert "warnings" in data
    assert "has_warnings" in data


def test_preview_tickets_returns_draft_details(
    client: TestClient, sample_prd_id: str
) -> None:
    """POST /api/tickets/preview includes complete draft information."""
    response = client.post(
        "/api/tickets/preview",
        json={"prd_id": sample_prd_id, "project_key": "PROJ"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check draft structure
    draft = data["drafts"][0]
    assert "draft_id" in draft
    assert "feature_id" in draft
    assert "title" in draft
    assert "description" in draft
    assert "acceptance_criteria" in draft
    assert "test_cases" in draft
    assert "priority" in draft
    assert "is_complete_draft" in draft


def test_preview_tickets_invalid_project_key(
    client: TestClient, sample_prd_id: str
) -> None:
    """POST /api/tickets/preview rejects invalid project key."""
    response = client.post(
        "/api/tickets/preview",
        json={"prd_id": sample_prd_id, "project_key": "invalid-key"},
    )

    assert response.status_code == 422  # Validation error


def test_preview_tickets_prd_not_found(client: TestClient) -> None:
    """POST /api/tickets/preview returns 404 for nonexistent PRD."""
    fake_uuid = str(uuid4())
    response = client.post(
        "/api/tickets/preview",
        json={"prd_id": fake_uuid, "project_key": "PROJ"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_preview_tickets_with_specific_features(
    client: TestClient, sample_prd_id: str
) -> None:
    """POST /api/tickets/preview can filter by feature IDs."""
    # Get all features first
    prd_response = client.get(f"/api/prd/{sample_prd_id}")
    feature_id = prd_response.json()["features"][0]["feature_id"]

    response = client.post(
        "/api/tickets/preview",
        json={
            "prd_id": sample_prd_id,
            "project_key": "PROJ",
            "feature_ids": [feature_id],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ticket_count"] == 1
    assert data["drafts"][0]["feature_id"] == feature_id


# ============================================================================
# POST /api/tickets/create Tests
# ============================================================================


def test_create_tickets_validation_only(client: TestClient, sample_prd_id: str) -> None:
    """POST /api/tickets/create validates request format."""
    # This test just validates the request format without actual Jira creation
    # since we don't have Jira OAuth set up in tests
    response = client.post(
        "/api/tickets/create",
        json={"prd_id": sample_prd_id, "project_key": "PROJ"},
    )

    # Should fail with proper error (no OAuth token)
    assert response.status_code in (401, 500)


def test_create_tickets_invalid_project_key(
    client: TestClient, sample_prd_id: str
) -> None:
    """POST /api/tickets/create rejects invalid project key."""
    response = client.post(
        "/api/tickets/create",
        json={"prd_id": sample_prd_id, "project_key": "invalid-key"},
    )

    assert response.status_code == 422  # Validation error


def test_create_tickets_prd_not_found(client: TestClient) -> None:
    """POST /api/tickets/create returns 404 for nonexistent PRD."""
    fake_uuid = str(uuid4())
    response = client.post(
        "/api/tickets/create",
        json={"prd_id": fake_uuid, "project_key": "PROJ"},
    )

    assert response.status_code == 404


# ============================================================================
# GET /api/tickets/batch/{batch_id} Tests
# ============================================================================


def test_get_batch_not_found(client: TestClient) -> None:
    """GET /api/tickets/batch/{batch_id} returns 404 for nonexistent batch."""
    fake_uuid = str(uuid4())
    response = client.get(f"/api/tickets/batch/{fake_uuid}")

    assert response.status_code == 404
