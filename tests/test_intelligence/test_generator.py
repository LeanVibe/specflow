"""Tests for Criteria Generator using pydantic.ai."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from specflow.intelligence.generator import CriteriaGenerator
from specflow.models import Feature


class TestCriteriaGenerator:
    """Test suite for CriteriaGenerator."""

    @pytest.fixture
    def generator(self) -> CriteriaGenerator:
        """Create CriteriaGenerator instance with mocked agent."""
        with patch("specflow.intelligence.generator.Agent"):
            return CriteriaGenerator()

    @pytest.fixture
    def sample_feature(self) -> Feature:
        """Sample feature for testing."""
        return Feature(
            feature_id=uuid4(),
            name="User Authentication",
            description="Allow users to securely log in and log out of the application using email/password",
            requirements=[],
        )

    @pytest.fixture
    def complex_feature(self) -> Feature:
        """Complex feature with multiple aspects."""
        return Feature(
            feature_id=uuid4(),
            name="E-commerce Checkout",
            description="Complete checkout flow with payment processing, address validation, and order confirmation",
            requirements=[],
        )

    def test_generate_acceptance_criteria_format(
        self, generator: CriteriaGenerator, sample_feature: Feature
    ) -> None:
        """Test that generated criteria follow proper format."""
        # Mock AI response
        mock_criteria = [
            "Given a valid email and password, when user submits login form, then user is authenticated",
            "Given invalid credentials, when user submits login form, then error message is displayed",
            "Given a logged-in user, when user clicks logout, then session is terminated",
        ]

        with patch.object(
            generator, "_generate_criteria_with_ai", return_value=mock_criteria
        ):
            criteria = generator.generate_acceptance_criteria(sample_feature)

        assert len(criteria) >= 3
        assert all(isinstance(c, str) for c in criteria)
        # Check that at least some follow Given/When/Then format
        assert any("given" in c.lower() and "when" in c.lower() and "then" in c.lower() for c in criteria)

    def test_criteria_follow_given_when_then(
        self, generator: CriteriaGenerator, sample_feature: Feature
    ) -> None:
        """Test that criteria follow Given/When/Then BDD format."""
        mock_criteria = [
            "Given valid email and password, when user submits, then user is authenticated",
            "Given invalid credentials, when user submits, then error is shown",
        ]

        with patch.object(
            generator, "_generate_criteria_with_ai", return_value=mock_criteria
        ):
            criteria = generator.generate_acceptance_criteria(sample_feature)

        # All should have the three components
        for criterion in criteria:
            lower_c = criterion.lower()
            assert "given" in lower_c, f"Missing 'given' in: {criterion}"
            assert "when" in lower_c, f"Missing 'when' in: {criterion}"
            assert "then" in lower_c, f"Missing 'then' in: {criterion}"

    def test_generate_test_stubs_naming(
        self, generator: CriteriaGenerator, sample_feature: Feature
    ) -> None:
        """Test that test stubs follow proper naming conventions."""
        mock_stubs = [
            "test_login_with_valid_credentials",
            "test_login_with_invalid_credentials",
            "test_logout_clears_session",
        ]

        with patch.object(generator, "_generate_test_stubs_with_ai", return_value=mock_stubs):
            stubs = generator.generate_test_stubs(sample_feature)

        assert len(stubs) >= 3
        # All should start with "test_"
        assert all(stub.startswith("test_") for stub in stubs)
        # Should use snake_case
        assert all("_" in stub for stub in stubs)
        # Should not have spaces or special chars
        assert all(stub.replace("_", "").replace("test", "").isalnum() for stub in stubs)

    def test_test_stubs_include_all_types(
        self, generator: CriteriaGenerator, complex_feature: Feature
    ) -> None:
        """Test that test stubs include unit, integration, and e2e tests."""
        mock_stubs = [
            "test_checkout_validates_address",  # unit
            "test_checkout_processes_payment",  # integration
            "test_complete_checkout_flow_e2e",  # e2e
        ]

        with patch.object(generator, "_generate_test_stubs_with_ai", return_value=mock_stubs):
            stubs = generator.generate_test_stubs(complex_feature)

        # Should have multiple types of tests
        assert len(stubs) >= 3
        # At least one should indicate e2e or integration
        combined = " ".join(stubs)
        assert "e2e" in combined.lower() or "integration" in combined.lower() or "flow" in combined.lower()

    def test_generate_acceptance_criteria_handles_errors(
        self, generator: CriteriaGenerator, sample_feature: Feature
    ) -> None:
        """Test that errors are handled gracefully."""
        with patch.object(
            generator, "_generate_criteria_with_ai", side_effect=Exception("API Error")
        ):
            criteria = generator.generate_acceptance_criteria(sample_feature)

        # Should return empty list on error
        assert criteria == []

    def test_generate_test_stubs_handles_errors(
        self, generator: CriteriaGenerator, sample_feature: Feature
    ) -> None:
        """Test that test stub generation handles errors gracefully."""
        with patch.object(
            generator, "_generate_test_stubs_with_ai", side_effect=Exception("API Error")
        ):
            stubs = generator.generate_test_stubs(sample_feature)

        # Should return empty list on error
        assert stubs == []

    def test_generate_criteria_returns_3_to_5_items(
        self, generator: CriteriaGenerator, sample_feature: Feature
    ) -> None:
        """Test that criteria generation returns 3-5 items as specified."""
        mock_criteria = [
            "Given valid input, when user submits, then action succeeds",
            "Given invalid input, when user submits, then error is shown",
            "Given edge case, when user submits, then handled gracefully",
            "Given timeout, when request fails, then retry logic works",
        ]

        with patch.object(
            generator, "_generate_criteria_with_ai", return_value=mock_criteria
        ):
            criteria = generator.generate_acceptance_criteria(sample_feature)

        assert 3 <= len(criteria) <= 5, f"Expected 3-5 criteria, got {len(criteria)}"
