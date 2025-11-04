"""Feature extraction from unstructured PRD text using pydantic.ai."""

from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent

from specflow.models import Feature
from specflow.utils.config import get_settings
from specflow.utils.logger import LoggerMixin


class FeatureList(BaseModel):
    """Structured output for feature extraction."""

    features: list[Feature]


class FeatureExtractor(LoggerMixin):
    """Extract features from unstructured PRD text using AI.

    Uses pydantic.ai to identify feature boundaries and extract
    structured Feature objects from raw text.
    """

    def __init__(self) -> None:
        """Initialize FeatureExtractor with AI agent."""
        self.settings = get_settings()
        self.agent = self._build_extraction_agent()

    def _build_extraction_agent(self) -> Agent[None, FeatureList]:
        """Build pydantic.ai agent for feature extraction.

        Returns:
            Configured Agent for extracting features.
        """
        system_prompt = """You are an expert at analyzing Product Requirements Documents (PRDs).
Your task is to extract distinct features from unstructured text.

A feature is a high-level capability or functionality that provides value to users.
For each feature, extract:
- name: Clear, concise feature name (e.g., "User Authentication", "Dashboard")
- description: Detailed description of what the feature does
- requirements: List of specific requirements (extract if clear, otherwise empty list)

Guidelines:
- Identify feature boundaries even when not explicitly marked
- Combine related requirements into single features
- Be conservative: better to have fewer clear features than many vague ones
- If text is too vague or not feature-related, return empty list
- Extract actual features, not general statements like "system should be fast"

Return a structured list of Feature objects."""

        # Map provider name to pydantic.ai model format
        model_mapping = {
            "openai": "openai:gpt-4o",
            "anthropic": "anthropic:claude-3-5-sonnet-20241022",
            "gemini": "gemini-1.5-flash",
        }
        model = model_mapping.get(self.settings.ai_provider, "openai:gpt-4o")

        return Agent(
            model,
            result_type=FeatureList,
            system_prompt=system_prompt,
        )

    def extract_features(self, raw_text: str) -> list[Feature]:
        """Extract features from raw PRD text.

        Args:
            raw_text: Unstructured PRD text to analyze.

        Returns:
            List of extracted Feature objects, empty list if none found or on error.
        """
        # Handle empty input
        if not raw_text or not raw_text.strip():
            self.log_debug("Empty text provided, returning empty feature list")
            return []

        try:
            self.log_info(f"Extracting features from text ({len(raw_text)} chars)")
            features = self._extract_with_ai(raw_text)
            self.log_info(f"Extracted {len(features)} features")
            return features

        except Exception as e:
            self.log_error(f"Error extracting features: {e}", exc_info=True)
            return []

    def _extract_with_ai(self, text: str) -> list[Feature]:
        """Internal method to extract features using AI.

        Args:
            text: Text to analyze.

        Returns:
            List of extracted features.

        Raises:
            Exception: If AI call fails.
        """
        try:
            # Run AI agent synchronously (pydantic-ai supports both sync and async)
            result = self.agent.run_sync(
                user_prompt=f"Extract features from this PRD text:\n\n{text}"
            )

            # Extract features from structured response
            if result.data and result.data.features:
                return result.data.features
            return []

        except Exception as e:
            self.log_error(f"AI extraction failed: {e}", exc_info=True)
            raise
