"""Tests for SpecFlow data models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from specflow.models import (
    AmbiguityIssue,
    AmbiguityReport,
    AmbiguityType,
    ComplexityLevel,
    Feature,
    PRD,
    PriorityLevel,
    QualityCheck,
    QualityCheckCategory,
    QualityScore,
    Requirement,
    RequirementType,
    SeverityLevel,
    TicketBatch,
    TicketDraft,
    TicketPriority,
    TicketStatus,
    TicketType,
)


class TestRequirementModel:
    """Tests for Requirement model."""

    def test_requirement_creation_valid(self, sample_requirement: Requirement) -> None:
        """Valid requirement data creates model successfully."""
        assert sample_requirement.description == "User must be able to log in with email and password"
        assert sample_requirement.requirement_type == RequirementType.FUNCTIONAL
        assert sample_requirement.priority == PriorityLevel.HIGH
        assert len(sample_requirement.acceptance_criteria) == 2
        assert len(sample_requirement.edge_cases) == 3

    def test_requirement_has_acceptance_criteria(self, sample_requirement: Requirement) -> None:
        """Computed field correctly identifies presence of acceptance criteria."""
        assert sample_requirement.has_acceptance_criteria is True

        req_without_ac = Requirement(description="A requirement without AC")
        assert req_without_ac.has_acceptance_criteria is False

    def test_requirement_is_blocked(self) -> None:
        """Computed field correctly identifies blocked requirements."""
        blocked_req = Requirement(
            description="Blocked requirement", dependencies=[uuid4(), uuid4()]
        )
        assert blocked_req.is_blocked is True

        unblocked_req = Requirement(description="Unblocked requirement")
        assert unblocked_req.is_blocked is False

    def test_requirement_invalid_empty_description(self) -> None:
        """Invalid data raises validation errors."""
        with pytest.raises(ValidationError) as exc_info:
            Requirement(description="")
        assert "description" in str(exc_info.value)


class TestFeatureModel:
    """Tests for Feature model."""

    def test_feature_creation_valid(self, sample_feature: Feature) -> None:
        """Valid feature data creates model successfully."""
        assert sample_feature.name == "User Authentication"
        assert len(sample_feature.requirements) == 1
        assert len(sample_feature.acceptance_criteria) == 3
        assert sample_feature.priority == PriorityLevel.CRITICAL
        assert sample_feature.complexity == ComplexityLevel.MODERATE

    def test_feature_computed_fields(self, sample_feature: Feature) -> None:
        """Computed fields calculate correctly."""
        assert sample_feature.requirement_count == 1
        assert sample_feature.acceptance_criteria_count == 3
        assert sample_feature.is_complete is True

    def test_feature_is_complete_false(self) -> None:
        """Feature without requirements or AC is not complete."""
        incomplete = Feature(name="Incomplete", description="Missing stuff")
        assert incomplete.is_complete is False

    def test_feature_priority_scoring(self, sample_feature: Feature) -> None:
        """Priority calculation from impact/effort."""
        score = sample_feature.calculate_priority_score()
        assert score == 4  # CRITICAL = 4

        medium_feature = Feature(
            name="Medium Feature",
            description="Medium priority",
            priority=PriorityLevel.MEDIUM,
        )
        assert medium_feature.calculate_priority_score() == 2


class TestPRDModel:
    """Tests for PRD model."""

    def test_prd_creation_valid(self, sample_prd: PRD) -> None:
        """Valid PRD data creates model successfully."""
        assert sample_prd.title == "MVP Authentication System"
        assert len(sample_prd.features) == 1
        assert len(sample_prd.parsed_sections) == 2
        assert sample_prd.metadata.author == "Product Manager"

    def test_prd_computed_fields(self, sample_prd: PRD) -> None:
        """PRD computed fields calculate correctly."""
        assert sample_prd.feature_count == 1
        assert sample_prd.total_requirements == 1
        assert sample_prd.completion_percentage == 100.0

    def test_prd_completion_percentage_zero_features(self) -> None:
        """PRD with no features has 0% completion."""
        empty_prd = PRD(title="Empty PRD", raw_content="Nothing here")
        assert empty_prd.completion_percentage == 0.0

    def test_prd_get_features_by_priority(self, sample_prd: PRD) -> None:
        """Get features by priority level."""
        critical_features = sample_prd.get_features_by_priority(PriorityLevel.CRITICAL)
        assert len(critical_features) == 1
        assert critical_features[0].name == "User Authentication"

        low_features = sample_prd.get_features_by_priority(PriorityLevel.LOW)
        assert len(low_features) == 0

    def test_prd_get_critical_features(self, sample_prd: PRD) -> None:
        """Get all critical priority features."""
        critical = sample_prd.get_critical_features()
        assert len(critical) == 1
        assert critical[0].priority == PriorityLevel.CRITICAL

    def test_prd_get_feature_by_id(self, sample_prd: PRD, sample_feature: Feature) -> None:
        """Get feature by its ID."""
        found = sample_prd.get_feature_by_id(sample_feature.feature_id)
        assert found is not None
        assert found.name == "User Authentication"

        not_found = sample_prd.get_feature_by_id(uuid4())
        assert not_found is None


class TestTicketDraftModel:
    """Tests for TicketDraft model."""

    def test_ticket_draft_creation_valid(self, sample_ticket_draft: TicketDraft) -> None:
        """Valid ticket draft data creates model successfully."""
        assert sample_ticket_draft.title == "Implement user login with email and password"
        assert sample_ticket_draft.ticket_type == TicketType.STORY
        assert sample_ticket_draft.priority == TicketPriority.HIGH
        assert len(sample_ticket_draft.acceptance_criteria) == 3

    def test_ticket_draft_computed_fields(self, sample_ticket_draft: TicketDraft) -> None:
        """Ticket draft computed fields work correctly."""
        assert sample_ticket_draft.has_acceptance_criteria is True
        assert sample_ticket_draft.has_test_cases is False

    def test_ticket_draft_is_complete(self, sample_ticket_draft: TicketDraft) -> None:
        """Ticket draft completeness check."""
        # Sample draft is missing test cases
        assert sample_ticket_draft.is_complete_draft is False

        # Add test cases to make it complete
        from specflow.models import TestCase

        sample_ticket_draft.test_cases = [
            TestCase(
                name="test_login_valid",
                test_type="unit",
                description="Test login with valid credentials",
            )
        ]
        assert sample_ticket_draft.is_complete_draft is True

    def test_ticket_draft_to_html(self, sample_ticket_draft: TicketDraft) -> None:
        """Convert draft to HTML description."""
        html = sample_ticket_draft.to_description_html()
        assert "<h2>Description</h2>" in html
        assert "<h2>Acceptance Criteria</h2>" in html
        assert "<ul>" in html
        assert "valid credentials" in html


class TestTicketBatchModel:
    """Tests for TicketBatch model."""

    def test_ticket_batch_creation(self, sample_ticket_draft: TicketDraft) -> None:
        """Ticket batch created with drafts."""
        batch = TicketBatch(
            prd_id=uuid4(),
            project_key="PROJ",
            drafts=[sample_ticket_draft],
        )
        assert batch.total_count == 1
        assert batch.success_count == 0
        assert batch.failed_count == 0

    def test_ticket_batch_success_rate(self, sample_ticket_draft: TicketDraft) -> None:
        """Success rate calculation."""
        batch = TicketBatch(
            prd_id=uuid4(),
            project_key="PROJ",
            drafts=[sample_ticket_draft, sample_ticket_draft, sample_ticket_draft],
        )

        # Simulate 2 successes and 1 failure
        from specflow.models import JiraTicket

        batch.created_tickets = [
            JiraTicket(
                ticket_id="PROJ-1",
                draft_id=sample_ticket_draft.draft_id,
                project_key="PROJ",
                issue_key="PROJ-1",
                summary="Test",
                description_html="<p>Test</p>",
                jira_url="https://jira.example.com/PROJ-1",
            ),
            JiraTicket(
                ticket_id="PROJ-2",
                draft_id=sample_ticket_draft.draft_id,
                project_key="PROJ",
                issue_key="PROJ-2",
                summary="Test",
                description_html="<p>Test</p>",
                jira_url="https://jira.example.com/PROJ-2",
            ),
        ]
        batch.failed_drafts = [(uuid4(), "Connection error")]

        assert batch.success_count == 2
        assert batch.failed_count == 1
        assert batch.success_rate == pytest.approx(66.67, rel=0.1)
        assert batch.has_failures is True


class TestAmbiguityReportModel:
    """Tests for AmbiguityReport model."""

    def test_ambiguity_report_creation(self) -> None:
        """Ambiguity report with issues."""
        issue1 = AmbiguityIssue(
            ambiguity_type=AmbiguityType.VAGUE_TERM,
            severity=SeverityLevel.HIGH,
            original_text="The system should be fast",
            explanation="'fast' is subjective and unmeasurable",
            suggestion="Specify response time (e.g., 'responds in < 200ms')",
        )

        issue2 = AmbiguityIssue(
            ambiguity_type=AmbiguityType.MISSING_METRIC,
            severity=SeverityLevel.CRITICAL,
            original_text="Handle large number of users",
            explanation="'large number' is undefined",
            suggestion="Specify exact user count (e.g., '10,000 concurrent users')",
        )

        report = AmbiguityReport(
            prd_id=uuid4(),
            issues=[issue1, issue2],
            ai_model_used="gpt-4",
            analysis_duration_seconds=2.5,
        )

        assert report.total_issues == 2
        assert report.critical_count == 1
        assert report.high_count == 1
        assert report.has_blocking_issues is True

    def test_ambiguity_report_get_by_severity(self) -> None:
        """Filter issues by severity."""
        high_issue = AmbiguityIssue(
            ambiguity_type=AmbiguityType.VAGUE_TERM,
            severity=SeverityLevel.HIGH,
            original_text="fast",
            explanation="Vague",
            suggestion="Be specific",
        )

        low_issue = AmbiguityIssue(
            ambiguity_type=AmbiguityType.SUBJECTIVE_LANGUAGE,
            severity=SeverityLevel.LOW,
            original_text="beautiful",
            explanation="Subjective",
            suggestion="Define criteria",
        )

        report = AmbiguityReport(
            prd_id=uuid4(),
            issues=[high_issue, low_issue],
            ai_model_used="gpt-4",
            analysis_duration_seconds=1.0,
        )

        high_issues = report.get_issues_by_severity(SeverityLevel.HIGH)
        assert len(high_issues) == 1
        assert high_issues[0].severity == SeverityLevel.HIGH


class TestQualityScoreModel:
    """Tests for QualityScore model."""

    def test_quality_score_complete_feature(self) -> None:
        """Complete feature scores 90-100."""
        checks = [
            QualityCheck(
                category=QualityCheckCategory.COMPLETENESS,
                check_name="Has description",
                passed=True,
                score=100.0,
                details="Feature has detailed description",
            ),
            QualityCheck(
                category=QualityCheckCategory.CLARITY,
                check_name="No ambiguities",
                passed=True,
                score=95.0,
                details="Requirements are clear",
            ),
            QualityCheck(
                category=QualityCheckCategory.TESTABILITY,
                check_name="Has AC",
                passed=True,
                score=100.0,
                details="All AC defined",
            ),
        ]

        score = QualityScore(
            prd_id=uuid4(),
            feature_id=uuid4(),
            checks=checks,
            overall_score=95.0,
            is_ready=True,
        )

        assert score.grade == "A"
        assert score.is_ready is True
        assert score.has_blocking_issues is False

    def test_quality_score_incomplete_feature(self) -> None:
        """Incomplete feature scores below 60."""
        checks = [
            QualityCheck(
                category=QualityCheckCategory.COMPLETENESS,
                check_name="Has description",
                passed=False,
                score=40.0,
                details="Missing description",
            )
        ]

        score = QualityScore(
            prd_id=uuid4(),
            checks=checks,
            overall_score=40.0,
            is_ready=False,
            blocking_issues=["Missing description", "No acceptance criteria"],
        )

        assert score.grade == "F"
        assert score.is_ready is False
        assert score.has_blocking_issues is True

    def test_quality_score_category_scores(self) -> None:
        """Category scores compute correctly."""
        checks = [
            QualityCheck(
                category=QualityCheckCategory.COMPLETENESS,
                check_name="Check 1",
                passed=True,
                score=100.0,
                details="Complete",
            ),
            QualityCheck(
                category=QualityCheckCategory.COMPLETENESS,
                check_name="Check 2",
                passed=True,
                score=80.0,
                details="Mostly complete",
            ),
            QualityCheck(
                category=QualityCheckCategory.CLARITY,
                check_name="Check 3",
                passed=True,
                score=90.0,
                details="Clear",
            ),
        ]

        score = QualityScore(
            prd_id=uuid4(),
            checks=checks,
            overall_score=90.0,
            is_ready=True,
        )

        assert score.completeness_score == 90.0  # (100 + 80) / 2
        assert score.clarity_score == 90.0  # 90 / 1
        assert score.testability_score == 0.0  # No testability checks
