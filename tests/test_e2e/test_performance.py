"""End-to-end performance benchmark tests.

Tests performance characteristics of the complete pipeline to ensure
the system meets speed and efficiency requirements.
"""

import time

import pytest
from fastapi.testclient import TestClient

from specflow.integrations import TicketConverter
from specflow.intelligence import QualityScorer
from specflow.models import TicketDraft, TicketPriority, TicketType
from specflow.parsers import MarkdownParser


@pytest.mark.e2e
@pytest.mark.slow
class TestPerformance:
    """E2E performance benchmark tests."""

    def test_parse_large_prd_performance(self) -> None:
        """E2E Performance: Parse large PRD (50+ features) in reasonable time."""
        # Generate a large PRD programmatically
        large_prd_content = self._generate_large_prd(num_features=50)

        parser = MarkdownParser()

        start_time = time.time()
        prd = parser.parse(large_prd_content)
        parse_time = time.time() - start_time

        # Verify parsing succeeded
        assert prd is not None
        assert len(prd.features) >= 40  # May parse slightly fewer due to structure

        # Performance check: Should parse in under 5 seconds
        # (Being generous to account for slower CI environments)
        assert parse_time < 5.0, f"Parsing took {parse_time:.2f}s, expected < 5s"

        print(f"Parsed {len(prd.features)} features in {parse_time:.3f}s")

    def test_quality_scoring_performance(self, comprehensive_prd_content: str) -> None:
        """E2E Performance: Score multiple features quickly."""
        # Parse PRD with multiple features
        parser = MarkdownParser()
        prd = parser.parse(comprehensive_prd_content)

        scorer = QualityScorer()

        start_time = time.time()
        scores = [scorer.score_readiness(feature, prd.prd_id) for feature in prd.features]
        score_time = time.time() - start_time

        # Verify scoring succeeded
        assert len(scores) == len(prd.features)
        assert all(0 <= s.overall_score <= 100 for s in scores)

        # Performance check: Should score all features in under 2 seconds
        assert score_time < 2.0, f"Scoring took {score_time:.2f}s, expected < 2s"

        print(
            f"Scored {len(scores)} features in {score_time:.3f}s "
            f"({score_time/len(scores)*1000:.1f}ms per feature)"
        )

    def test_ticket_conversion_bulk_performance(self) -> None:
        """E2E Performance: Convert 50+ tickets efficiently."""
        # Generate 50 ticket drafts
        num_tickets = 50
        drafts = self._generate_ticket_drafts(num_tickets)

        start_time = time.time()
        jira_tickets = [TicketConverter.draft_to_jira_format(d, "PERF") for d in drafts]
        conversion_time = time.time() - start_time

        # Verify conversion succeeded
        assert len(jira_tickets) == num_tickets
        assert all("fields" in t and "project" in t["fields"] for t in jira_tickets)

        # Performance check: Should convert in under 1 second
        assert (
            conversion_time < 1.0
        ), f"Conversion took {conversion_time:.2f}s, expected < 1s"

        print(
            f"Converted {num_tickets} tickets in {conversion_time:.3f}s "
            f"({conversion_time/num_tickets*1000:.1f}ms per ticket)"
        )

    def test_api_parse_endpoint_performance(
        self, api_client: TestClient, comprehensive_prd_content: str
    ) -> None:
        """E2E Performance: API parse endpoint responds quickly."""
        start_time = time.time()
        response = api_client.post(
            "/api/prd/parse",
            json={"content": comprehensive_prd_content, "format": "markdown"},
        )
        response_time = time.time() - start_time

        assert response.status_code == 200

        # Performance check: Should respond in under 3 seconds
        assert (
            response_time < 3.0
        ), f"API parse took {response_time:.2f}s, expected < 3s"

        print(f"API parse endpoint responded in {response_time:.3f}s")

    def test_api_ticket_preview_performance(
        self, api_client: TestClient, comprehensive_prd_content: str
    ) -> None:
        """E2E Performance: Ticket preview generates quickly."""
        # First parse PRD
        parse_response = api_client.post(
            "/api/prd/parse",
            json={"content": comprehensive_prd_content, "format": "markdown"},
        )
        prd_id = parse_response.json()["prd_id"]

        # Measure preview generation time
        start_time = time.time()
        preview_response = api_client.post(
            "/api/tickets/preview",
            json={"prd_id": prd_id, "project_key": "PERF"},
        )
        preview_time = time.time() - start_time

        assert preview_response.status_code == 200

        preview_data = preview_response.json()
        ticket_count = preview_data["ticket_count"]

        # Performance check: Should generate preview in under 2 seconds
        assert (
            preview_time < 2.0
        ), f"Preview took {preview_time:.2f}s, expected < 2s"

        print(
            f"Generated preview for {ticket_count} tickets in {preview_time:.3f}s"
        )

    def test_end_to_end_pipeline_performance(self, comprehensive_prd_content: str) -> None:
        """E2E Performance: Complete pipeline completes in reasonable time."""
        start_time = time.time()

        # Step 1: Parse
        parser = MarkdownParser()
        prd = parser.parse(comprehensive_prd_content)
        parse_time = time.time() - start_time

        # Step 2: Score quality
        scorer = QualityScorer()
        scores = [scorer.score_readiness(f, prd.prd_id) for f in prd.features]
        score_time = time.time() - start_time - parse_time

        # Step 3: Generate drafts
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
        draft_time = time.time() - start_time - parse_time - score_time

        # Step 4: Convert to Jira
        jira_tickets = [TicketConverter.draft_to_jira_format(d, "E2E") for d in drafts]
        convert_time = time.time() - start_time - parse_time - score_time - draft_time

        total_time = time.time() - start_time

        # Verify completion
        assert len(jira_tickets) > 0

        # Performance check: Complete pipeline should finish in under 10 seconds
        assert total_time < 10.0, f"Pipeline took {total_time:.2f}s, expected < 10s"

        print(f"\nPipeline Performance Breakdown:")
        print(f"  Parse:   {parse_time:.3f}s")
        print(f"  Score:   {score_time:.3f}s")
        print(f"  Draft:   {draft_time:.3f}s")
        print(f"  Convert: {convert_time:.3f}s")
        print(f"  TOTAL:   {total_time:.3f}s")

    # Helper methods

    def _generate_large_prd(self, num_features: int) -> str:
        """Generate a large PRD with many features for performance testing."""
        features_text = []

        for i in range(1, num_features + 1):
            feature_text = f"""
### Feature {i}: Feature Number {i}
**Description:** This is feature number {i} for performance testing.

**User Story:** As a user, I want feature {i} so that I can test performance.

**Requirements:**
- Requirement 1 for feature {i}
- Requirement 2 for feature {i}
- Requirement 3 for feature {i}

**Acceptance Criteria:**
- Given condition {i}, when action occurs, then result is achieved
- Given another condition, when action happens, then expected outcome
- Given edge case, when boundary reached, then handled properly
"""
            features_text.append(feature_text)

        return f"""# Large Performance Test PRD

## Overview
This is a large PRD with {num_features} features for performance testing.

## Features

{"".join(features_text)}
"""

    def _generate_ticket_drafts(self, count: int) -> list[TicketDraft]:
        """Generate multiple ticket drafts for bulk testing."""
        from uuid import uuid4

        drafts = []
        for i in range(count):
            draft = TicketDraft(
                feature_id=uuid4(),
                ticket_type=TicketType.STORY,
                title=f"Test Ticket {i}",
                description=f"Description for test ticket {i}",
                acceptance_criteria=[
                    f"Criterion 1 for ticket {i}",
                    f"Criterion 2 for ticket {i}",
                ],
                test_cases=[],
                priority=TicketPriority.MEDIUM,
                labels=["performance-test"],
                story_points=3,
            )
            drafts.append(draft)

        return drafts
