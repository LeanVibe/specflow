"""Generate acceptance criteria and test stubs using pydantic.ai."""

from pydantic import BaseModel
from pydantic_ai import Agent

from specflow.models import Feature
from specflow.utils.config import get_settings
from specflow.utils.logger import LoggerMixin


class CriteriaList(BaseModel):
    """Structured output for acceptance criteria."""

    criteria: list[str]


class TestStubList(BaseModel):
    """Structured output for test stubs."""

    test_stubs: list[str]


class CriteriaGenerator(LoggerMixin):
    """Generate acceptance criteria and test stubs for features using AI.

    Creates Given/When/Then format acceptance criteria and test case templates.
    """

    def __init__(self) -> None:
        """Initialize CriteriaGenerator with AI agents."""
        self.settings = get_settings()
        self.criteria_agent = self._build_criteria_agent()
        self.test_stub_agent = self._build_test_stub_agent()

    def _get_model(self) -> str:
        """Get the appropriate model string for the configured provider."""
        model_mapping = {
            "openai": "openai:gpt-4o",
            "anthropic": "anthropic:claude-3-5-sonnet-20241022",
            "gemini": "gemini-1.5-flash",
        }
        return model_mapping.get(self.settings.ai_provider, "openai:gpt-4o")

    def _build_criteria_agent(self) -> Agent[None, CriteriaList]:
        """Build pydantic.ai agent for generating acceptance criteria.

        Returns:
            Configured Agent for generating criteria.
        """
        system_prompt = """You are an expert at writing acceptance criteria for software features.

Your task is to generate 3-5 clear, testable acceptance criteria in Given/When/Then format.

Format Guidelines:
- Each criterion MUST follow: "Given [context], when [action], then [outcome]"
- Be specific and testable
- Cover happy path, error cases, and edge cases
- Use clear, unambiguous language
- Focus on user-facing behavior, not implementation

Example:
Given a valid email and password, when user submits login form, then user is authenticated and redirected to dashboard

Return exactly 3-5 acceptance criteria."""

        return Agent(
            self._get_model(),
            result_type=CriteriaList,
            system_prompt=system_prompt,
        )

    def _build_test_stub_agent(self) -> Agent[None, TestStubList]:
        """Build pydantic.ai agent for generating test stubs.

        Returns:
            Configured Agent for generating test stubs.
        """
        system_prompt = """You are an expert at designing test cases for software features.

Your task is to generate test case names (stubs) that cover unit, integration, and e2e testing.

Naming Guidelines:
- Use snake_case format
- Start with "test_"
- Be descriptive and specific
- Include test type hint when relevant (e.g., _e2e, _integration)
- Cover different scenarios: happy path, error cases, edge cases, performance

Example test stubs:
- test_login_with_valid_credentials
- test_login_with_invalid_password_shows_error
- test_login_rate_limiting_after_failed_attempts
- test_complete_authentication_flow_e2e

Return 3-7 test stub names."""

        return Agent(
            self._get_model(),
            result_type=TestStubList,
            system_prompt=system_prompt,
        )

    def generate_acceptance_criteria(self, feature: Feature) -> list[str]:
        """Generate acceptance criteria for a feature in Given/When/Then format.

        Args:
            feature: Feature to generate criteria for.

        Returns:
            List of 3-5 acceptance criteria strings, empty list on error.
        """
        try:
            self.log_info(f"Generating acceptance criteria for feature: {feature.name}")
            criteria = self._generate_criteria_with_ai(feature)
            self.log_info(f"Generated {len(criteria)} acceptance criteria")
            return criteria

        except Exception as e:
            self.log_error(f"Error generating acceptance criteria: {e}", exc_info=True)
            return []

    def _generate_criteria_with_ai(self, feature: Feature) -> list[str]:
        """Internal method to generate criteria using AI.

        Args:
            feature: Feature to analyze.

        Returns:
            List of acceptance criteria.

        Raises:
            Exception: If AI call fails.
        """
        try:
            prompt = f"""Feature: {feature.name}

Description: {feature.description}

Generate 3-5 acceptance criteria in Given/When/Then format."""

            result = self.criteria_agent.run_sync(user_prompt=prompt)

            if result.data and result.data.criteria:
                return result.data.criteria
            return []

        except Exception as e:
            self.log_error(f"AI criteria generation failed: {e}", exc_info=True)
            raise

    def generate_test_stubs(self, feature: Feature) -> list[str]:
        """Generate test case template names for a feature.

        Args:
            feature: Feature to generate test stubs for.

        Returns:
            List of test case names in snake_case format, empty list on error.
        """
        try:
            self.log_info(f"Generating test stubs for feature: {feature.name}")
            stubs = self._generate_test_stubs_with_ai(feature)
            self.log_info(f"Generated {len(stubs)} test stubs")
            return stubs

        except Exception as e:
            self.log_error(f"Error generating test stubs: {e}", exc_info=True)
            return []

    def _generate_test_stubs_with_ai(self, feature: Feature) -> list[str]:
        """Internal method to generate test stubs using AI.

        Args:
            feature: Feature to analyze.

        Returns:
            List of test stub names.

        Raises:
            Exception: If AI call fails.
        """
        try:
            prompt = f"""Feature: {feature.name}

Description: {feature.description}

Generate 3-7 test case names (stubs) in snake_case format.
Include unit, integration, and e2e tests as appropriate."""

            result = self.test_stub_agent.run_sync(user_prompt=prompt)

            if result.data and result.data.test_stubs:
                return result.data.test_stubs
            return []

        except Exception as e:
            self.log_error(f"AI test stub generation failed: {e}", exc_info=True)
            raise
