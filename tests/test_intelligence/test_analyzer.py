"""Tests for Ambiguity Analyzer using pydantic.ai."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from specflow.intelligence.analyzer import AmbiguityAnalyzer
from specflow.models import (
    PRD,
    AmbiguityIssue,
    AmbiguityReport,
    AmbiguityType,
    Feature,
    PRDMetadata,
    SeverityLevel,
)


class TestAmbiguityAnalyzer:
    """Test suite for AmbiguityAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> AmbiguityAnalyzer:
        """Create AmbiguityAnalyzer instance with mocked agent."""
        with patch("specflow.intelligence.analyzer.Agent"):
            return AmbiguityAnalyzer()

    @pytest.fixture
    def vague_feature(self) -> Feature:
        """Feature with vague terms."""
        return Feature(
            feature_id=uuid4(),
            name="Fast Dashboard",
            description="The dashboard should be fast and user-friendly. It needs to be intuitive and easy to use.",
            requirements=[],
        )

    @pytest.fixture
    def clear_feature(self) -> Feature:
        """Feature with clear, specific requirements."""
        return Feature(
            feature_id=uuid4(),
            name="User Dashboard",
            description="Display user activity in a table with 50 items per page. Load time must be under 200ms.",
            requirements=[],
        )

    @pytest.fixture
    def missing_metrics_feature(self) -> Feature:
        """Feature missing quantifiable metrics."""
        return Feature(
            feature_id=uuid4(),
            name="Performance Optimization",
            description="The system needs to handle many concurrent users and process requests quickly.",
            requirements=[],
        )

    @pytest.fixture
    def sample_prd_with_vague_features(self, vague_feature: Feature) -> PRD:
        """PRD containing vague features."""
        return PRD(
            prd_id=uuid4(),
            title="Vague Requirements",
            raw_content="The system should be fast and easy.",
            features=[vague_feature],
            metadata=PRDMetadata(),
        )

    @pytest.fixture
    def sample_prd_clear(self, clear_feature: Feature) -> PRD:
        """PRD with clear requirements."""
        return PRD(
            prd_id=uuid4(),
            title="Clear Requirements",
            raw_content="Specific metrics and clear goals.",
            features=[clear_feature],
            metadata=PRDMetadata(),
        )

    def test_detects_vague_terms(
        self, analyzer: AmbiguityAnalyzer, vague_feature: Feature
    ) -> None:
        """Test detection of vague terms like 'fast', 'easy', 'user-friendly'."""
        issues = analyzer._check_for_vague_terms(vague_feature.description, vague_feature.feature_id)

        # Should detect multiple vague terms
        assert len(issues) >= 2
        vague_terms_found = [issue.original_text.lower() for issue in issues]
        assert any(term in " ".join(vague_terms_found) for term in ["fast", "user-friendly", "intuitive", "easy"])

    def test_flags_missing_metrics(
        self, analyzer: AmbiguityAnalyzer, missing_metrics_feature: Feature
    ) -> None:
        """Test flagging of missing metrics in requirements."""
        issues = analyzer._check_for_vague_terms(
            missing_metrics_feature.description, missing_metrics_feature.feature_id
        )

        # Should flag "many" and "quickly" as needing quantification
        assert len(issues) >= 1
        vague_terms = " ".join([issue.original_text.lower() for issue in issues])
        assert "many" in vague_terms or "quickly" in vague_terms

    def test_suggests_improvements(
        self, analyzer: AmbiguityAnalyzer, sample_prd_with_vague_features: PRD
    ) -> None:
        """Test that analyzer suggests improvements for vague requirements."""
        # Mock AI suggestions
        mock_issues = [
            AmbiguityIssue(
                feature_id=sample_prd_with_vague_features.features[0].feature_id,
                ambiguity_type=AmbiguityType.VAGUE_TERM,
                severity=SeverityLevel.HIGH,
                original_text="fast",
                explanation="'Fast' is subjective and not measurable",
                suggestion="Specify load time requirements (e.g., 'page load under 200ms')",
            )
        ]

        with patch.object(analyzer, "_analyze_with_ai", return_value=mock_issues):
            report = analyzer.detect_ambiguities(sample_prd_with_vague_features)

        assert report.total_issues > 0
        # All issues should have suggestions
        assert all(issue.suggestion for issue in report.issues)
        # Suggestions should be specific
        assert any(len(issue.suggestion) > 20 for issue in report.issues)

    def test_classifies_severity(
        self, analyzer: AmbiguityAnalyzer, sample_prd_with_vague_features: PRD
    ) -> None:
        """Test that ambiguities are classified by severity."""
        mock_issues = [
            AmbiguityIssue(
                feature_id=sample_prd_with_vague_features.features[0].feature_id,
                ambiguity_type=AmbiguityType.MISSING_METRIC,
                severity=SeverityLevel.CRITICAL,
                original_text="fast",
                explanation="No performance metrics defined",
                suggestion="Define specific performance requirements",
            ),
            AmbiguityIssue(
                feature_id=sample_prd_with_vague_features.features[0].feature_id,
                ambiguity_type=AmbiguityType.VAGUE_TERM,
                severity=SeverityLevel.MEDIUM,
                original_text="user-friendly",
                explanation="Subjective term",
                suggestion="Define specific usability criteria",
            ),
        ]

        with patch.object(analyzer, "_analyze_with_ai", return_value=mock_issues):
            report = analyzer.detect_ambiguities(sample_prd_with_vague_features)

        # Check severity distribution
        assert report.critical_count >= 1
        assert report.high_count + report.critical_count >= 1
        # Issues should have different severity levels
        severities = {issue.severity for issue in report.issues}
        assert len(severities) >= 1

    def test_no_ambiguities_in_clear_text(
        self, analyzer: AmbiguityAnalyzer, sample_prd_clear: PRD
    ) -> None:
        """Test that clear, specific text has no/few ambiguities."""
        # Mock AI response for clear text
        with patch.object(analyzer, "_analyze_with_ai", return_value=[]):
            report = analyzer.detect_ambiguities(sample_prd_clear)

        # Should have no critical issues
        assert report.critical_count == 0
        # Should not have blocking issues
        assert not report.has_blocking_issues

    def test_detect_ambiguities_returns_report(
        self, analyzer: AmbiguityAnalyzer, sample_prd_with_vague_features: PRD
    ) -> None:
        """Test that detect_ambiguities returns proper AmbiguityReport."""
        mock_issues = [
            AmbiguityIssue(
                ambiguity_type=AmbiguityType.VAGUE_TERM,
                severity=SeverityLevel.HIGH,
                original_text="fast",
                explanation="Vague performance term",
                suggestion="Specify load time under 200ms",
            )
        ]

        with patch.object(analyzer, "_analyze_with_ai", return_value=mock_issues):
            report = analyzer.detect_ambiguities(sample_prd_with_vague_features)

        assert isinstance(report, AmbiguityReport)
        assert report.prd_id == sample_prd_with_vague_features.prd_id
        assert len(report.issues) > 0
        assert report.ai_model_used is not None
        assert report.analysis_duration_seconds >= 0

    def test_handles_analysis_errors(
        self, analyzer: AmbiguityAnalyzer, sample_prd_with_vague_features: PRD
    ) -> None:
        """Test that analysis errors are handled gracefully."""
        with patch.object(analyzer, "_analyze_with_ai", side_effect=Exception("API Error")):
            report = analyzer.detect_ambiguities(sample_prd_with_vague_features)

        # Should return report with no issues on error
        assert isinstance(report, AmbiguityReport)
        assert report.total_issues == 0

    def test_detects_multiple_ambiguity_types(
        self, analyzer: AmbiguityAnalyzer, sample_prd_with_vague_features: PRD
    ) -> None:
        """Test detection of multiple types of ambiguities."""
        mock_issues = [
            AmbiguityIssue(
                ambiguity_type=AmbiguityType.VAGUE_TERM,
                severity=SeverityLevel.HIGH,
                original_text="fast",
                explanation="Vague term",
                suggestion="Specify metrics",
            ),
            AmbiguityIssue(
                ambiguity_type=AmbiguityType.MISSING_METRIC,
                severity=SeverityLevel.HIGH,
                original_text="many users",
                explanation="No quantity specified",
                suggestion="Define user count",
            ),
            AmbiguityIssue(
                ambiguity_type=AmbiguityType.SUBJECTIVE_LANGUAGE,
                severity=SeverityLevel.MEDIUM,
                original_text="user-friendly",
                explanation="Subjective",
                suggestion="Define usability metrics",
            ),
        ]

        with patch.object(analyzer, "_analyze_with_ai", return_value=mock_issues):
            report = analyzer.detect_ambiguities(sample_prd_with_vague_features)

        # Should detect at least 3 types
        ambiguity_types = {issue.ambiguity_type for issue in report.issues}
        assert len(ambiguity_types) >= 3
