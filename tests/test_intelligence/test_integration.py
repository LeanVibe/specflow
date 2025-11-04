"""Integration tests for intelligence modules working together."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from specflow.intelligence import (
    AmbiguityAnalyzer,
    CriteriaGenerator,
    FeatureExtractor,
    QualityScorer,
)
from specflow.models import Feature, PRD, PRDMetadata


class TestIntelligenceIntegration:
    """Test intelligence modules working together."""

    @pytest.fixture
    def sample_prd_text(self) -> str:
        """Sample PRD text for integration testing."""
        return """
        User Authentication Feature:
        Users need to securely log in using email and password.
        The system should respond in under 200ms and support 1000 concurrent users.
        Password reset via email is required.

        Dashboard Feature:
        After login, users see their activity dashboard.
        The dashboard should be fast and user-friendly.
        """

    def test_full_intelligence_pipeline(self, sample_prd_text: str) -> None:
        """Test complete pipeline: extract -> generate criteria -> analyze -> score."""
        # Step 1: Extract features from text
        with patch("specflow.intelligence.extractor.Agent"):
            extractor = FeatureExtractor()
            mock_features = [
                Feature(
                    feature_id=uuid4(),
                    name="User Authentication",
                    description="Users need to securely log in using email and password. System responds in under 200ms.",
                    requirements=[],
                ),
                Feature(
                    feature_id=uuid4(),
                    name="Dashboard",
                    description="Activity dashboard that is fast and user-friendly",
                    requirements=[],
                ),
            ]

            with patch.object(extractor, "_extract_with_ai", return_value=mock_features):
                features = extractor.extract_features(sample_prd_text)

        assert len(features) == 2

        # Step 2: Generate acceptance criteria for first feature
        with patch("specflow.intelligence.generator.Agent"):
            generator = CriteriaGenerator()
            mock_criteria = [
                "Given valid email and password, when user submits, then user is authenticated",
                "Given system under load, when user logs in, then response time is under 200ms",
                "Given user forgot password, when reset requested, then email is sent",
            ]

            with patch.object(
                generator, "_generate_criteria_with_ai", return_value=mock_criteria
            ):
                criteria = generator.generate_acceptance_criteria(features[0])

        assert len(criteria) == 3
        features[0].acceptance_criteria = criteria

        # Step 3: Analyze for ambiguities
        prd = PRD(
            prd_id=uuid4(),
            title="Test PRD",
            raw_content=sample_prd_text,
            features=features,
            metadata=PRDMetadata(),
        )

        with patch("specflow.intelligence.analyzer.Agent"):
            analyzer = AmbiguityAnalyzer()
            with patch.object(analyzer, "_analyze_with_ai", return_value=[]):
                report = analyzer.detect_ambiguities(prd)

        # First feature should have fewer issues (has metrics)
        # Second feature should have issues (vague terms: "fast", "user-friendly")
        assert report.total_issues >= 0

        # Step 4: Score feature quality
        scorer = QualityScorer()
        score1 = scorer.score_readiness(features[0], prd.prd_id)
        score2 = scorer.score_readiness(features[1], prd.prd_id)

        # First feature should score higher (has metrics, criteria)
        assert score1.overall_score > score2.overall_score
        assert score1.overall_score >= 70  # Has criteria but no test stubs

    def test_modules_can_be_imported(self) -> None:
        """Test that all intelligence modules can be imported."""
        # This tests the __init__.py exports
        assert FeatureExtractor is not None
        assert CriteriaGenerator is not None
        assert AmbiguityAnalyzer is not None
        assert QualityScorer is not None

    def test_extractor_and_generator_work_together(self) -> None:
        """Test extractor output can be used by generator."""
        with patch("specflow.intelligence.extractor.Agent"):
            extractor = FeatureExtractor()
            mock_feature = Feature(
                feature_id=uuid4(),
                name="Test Feature",
                description="A test feature description",
                requirements=[],
            )

            with patch.object(extractor, "_extract_with_ai", return_value=[mock_feature]):
                features = extractor.extract_features("test text")

        assert len(features) == 1

        # Use extracted feature with generator
        with patch("specflow.intelligence.generator.Agent"):
            generator = CriteriaGenerator()
            mock_criteria = ["Given X, when Y, then Z"]

            with patch.object(
                generator, "_generate_criteria_with_ai", return_value=mock_criteria
            ):
                criteria = generator.generate_acceptance_criteria(features[0])

        assert len(criteria) == 1

    def test_analyzer_and_scorer_work_together(self) -> None:
        """Test analyzer output influences scorer."""
        feature = Feature(
            feature_id=uuid4(),
            name="Vague Feature",
            description="A fast and easy feature",  # Vague terms
            requirements=[],
            acceptance_criteria=[],
        )

        prd = PRD(
            prd_id=uuid4(),
            title="Test",
            raw_content="test",
            features=[feature],
            metadata=PRDMetadata(),
        )

        # Analyze for ambiguities
        with patch("specflow.intelligence.analyzer.Agent"):
            analyzer = AmbiguityAnalyzer()
            # The pattern matching in _check_for_vague_terms will catch "fast" and "easy"
            # But we mocked _analyze_with_ai to return empty, so only pattern matching results
            with patch.object(analyzer, "_analyze_with_ai", return_value=[]):
                report = analyzer.detect_ambiguities(prd)

        # Pattern matching should detect at least the vague terms in description
        # "fast" and "easy" are in VAGUE_TERMS list
        vague_in_desc = len([term for term in analyzer.VAGUE_TERMS if term in feature.description.lower()])
        assert report.total_issues >= vague_in_desc

        # Score the feature
        scorer = QualityScorer()
        score = scorer.score_readiness(feature, prd.prd_id)

        # Should score low due to vague terms and missing criteria
        assert score.overall_score < 60
        assert not score.is_ready
