"""Detect ambiguities and unclear requirements in PRDs using pydantic.ai."""

import re
import time
from uuid import UUID

from pydantic import BaseModel
from pydantic_ai import Agent

from specflow.models import (
    PRD,
    AmbiguityIssue,
    AmbiguityReport,
    AmbiguityType,
    SeverityLevel,
)
from specflow.utils.config import get_settings
from specflow.utils.logger import LoggerMixin


class AmbiguityIssueList(BaseModel):
    """Structured output for ambiguity detection."""

    issues: list[AmbiguityIssue]


class AmbiguityAnalyzer(LoggerMixin):
    """Detect vague, unclear, or ambiguous requirements in PRDs.

    Uses both pattern matching and AI to identify issues like:
    - Vague terms (fast, easy, user-friendly)
    - Missing metrics (many, few, quickly)
    - Subjective language
    - Unclear dependencies
    """

    # Common vague terms to detect
    VAGUE_TERMS = [
        "fast", "slow", "quick", "quickly", "easy", "simple", "hard", "difficult",
        "user-friendly", "intuitive", "seamless", "smooth", "efficient", "optimal",
        "good", "bad", "better", "best", "nice", "clean", "elegant", "beautiful",
        "many", "few", "some", "several", "most", "often", "rarely", "sometimes",
        "large", "small", "big", "tiny", "huge", "massive", "minimal",
        "high", "low", "more", "less",
    ]

    def __init__(self) -> None:
        """Initialize AmbiguityAnalyzer with AI agent."""
        self.settings = get_settings()
        self.agent = self._build_analysis_agent()

    def _get_model(self) -> str:
        """Get the appropriate model string for the configured provider."""
        model_mapping = {
            "openai": "openai:gpt-4o",
            "anthropic": "anthropic:claude-3-5-sonnet-20241022",
            "gemini": "gemini-1.5-flash",
        }
        return model_mapping.get(self.settings.ai_provider, "openai:gpt-4o")

    def _build_analysis_agent(self) -> Agent[None, AmbiguityIssueList]:
        """Build pydantic.ai agent for ambiguity analysis.

        Returns:
            Configured Agent for detecting ambiguities.
        """
        system_prompt = """You are an expert at analyzing requirements for clarity and completeness.

Your task is to identify ambiguities, vague terms, and unclear requirements.

Detect these types of issues:
1. VAGUE_TERM: Subjective terms like "fast", "easy", "user-friendly"
2. MISSING_METRIC: Quantifiable things without numbers (e.g., "many users", "quickly")
3. SUBJECTIVE_LANGUAGE: Beauty/preference terms ("beautiful", "intuitive")
4. MISSING_CONTEXT: Unclear who, what, when, where
5. INCOMPLETE_CONDITION: Missing if/then/else cases

For each issue provide:
- ambiguity_type: The type of ambiguity
- severity: CRITICAL (blocks implementation), HIGH (likely confusion), MEDIUM (should clarify), LOW (nice to clarify)
- original_text: The problematic text
- explanation: Why it's ambiguous
- suggestion: Specific improvement (e.g., "Specify load time under 200ms" not just "add metrics")

Be thorough but not pedantic. Focus on issues that would cause confusion during implementation."""

        return Agent[AmbiguityIssueList](
            self._get_model(),
            system_prompt=system_prompt,
        )

    def detect_ambiguities(self, prd: PRD) -> AmbiguityReport:
        """Detect all ambiguities in a PRD.

        Args:
            prd: PRD to analyze.

        Returns:
            AmbiguityReport with all detected issues.
        """
        start_time = time.time()

        try:
            self.log_info(f"Analyzing PRD for ambiguities: {prd.title}")

            # Collect issues from pattern matching
            pattern_issues: list[AmbiguityIssue] = []
            for feature in prd.features:
                pattern_issues.extend(
                    self._check_for_vague_terms(feature.description, feature.feature_id)
                )

            # Get AI-powered analysis
            ai_issues = self._analyze_with_ai(prd)

            # Combine and deduplicate issues
            all_issues = pattern_issues + ai_issues
            duration = time.time() - start_time

            self.log_info(f"Found {len(all_issues)} ambiguity issues")

            return AmbiguityReport(
                prd_id=prd.prd_id,
                issues=all_issues,
                ai_model_used=self._get_model(),
                analysis_duration_seconds=duration,
            )

        except Exception as e:
            self.log_error(f"Error analyzing ambiguities: {e}", exc_info=True)
            # Return empty report on error
            return AmbiguityReport(
                prd_id=prd.prd_id,
                issues=[],
                ai_model_used=self._get_model(),
                analysis_duration_seconds=time.time() - start_time,
            )

    def _check_for_vague_terms(
        self, text: str, feature_id: UUID | None = None
    ) -> list[AmbiguityIssue]:
        """Check text for vague terms using pattern matching.

        Args:
            text: Text to analyze.
            feature_id: Optional feature ID where text was found.

        Returns:
            List of AmbiguityIssue objects for vague terms found.
        """
        issues: list[AmbiguityIssue] = []
        text_lower = text.lower()

        for term in self.VAGUE_TERMS:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                # Determine severity based on term type
                severity = self._classify_vague_term_severity(term)

                issues.append(
                    AmbiguityIssue(
                        feature_id=feature_id,
                        ambiguity_type=self._classify_vague_term_type(term),
                        severity=severity,
                        original_text=term,
                        explanation=f"'{term}' is vague and subjective. Needs quantification or specific criteria.",
                        suggestion=self._suggest_improvement(term),
                    )
                )

        return issues

    def _classify_vague_term_type(self, term: str) -> AmbiguityType:
        """Classify the type of vague term.

        Args:
            term: The vague term.

        Returns:
            Appropriate AmbiguityType.
        """
        metric_terms = ["many", "few", "some", "several", "most", "large", "small", "quickly", "fast", "slow"]
        subjective_terms = ["beautiful", "elegant", "nice", "clean", "intuitive", "user-friendly"]

        if term.lower() in metric_terms:
            return AmbiguityType.MISSING_METRIC
        elif term.lower() in subjective_terms:
            return AmbiguityType.SUBJECTIVE_LANGUAGE
        else:
            return AmbiguityType.VAGUE_TERM

    def _classify_vague_term_severity(self, term: str) -> SeverityLevel:
        """Classify severity of a vague term.

        Args:
            term: The vague term.

        Returns:
            Appropriate SeverityLevel.
        """
        # Critical: Terms that block implementation
        critical_terms = ["many", "quickly", "fast", "high", "low"]
        # High: Terms likely to cause confusion
        high_terms = ["easy", "simple", "user-friendly", "intuitive"]

        term_lower = term.lower()
        if term_lower in critical_terms:
            return SeverityLevel.HIGH  # Use HIGH instead of CRITICAL for pattern matching
        elif term_lower in high_terms:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW

    def _suggest_improvement(self, term: str) -> str:
        """Suggest specific improvement for a vague term.

        Args:
            term: The vague term.

        Returns:
            Specific suggestion for improvement.
        """
        suggestions = {
            "fast": "Specify response time (e.g., 'API responds in <200ms')",
            "quickly": "Define time constraint (e.g., 'process completes within 5 seconds')",
            "slow": "Specify acceptable delay (e.g., 'background job may take up to 2 minutes')",
            "many": "Provide specific number (e.g., 'support 1000+ concurrent users')",
            "few": "Specify exact count (e.g., 'limit to 3 attempts')",
            "easy": "Define usability criteria (e.g., 'new users complete task in under 2 minutes')",
            "user-friendly": "Specify usability metrics (e.g., '80% of users succeed without help')",
            "intuitive": "Define learnability goals (e.g., 'users find feature without training')",
            "large": "Provide size specification (e.g., 'files up to 100MB')",
            "small": "Specify size limit (e.g., 'thumbnails 150x150 pixels')",
        }

        return suggestions.get(
            term.lower(),
            f"Replace '{term}' with specific, measurable criteria"
        )

    def _analyze_with_ai(self, prd: PRD) -> list[AmbiguityIssue]:
        """Use AI to detect ambiguities beyond pattern matching.

        Args:
            prd: PRD to analyze.

        Returns:
            List of AmbiguityIssue objects detected by AI.

        Raises:
            Exception: If AI call fails.
        """
        try:
            # Build analysis prompt with feature details
            features_text = "\n\n".join([
                f"Feature: {f.name}\nDescription: {f.description}"
                for f in prd.features
            ])

            prompt = f"""PRD Title: {prd.title}

Features to analyze:
{features_text}

Identify ambiguities, vague terms, missing metrics, and unclear requirements.
Focus on issues that would cause confusion during implementation."""

            result = self.agent.run_sync(user_prompt=prompt)

            if result.data and result.data.issues:
                return result.data.issues
            return []

        except Exception as e:
            self.log_error(f"AI ambiguity analysis failed: {e}", exc_info=True)
            raise
