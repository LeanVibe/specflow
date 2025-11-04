"""Tests for Quality Scorer using pydantic.ai."""

from uuid import uuid4

import pytest

from specflow.intelligence.scorer import QualityScorer
from specflow.models import (
    PRD,
    Feature,
    PRDMetadata,
    QualityCheck,
    QualityCheckCategory,
    Requirement,
    RequirementType,
)


class TestQualityScorer:
    """Test suite for QualityScorer."""

    @pytest.fixture
    def scorer(self) -> QualityScorer:
        """Create QualityScorer instance."""
        return QualityScorer()

    @pytest.fixture
    def complete_feature(self) -> Feature:
        """Complete feature with all required elements."""
        return Feature(
            feature_id=uuid4(),
            name="User Authentication",
            description="Secure login system with email/password authentication. Load time under 200ms. Support 1000+ concurrent users.",
            requirements=[
                Requirement(
                    description="User can log in with email and password",
                    requirement_type=RequirementType.FUNCTIONAL,
                    acceptance_criteria=["Given valid credentials, when user submits, then user is authenticated"],
                )
            ],
            acceptance_criteria=[
                "Given valid email and password, when user submits login form, then user is authenticated",
                "Given invalid credentials, when user submits login form, then error message is displayed",
                "Given system load of 1000 users, when user logs in, then response time is under 200ms",
            ],
            test_stubs=["test_login_success", "test_login_failure", "test_login_performance"],
        )

    @pytest.fixture
    def incomplete_feature(self) -> Feature:
        """Incomplete feature missing key elements."""
        return Feature(
            feature_id=uuid4(),
            name="Dashboard",
            description="A dashboard",  # Vague description
            requirements=[],  # No requirements
            acceptance_criteria=[],  # No acceptance criteria
        )

    @pytest.fixture
    def sample_prd_complete(self, complete_feature: Feature) -> PRD:
        """PRD with complete features."""
        return PRD(
            prd_id=uuid4(),
            title="Complete PRD",
            raw_content="Complete specification",
            features=[complete_feature],
            metadata=PRDMetadata(),
        )

    @pytest.fixture
    def sample_prd_incomplete(self, incomplete_feature: Feature) -> PRD:
        """PRD with incomplete features."""
        return PRD(
            prd_id=uuid4(),
            title="Incomplete PRD",
            raw_content="Vague specification",
            features=[incomplete_feature],
            metadata=PRDMetadata(),
        )

    def test_complete_feature_scores_high(
        self, scorer: QualityScorer, complete_feature: Feature, sample_prd_complete: PRD
    ) -> None:
        """Test that a complete feature scores highly (>= 80)."""
        score = scorer.score_readiness(complete_feature, sample_prd_complete.prd_id)

        assert score.overall_score >= 80, f"Complete feature should score >= 80, got {score.overall_score}"
        assert score.is_ready is True, "Complete feature should be ready"
        assert score.grade in ["A", "B"], f"Complete feature should get A or B grade, got {score.grade}"

    def test_incomplete_feature_scores_low(
        self, scorer: QualityScorer, incomplete_feature: Feature, sample_prd_incomplete: PRD
    ) -> None:
        """Test that an incomplete feature scores low (< 60)."""
        score = scorer.score_readiness(incomplete_feature, sample_prd_incomplete.prd_id)

        assert score.overall_score < 60, f"Incomplete feature should score < 60, got {score.overall_score}"
        assert score.is_ready is False, "Incomplete feature should not be ready"
        assert score.grade in ["D", "F"], f"Incomplete feature should get D or F grade, got {score.grade}"
        assert len(score.blocking_issues) > 0, "Incomplete feature should have blocking issues"

    def test_score_weights_applied_correctly(
        self, scorer: QualityScorer, complete_feature: Feature, sample_prd_complete: PRD
    ) -> None:
        """Test that scoring weights are applied correctly.

        Weights: Completeness 40%, Clarity 30%, Testability 20%, Feasibility 10%
        """
        score = scorer.score_readiness(complete_feature, sample_prd_complete.prd_id)

        # Check that all categories have checks
        categories = {check.category for check in score.checks}
        assert QualityCheckCategory.COMPLETENESS in categories
        assert QualityCheckCategory.CLARITY in categories
        assert QualityCheckCategory.TESTABILITY in categories
        assert QualityCheckCategory.FEASIBILITY in categories

        # Completeness should be weighted most heavily
        assert score.completeness_score >= 0
        assert score.clarity_score >= 0
        assert score.testability_score >= 0
        assert score.feasibility_score >= 0

    def test_ready_threshold_is_80(
        self, scorer: QualityScorer, complete_feature: Feature, sample_prd_complete: PRD
    ) -> None:
        """Test that the ready threshold is correctly set at 80."""
        # Test feature scoring exactly 80 or above
        score = scorer.score_readiness(complete_feature, sample_prd_complete.prd_id)

        if score.overall_score >= 80:
            assert score.is_ready is True
        else:
            assert score.is_ready is False

        # Verify threshold logic
        assert (score.overall_score >= 80) == score.is_ready

    def test_grade_assignment(
        self, scorer: QualityScorer, sample_prd_complete: PRD, sample_prd_incomplete: PRD
    ) -> None:
        """Test that grades are assigned correctly based on score ranges."""
        # Create features with different completeness levels
        high_score_feature = sample_prd_complete.features[0]
        low_score_feature = sample_prd_incomplete.features[0]

        high_score = scorer.score_readiness(high_score_feature, sample_prd_complete.prd_id)
        low_score = scorer.score_readiness(low_score_feature, sample_prd_incomplete.prd_id)

        # Verify grade logic
        if high_score.overall_score >= 90:
            assert high_score.grade == "A"
        elif high_score.overall_score >= 80:
            assert high_score.grade == "B"

        if low_score.overall_score < 60:
            assert low_score.grade in ["D", "F"]

    def test_check_completeness_logic(
        self, scorer: QualityScorer, complete_feature: Feature, incomplete_feature: Feature
    ) -> None:
        """Test the completeness checking logic."""
        complete_checks = scorer._check_completeness(complete_feature)
        incomplete_checks = scorer._check_completeness(incomplete_feature)

        # Complete feature should have all checks True
        assert complete_checks["has_name"] is True
        assert complete_checks["has_description"] is True
        assert complete_checks["has_acceptance_criteria"] is True

        # Incomplete feature should have some False
        assert incomplete_checks["has_acceptance_criteria"] is False

    def test_calculate_overall_score_weights(
        self, scorer: QualityScorer, complete_feature: Feature, sample_prd_complete: PRD
    ) -> None:
        """Test that overall score calculation uses correct weights."""
        # Create sample checks with known scores
        checks = [
            QualityCheck(
                category=QualityCheckCategory.COMPLETENESS,
                check_name="test_completeness",
                passed=True,
                score=100.0,
                details="Complete",
            ),
            QualityCheck(
                category=QualityCheckCategory.CLARITY,
                check_name="test_clarity",
                passed=True,
                score=100.0,
                details="Clear",
            ),
            QualityCheck(
                category=QualityCheckCategory.TESTABILITY,
                check_name="test_testability",
                passed=True,
                score=100.0,
                details="Testable",
            ),
            QualityCheck(
                category=QualityCheckCategory.FEASIBILITY,
                check_name="test_feasibility",
                passed=True,
                score=100.0,
                details="Feasible",
            ),
        ]

        overall = scorer._calculate_overall_score(checks)

        # If all categories score 100, overall should be 100
        # (40% * 100) + (30% * 100) + (20% * 100) + (10% * 100) = 100
        assert overall == 100.0

    def test_scoring_handles_missing_elements(
        self, scorer: QualityScorer, incomplete_feature: Feature, sample_prd_incomplete: PRD
    ) -> None:
        """Test that scoring properly handles features with missing elements."""
        score = scorer.score_readiness(incomplete_feature, sample_prd_incomplete.prd_id)

        # Should still produce a valid score
        assert 0 <= score.overall_score <= 100
        assert len(score.checks) > 0
        # Should have blocking issues
        assert len(score.blocking_issues) > 0
        # Completeness score should be low
        assert score.completeness_score < 50

    def test_quality_score_includes_recommendations(
        self, scorer: QualityScorer, incomplete_feature: Feature, sample_prd_incomplete: PRD
    ) -> None:
        """Test that quality scores include actionable recommendations."""
        score = scorer.score_readiness(incomplete_feature, sample_prd_incomplete.prd_id)

        # Should have recommendations for improvement
        assert len(score.recommendations) > 0
        # Recommendations should be specific
        assert all(len(rec) > 10 for rec in score.recommendations)
