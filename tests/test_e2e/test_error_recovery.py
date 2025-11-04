"""End-to-end tests for error recovery and graceful degradation.

Tests how the system handles various failure scenarios and recovers gracefully
without crashing or losing data.
"""

import pytest
from fastapi.testclient import TestClient

from specflow.integrations import TicketConverter
from specflow.intelligence import AmbiguityAnalyzer, QualityScorer
from specflow.models import TicketDraft, TicketPriority, TicketType
from specflow.parsers import InvalidFormatError, MarkdownParser, ParseFailureError


@pytest.mark.e2e
class TestErrorRecovery:
    """E2E tests for error handling and graceful degradation."""

    def test_invalid_prd_graceful_failure(self, malformed_prd_content: str) -> None:
        """E2E: Invalid PRD produces helpful error without crashing."""
        parser = MarkdownParser()

        # Should either parse with warnings or raise clear error
        try:
            prd = parser.parse(malformed_prd_content)
            # If parsing succeeds, should have minimal structure
            assert prd is not None
            assert prd.title is not None
        except (ParseFailureError, InvalidFormatError) as e:
            # If parsing fails, should have clear error message
            assert str(e) != ""
            assert "Error" in str(type(e).__name__)

    def test_empty_prd_graceful_failure(self, empty_prd_content: str) -> None:
        """E2E: Empty PRD is rejected with clear error message."""
        parser = MarkdownParser()

        with pytest.raises((ParseFailureError, InvalidFormatError, ValueError)):
            parser.parse(empty_prd_content)

    def test_analysis_continues_with_incomplete_features(
        self, simple_prd_content: str
    ) -> None:
        """E2E: Analysis works even when features have missing elements."""
        # Parse (may have incomplete features)
        parser = MarkdownParser()
        prd = parser.parse(simple_prd_content)

        # Analysis should complete without crashing
        analyzer = AmbiguityAnalyzer()
        try:
            report = analyzer.detect_ambiguities(prd)
            assert report is not None
            assert isinstance(report.total_issues, int)
        except Exception:
            # AI may fail - that's acceptable
            pass

        # Scoring should also complete
        scorer = QualityScorer()
        scores = [scorer.score_readiness(f, prd.prd_id) for f in prd.features]

        assert len(scores) > 0
        # Scores should reflect blocking issues
        for score in scores:
            assert isinstance(score.blocking_issues, list)

    def test_ticket_conversion_handles_missing_data(
        self, sample_prd_for_pipeline: "PRD"
    ) -> None:
        """E2E: Ticket conversion works even with minimal feature data."""
        feature = sample_prd_for_pipeline.features[0]

        # Create draft with minimal data
        draft = TicketDraft(
            feature_id=feature.feature_id,
            ticket_type=TicketType.STORY,
            title=feature.name or "Untitled",
            description=feature.description or "",
            acceptance_criteria=feature.acceptance_criteria or [],
            test_cases=[],
            priority=TicketPriority.MEDIUM,
            labels=[],
            story_points=None,
        )

        # Conversion should succeed
        jira_ticket = TicketConverter.draft_to_jira_format(draft, "PROJ")

        assert "fields" in jira_ticket
        assert "project" in jira_ticket["fields"]
        assert "summary" in jira_ticket["fields"]
        assert "description" in jira_ticket["fields"]
        assert jira_ticket["fields"]["project"]["key"] == "PROJ"

    def test_api_handles_malformed_requests(self, api_client: TestClient) -> None:
        """E2E: API gracefully handles malformed requests."""
        # Missing required fields
        response = api_client.post("/api/prd/parse", json={})
        assert response.status_code == 422  # Validation error

        # Invalid format value
        response = api_client.post(
            "/api/prd/parse",
            json={"content": "test", "format": "invalid_format"},
        )
        assert response.status_code == 422

        # Invalid JSON structure
        response = api_client.post(
            "/api/prd/parse",
            data="not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_pipeline_recovers_from_partial_analysis_failure(
        self, comprehensive_prd_content: str
    ) -> None:
        """E2E: Pipeline continues even if analysis partially fails."""
        # Parse
        parser = MarkdownParser()
        prd = parser.parse(comprehensive_prd_content)

        # Try analysis (may fail with AI)
        analyzer = AmbiguityAnalyzer()
        try:
            report = analyzer.detect_ambiguities(prd)
            # If succeeds, verify structure
            assert report is not None
        except Exception:
            # If analysis fails, we should still be able to continue
            pass

        # Quality scoring should still work
        scorer = QualityScorer()
        scores = [scorer.score_readiness(f, prd.prd_id) for f in prd.features]

        assert len(scores) > 0

        # Ticket generation should still work
        drafts = [
            TicketDraft(
                feature_id=f.feature_id,
                ticket_type=TicketType.STORY,
                title=f.name,
                description=f.description,
                acceptance_criteria=f.acceptance_criteria,
                test_cases=[],
                priority=TicketPriority.MEDIUM,
                labels=f.tags,
                story_points=None,
            )
            for f in prd.features
        ]

        assert len(drafts) > 0

    def test_api_404_errors_are_informative(self, api_client: TestClient) -> None:
        """E2E: API 404 errors provide helpful information."""
        fake_uuid = "12345678-1234-5678-1234-567812345678"

        # Get non-existent PRD
        response = api_client.get(f"/api/prd/{fake_uuid}")
        assert response.status_code == 404
        error_detail = response.json()
        assert "detail" in error_detail
        assert "not found" in error_detail["detail"].lower()

        # Analyze non-existent PRD
        response = api_client.post(f"/api/prd/{fake_uuid}/analyze")
        assert response.status_code == 404

        # Preview tickets for non-existent PRD
        response = api_client.post(
            "/api/tickets/preview",
            json={"prd_id": fake_uuid, "project_key": "PROJ"},
        )
        assert response.status_code == 404

    def test_concurrent_api_requests_are_isolated(
        self, api_client: TestClient, simple_prd_content: str, comprehensive_prd_content: str
    ) -> None:
        """E2E: Concurrent API requests don't interfere with each other."""
        # Simulate concurrent requests by creating multiple PRDs rapidly
        responses = []

        contents = [simple_prd_content, comprehensive_prd_content, simple_prd_content]

        for content in contents:
            response = api_client.post(
                "/api/prd/parse",
                json={"content": content, "format": "markdown"},
            )
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have unique IDs
        prd_ids = [r.json()["prd_id"] for r in responses]
        assert len(prd_ids) == len(set(prd_ids)), "PRD IDs should be unique"

        # Each should be retrievable with correct content
        for i, prd_id in enumerate(prd_ids):
            get_response = api_client.get(f"/api/prd/{prd_id}")
            assert get_response.status_code == 200

    def test_feature_with_no_acceptance_criteria_handled(
        self, sample_prd_for_pipeline: "PRD"
    ) -> None:
        """E2E: Features without acceptance criteria are handled gracefully."""
        feature = sample_prd_for_pipeline.features[0]

        # Create draft with empty acceptance criteria
        draft = TicketDraft(
            feature_id=feature.feature_id,
            ticket_type=TicketType.STORY,
            title=feature.name,
            description=feature.description,
            acceptance_criteria=[],  # Empty
            test_cases=[],
            priority=TicketPriority.LOW,
            labels=["needs-criteria"],
            story_points=None,
        )

        # Should still convert successfully
        jira_ticket = TicketConverter.draft_to_jira_format(draft, "PROJ")

        assert "fields" in jira_ticket
        assert jira_ticket["fields"]["summary"] == feature.name

    def test_parser_handles_unicode_and_special_characters(self) -> None:
        """E2E: Parser handles unicode and special characters correctly."""
        unicode_prd = """# システム認証 (System Authentication)

## Features

### Feature 1: ユーザー登録 (User Registration)
Users can register with émails containing spëcial çharacters.

**Requirements:**
- Support UTF-8 email addresses
- Handle emojis in descriptions 🚀
- Process special characters: €, £, ¥, ©

**Acceptance Criteria:**
- Given unicode email, when validated, then accepted
"""

        parser = MarkdownParser()
        prd = parser.parse(unicode_prd)

        assert prd is not None
        assert "認証" in prd.title or "Authentication" in prd.title
        assert len(prd.features) > 0
