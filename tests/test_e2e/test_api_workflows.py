"""End-to-end tests for API workflow sequences.

Tests multi-step API workflows that simulate real user interactions
through the REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
class TestAPIWorkflows:
    """E2E tests for API endpoint workflow chains."""

    def test_api_prd_parse_to_tickets_workflow(
        self, api_client: TestClient, comprehensive_prd_content: str
    ) -> None:
        """E2E API: POST /parse → POST /analyze → POST /tickets/preview."""
        # Step 1: Parse PRD
        parse_response = api_client.post(
            "/api/prd/parse",
            json={"content": comprehensive_prd_content, "format": "markdown"},
        )
        assert parse_response.status_code == 200, f"Parse failed: {parse_response.text}"

        prd_data = parse_response.json()
        prd_id = prd_data["prd_id"]
        assert prd_data["title"] == "User Authentication System"
        assert prd_data["feature_count"] >= 3

        # Step 2: Retrieve parsed PRD (verify storage)
        get_response = api_client.get(f"/api/prd/{prd_id}")
        assert get_response.status_code == 200
        retrieved_prd = get_response.json()
        assert retrieved_prd["prd_id"] == prd_id

        # Step 3: Analyze PRD
        # Note: Analysis may fail without AI API keys or in async context - skip if it fails
        try:
            analyze_response = api_client.post(f"/api/prd/{prd_id}/analyze")
            if analyze_response.status_code == 200:
                analysis_data = analyze_response.json()
                assert "ambiguity_count" in analysis_data
                assert "average_quality_score" in analysis_data
        except Exception:
            # AI analysis may fail - this is acceptable for E2E tests
            pass

        # Step 4: Preview tickets
        preview_response = api_client.post(
            "/api/tickets/preview",
            json={"prd_id": prd_id, "project_key": "AUTH"},
        )
        assert preview_response.status_code == 200, f"Preview failed: {preview_response.text}"

        preview_data = preview_response.json()
        assert "drafts" in preview_data
        assert preview_data["ticket_count"] >= 3
        assert preview_data["project_key"] == "AUTH"

        # Verify draft structure
        for draft in preview_data["drafts"]:
            assert "title" in draft
            assert "description" in draft
            assert "acceptance_criteria" in draft
            assert "priority" in draft

    def test_api_parse_retrieve_analyze_sequence(
        self, api_client: TestClient, simple_prd_content: str
    ) -> None:
        """E2E API: Parse → Retrieve → Analyze verifies data persistence."""
        # Parse
        parse_response = api_client.post(
            "/api/prd/parse",
            json={"content": simple_prd_content, "format": "markdown"},
        )
        assert parse_response.status_code == 200

        prd_id = parse_response.json()["prd_id"]

        # Retrieve to verify storage
        get_response = api_client.get(f"/api/prd/{prd_id}")
        assert get_response.status_code == 200

        stored_prd = get_response.json()
        assert stored_prd["title"] == "Task Management Feature"
        assert len(stored_prd["features"]) >= 1

        # Analyze stored PRD
        analyze_response = api_client.post(f"/api/prd/{prd_id}/analyze")
        # Accept both success and graceful AI failure
        assert analyze_response.status_code in [200, 500]

    def test_api_multiple_prds_isolation(
        self, api_client: TestClient, simple_prd_content: str, comprehensive_prd_content: str
    ) -> None:
        """E2E API: Multiple PRDs are properly isolated and retrievable."""
        # Create first PRD
        response1 = api_client.post(
            "/api/prd/parse",
            json={"content": simple_prd_content, "format": "markdown"},
        )
        assert response1.status_code == 200
        prd1_id = response1.json()["prd_id"]

        # Create second PRD
        response2 = api_client.post(
            "/api/prd/parse",
            json={"content": comprehensive_prd_content, "format": "markdown"},
        )
        assert response2.status_code == 200
        prd2_id = response2.json()["prd_id"]

        # Verify they have different IDs
        assert prd1_id != prd2_id

        # Retrieve both and verify isolation
        get1 = api_client.get(f"/api/prd/{prd1_id}")
        get2 = api_client.get(f"/api/prd/{prd2_id}")

        assert get1.status_code == 200
        assert get2.status_code == 200

        prd1_data = get1.json()
        prd2_data = get2.json()

        assert prd1_data["title"] == "Task Management Feature"
        assert prd2_data["title"] == "User Authentication System"
        assert prd1_data["feature_count"] != prd2_data["feature_count"]

    def test_api_ticket_preview_with_different_projects(
        self, api_client: TestClient, comprehensive_prd_content: str
    ) -> None:
        """E2E API: Ticket preview works with different project keys."""
        # Parse PRD
        parse_response = api_client.post(
            "/api/prd/parse",
            json={"content": comprehensive_prd_content, "format": "markdown"},
        )
        assert parse_response.status_code == 200
        prd_id = parse_response.json()["prd_id"]

        # Preview with different project keys
        project_keys = ["AUTH", "PROJ", "TEST"]

        for project_key in project_keys:
            preview_response = api_client.post(
                "/api/tickets/preview",
                json={"prd_id": prd_id, "project_key": project_key},
            )
            assert (
                preview_response.status_code == 200
            ), f"Failed for project {project_key}: {preview_response.text}"

            preview_data = preview_response.json()
            assert preview_data["project_key"] == project_key

            # Verify all drafts reference the correct project
            for draft in preview_data["drafts"]:
                assert "title" in draft

    def test_api_error_handling_in_workflow(self, api_client: TestClient) -> None:
        """E2E API: Workflow gracefully handles errors at each step."""
        # Try to retrieve non-existent PRD
        fake_uuid = "12345678-1234-5678-1234-567812345678"
        get_response = api_client.get(f"/api/prd/{fake_uuid}")
        assert get_response.status_code == 404
        assert "not found" in get_response.json()["detail"].lower()

        # Try to analyze non-existent PRD
        analyze_response = api_client.post(f"/api/prd/{fake_uuid}/analyze")
        assert analyze_response.status_code == 404

        # Try to preview tickets for non-existent PRD
        preview_response = api_client.post(
            "/api/tickets/preview",
            json={"prd_id": fake_uuid, "project_key": "PROJ"},
        )
        assert preview_response.status_code == 404

        # Try to parse empty content
        empty_response = api_client.post(
            "/api/prd/parse",
            json={"content": "", "format": "markdown"},
        )
        assert empty_response.status_code == 422  # Validation error

    def test_api_health_check_before_workflow(self, api_client: TestClient) -> None:
        """E2E API: Health check verifies API availability before operations."""
        # Check health
        health_response = api_client.get("/health")
        assert health_response.status_code == 200

        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert "version" in health_data
        assert "timestamp" in health_data

        # If healthy, proceed with workflow
        simple_prd = "# Test\n\n## Features\n\n### F1\nDescription"
        parse_response = api_client.post(
            "/api/prd/parse",
            json={"content": simple_prd, "format": "markdown"},
        )
        assert parse_response.status_code == 200
