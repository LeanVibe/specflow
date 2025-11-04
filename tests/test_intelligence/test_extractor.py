"""Tests for Feature Extractor using pydantic.ai."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from specflow.intelligence.extractor import FeatureExtractor
from specflow.models import Feature


class TestFeatureExtractor:
    """Test suite for FeatureExtractor."""

    @pytest.fixture
    def extractor(self) -> FeatureExtractor:
        """Create FeatureExtractor instance with mocked agent."""
        with patch("specflow.intelligence.extractor.Agent"):
            return FeatureExtractor()

    @pytest.fixture
    def simple_prd_text(self) -> str:
        """Simple PRD text with one clear feature."""
        return """
        User Authentication Feature:
        Users need to be able to log in using their email and password.
        The system should validate credentials and provide secure access.
        """

    @pytest.fixture
    def multiple_features_text(self) -> str:
        """PRD text with multiple features."""
        return """
        Feature 1: User Login
        Users must authenticate with email/password. Support password reset.

        Feature 2: Dashboard
        After login, users see a personalized dashboard with their activity.
        The dashboard should load quickly and display recent items.
        """

    @pytest.fixture
    def mock_extracted_feature(self) -> Feature:
        """Mock feature extracted by AI."""
        return Feature(
            feature_id=uuid4(),
            name="User Authentication",
            description="Users need to be able to log in using their email and password",
            requirements=[],
            acceptance_criteria=[],
        )

    def test_extract_features_from_paragraph(
        self, extractor: FeatureExtractor, simple_prd_text: str, mock_extracted_feature: Feature
    ) -> None:
        """Test extracting a single feature from a paragraph."""
        # Mock the AI agent's response
        with patch.object(extractor, "_extract_with_ai", return_value=[mock_extracted_feature]):
            features = extractor.extract_features(simple_prd_text)

        assert len(features) == 1
        assert features[0].name == "User Authentication"
        assert "email and password" in features[0].description.lower()

    def test_extract_multiple_features(
        self, extractor: FeatureExtractor, multiple_features_text: str
    ) -> None:
        """Test extracting multiple features from text with multiple sections."""
        # Mock AI returning multiple features
        mock_features = [
            Feature(
                feature_id=uuid4(),
                name="User Login",
                description="Users must authenticate with email/password",
                requirements=[],
            ),
            Feature(
                feature_id=uuid4(),
                name="Dashboard",
                description="Personalized dashboard with user activity",
                requirements=[],
            ),
        ]

        with patch.object(extractor, "_extract_with_ai", return_value=mock_features):
            features = extractor.extract_features(multiple_features_text)

        assert len(features) == 2
        assert features[0].name == "User Login"
        assert features[1].name == "Dashboard"

    def test_extract_with_implicit_requirements(
        self, extractor: FeatureExtractor, simple_prd_text: str
    ) -> None:
        """Test that implicit requirements are captured in description."""
        mock_feature = Feature(
            feature_id=uuid4(),
            name="User Authentication",
            description="Users need to log in with email/password. System validates credentials and provides secure access.",
            requirements=[],
        )

        with patch.object(extractor, "_extract_with_ai", return_value=[mock_feature]):
            features = extractor.extract_features(simple_prd_text)

        assert len(features) == 1
        # Check that security aspect is captured
        assert "secure" in features[0].description.lower() or "validate" in features[0].description.lower()

    def test_handles_unclear_boundaries(self, extractor: FeatureExtractor) -> None:
        """Test handling text with unclear feature boundaries."""
        unclear_text = """
        The system needs to be fast and user-friendly.
        It should work on mobile and desktop.
        Performance is critical for user satisfaction.
        """

        # AI should try to extract something meaningful or return empty
        with patch.object(extractor, "_extract_with_ai", return_value=[]):
            features = extractor.extract_features(unclear_text)

        # Should not crash, even if no clear features
        assert isinstance(features, list)

    def test_empty_text_returns_empty_list(self, extractor: FeatureExtractor) -> None:
        """Test that empty or whitespace-only text returns empty list."""
        features_empty = extractor.extract_features("")
        features_whitespace = extractor.extract_features("   \n\t  ")

        assert features_empty == []
        assert features_whitespace == []

    def test_extract_features_handles_ai_errors(
        self, extractor: FeatureExtractor, simple_prd_text: str
    ) -> None:
        """Test that AI errors are handled gracefully."""
        with patch.object(extractor, "_extract_with_ai", side_effect=Exception("API Error")):
            features = extractor.extract_features(simple_prd_text)

        # Should return empty list on error, not crash
        assert features == []

    def test_extract_with_ai_uses_correct_prompt(
        self, extractor: FeatureExtractor, simple_prd_text: str
    ) -> None:
        """Test that _extract_with_ai is called with text."""
        with patch.object(
            extractor, "_extract_with_ai", return_value=[]
        ) as mock_extract:
            extractor.extract_features(simple_prd_text)

        # Verify the method was called with the text
        mock_extract.assert_called_once_with(simple_prd_text)
