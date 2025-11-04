"""Calculate Definition of Ready quality scores for features using pydantic.ai."""

from uuid import UUID

from specflow.models import (
    Feature,
    QualityCheck,
    QualityCheckCategory,
    QualityScore,
)
from specflow.utils.config import get_settings
from specflow.utils.logger import LoggerMixin


class QualityScorer(LoggerMixin):
    """Calculate Definition of Ready score for features.

    Scoring is based on:
    - Completeness (40%): Has all required fields
    - Clarity (30%): No major ambiguities
    - Testability (20%): Has testable acceptance criteria
    - Feasibility (10%): Is implementable with current info

    Overall score of 80+ indicates feature is ready for implementation.
    """

    # Score weights by category
    WEIGHTS = {
        QualityCheckCategory.COMPLETENESS: 0.40,
        QualityCheckCategory.CLARITY: 0.30,
        QualityCheckCategory.TESTABILITY: 0.20,
        QualityCheckCategory.FEASIBILITY: 0.10,
    }

    READY_THRESHOLD = 80.0

    def __init__(self) -> None:
        """Initialize QualityScorer."""
        self.settings = get_settings()

    def score_readiness(self, feature: Feature, prd_id: UUID) -> QualityScore:
        """Calculate Definition of Ready score for a feature.

        Args:
            feature: Feature to score.
            prd_id: ID of the PRD containing this feature.

        Returns:
            QualityScore with overall score, grade, and detailed checks.
        """
        try:
            self.log_info(f"Scoring feature readiness: {feature.name}")

            # Run all quality checks
            checks: list[QualityCheck] = []

            # Completeness checks (40%)
            checks.extend(self._check_completeness_category(feature))

            # Clarity checks (30%)
            checks.extend(self._check_clarity_category(feature))

            # Testability checks (20%)
            checks.extend(self._check_testability_category(feature))

            # Feasibility checks (10%)
            checks.extend(self._check_feasibility_category(feature))

            # Calculate overall score
            overall_score = self._calculate_overall_score(checks)

            # Determine if ready
            is_ready = overall_score >= self.READY_THRESHOLD

            # Collect blocking issues and recommendations
            blocking_issues = [
                check.details
                for check in checks
                if not check.passed and check.category == QualityCheckCategory.COMPLETENESS
            ]

            recommendations = []
            for check in checks:
                if not check.passed:
                    recommendations.extend(check.recommendations)

            self.log_info(f"Feature '{feature.name}' scored {overall_score:.1f} (Ready: {is_ready})")

            return QualityScore(
                feature_id=feature.feature_id,
                prd_id=prd_id,
                checks=checks,
                overall_score=overall_score,
                is_ready=is_ready,
                blocking_issues=blocking_issues,
                recommendations=recommendations,
            )

        except Exception as e:
            self.log_error(f"Error scoring feature: {e}", exc_info=True)
            # Return minimal score on error
            return QualityScore(
                feature_id=feature.feature_id,
                prd_id=prd_id,
                checks=[],
                overall_score=0.0,
                is_ready=False,
                blocking_issues=["Error during scoring"],
                recommendations=["Review feature manually"],
            )

    def _check_completeness_category(self, feature: Feature) -> list[QualityCheck]:
        """Check completeness of feature definition.

        Args:
            feature: Feature to check.

        Returns:
            List of QualityCheck results for completeness.
        """
        checks_dict = self._check_completeness(feature)
        quality_checks: list[QualityCheck] = []

        # Check: Has name
        quality_checks.append(
            QualityCheck(
                category=QualityCheckCategory.COMPLETENESS,
                check_name="has_name",
                passed=checks_dict["has_name"],
                score=100.0 if checks_dict["has_name"] else 0.0,
                details="Feature has a clear name" if checks_dict["has_name"] else "Feature missing name",
                recommendations=[] if checks_dict["has_name"] else ["Add a clear, descriptive feature name"],
            )
        )

        # Check: Has description
        quality_checks.append(
            QualityCheck(
                category=QualityCheckCategory.COMPLETENESS,
                check_name="has_description",
                passed=checks_dict["has_description"],
                score=100.0 if checks_dict["has_description"] else 0.0,
                details="Feature has detailed description" if checks_dict["has_description"] else "Feature missing description",
                recommendations=[] if checks_dict["has_description"] else ["Add detailed feature description (at least 20 characters)"],
            )
        )

        # Check: Has acceptance criteria
        quality_checks.append(
            QualityCheck(
                category=QualityCheckCategory.COMPLETENESS,
                check_name="has_acceptance_criteria",
                passed=checks_dict["has_acceptance_criteria"],
                score=100.0 if checks_dict["has_acceptance_criteria"] else 0.0,
                details="Feature has acceptance criteria" if checks_dict["has_acceptance_criteria"] else "Feature missing acceptance criteria",
                recommendations=[] if checks_dict["has_acceptance_criteria"] else ["Add 3-5 acceptance criteria in Given/When/Then format"],
            )
        )

        return quality_checks

    def _check_clarity_category(self, feature: Feature) -> list[QualityCheck]:
        """Check clarity of feature definition.

        Args:
            feature: Feature to check.

        Returns:
            List of QualityCheck results for clarity.
        """
        quality_checks: list[QualityCheck] = []

        # Check: Description length and specificity
        desc_length = len(feature.description)
        has_metrics = any(
            indicator in feature.description.lower()
            for indicator in ["ms", "second", "minute", "users", "requests", "mb", "gb", "%"]
        )

        quality_checks.append(
            QualityCheck(
                category=QualityCheckCategory.CLARITY,
                check_name="description_quality",
                passed=desc_length >= 50 and has_metrics,
                score=min(100.0, (desc_length / 100) * 100) if desc_length >= 20 else 0.0,
                details=f"Description is {'clear and specific' if desc_length >= 50 and has_metrics else 'vague or too brief'}",
                recommendations=[] if desc_length >= 50 and has_metrics else ["Add specific metrics and quantifiable requirements"],
            )
        )

        # Check: No obviously vague terms in description
        vague_terms = ["fast", "easy", "simple", "good", "better", "user-friendly", "intuitive"]
        has_vague = any(term in feature.description.lower() for term in vague_terms)

        quality_checks.append(
            QualityCheck(
                category=QualityCheckCategory.CLARITY,
                check_name="no_vague_terms",
                passed=not has_vague,
                score=0.0 if has_vague else 100.0,
                details="No vague terms detected" if not has_vague else "Description contains vague terms",
                recommendations=[] if not has_vague else ["Replace vague terms with specific, measurable criteria"],
            )
        )

        return quality_checks

    def _check_testability_category(self, feature: Feature) -> list[QualityCheck]:
        """Check testability of feature definition.

        Args:
            feature: Feature to check.

        Returns:
            List of QualityCheck results for testability.
        """
        quality_checks: list[QualityCheck] = []

        # Check: Has testable acceptance criteria
        has_testable_ac = len(feature.acceptance_criteria) >= 3
        all_have_structure = all(
            "given" in ac.lower() and "when" in ac.lower() and "then" in ac.lower()
            for ac in feature.acceptance_criteria
        ) if feature.acceptance_criteria else False

        quality_checks.append(
            QualityCheck(
                category=QualityCheckCategory.TESTABILITY,
                check_name="testable_acceptance_criteria",
                passed=has_testable_ac and all_have_structure,
                score=100.0 if has_testable_ac and all_have_structure else 50.0 if has_testable_ac else 0.0,
                details=f"Feature has {len(feature.acceptance_criteria)} acceptance criteria in Given/When/Then format" if all_have_structure else "Acceptance criteria need proper format",
                recommendations=[] if has_testable_ac and all_have_structure else ["Add 3-5 acceptance criteria in Given/When/Then format"],
            )
        )

        # Check: Has test stubs
        has_test_stubs = len(feature.test_stubs) >= 3

        quality_checks.append(
            QualityCheck(
                category=QualityCheckCategory.TESTABILITY,
                check_name="has_test_stubs",
                passed=has_test_stubs,
                score=100.0 if has_test_stubs else 0.0,
                details=f"Feature has {len(feature.test_stubs)} test stubs" if has_test_stubs else "Missing test stubs",
                recommendations=[] if has_test_stubs else ["Generate test case stubs for unit, integration, and e2e testing"],
            )
        )

        return quality_checks

    def _check_feasibility_category(self, feature: Feature) -> list[QualityCheck]:
        """Check feasibility of feature implementation.

        Args:
            feature: Feature to check.

        Returns:
            List of QualityCheck results for feasibility.
        """
        quality_checks: list[QualityCheck] = []

        # Check: Has complexity estimation
        has_complexity = feature.complexity is not None

        quality_checks.append(
            QualityCheck(
                category=QualityCheckCategory.FEASIBILITY,
                check_name="has_complexity_estimate",
                passed=has_complexity,
                score=100.0 if has_complexity else 50.0,  # Not critical
                details=f"Complexity estimated as {feature.complexity.value}" if has_complexity else "No complexity estimation",
                recommendations=[] if has_complexity else ["Estimate feature complexity (trivial/simple/moderate/complex/very_complex)"],
            )
        )

        # Check: No circular dependencies (basic check)
        has_dependencies = len(feature.dependencies) > 0

        quality_checks.append(
            QualityCheck(
                category=QualityCheckCategory.FEASIBILITY,
                check_name="dependency_clarity",
                passed=True,  # Basic implementation - always pass for now
                score=100.0,
                details=f"Feature has {len(feature.dependencies)} dependencies" if has_dependencies else "No dependencies",
                recommendations=[],
            )
        )

        return quality_checks

    def _check_completeness(self, feature: Feature) -> dict[str, bool]:
        """Check if feature has all required fields.

        Args:
            feature: Feature to check.

        Returns:
            Dictionary of completeness checks with True/False values.
        """
        return {
            "has_name": bool(feature.name and len(feature.name) > 0),
            "has_description": bool(feature.description and len(feature.description) >= 20),
            "has_acceptance_criteria": len(feature.acceptance_criteria) > 0,
            "has_requirements": len(feature.requirements) > 0,
            "has_test_stubs": len(feature.test_stubs) > 0,
        }

    def _calculate_overall_score(self, checks: list[QualityCheck]) -> float:
        """Calculate weighted overall score from individual checks.

        Weights: Completeness 40%, Clarity 30%, Testability 20%, Feasibility 10%

        Args:
            checks: List of quality checks.

        Returns:
            Overall score (0-100).
        """
        if not checks:
            return 0.0

        # Calculate average score per category
        category_scores: dict[QualityCheckCategory, float] = {}

        for category in QualityCheckCategory:
            category_checks = [c for c in checks if c.category == category]
            if category_checks:
                avg_score = sum(c.score for c in category_checks) / len(category_checks)
                category_scores[category] = avg_score
            else:
                category_scores[category] = 0.0

        # Apply weights
        overall = sum(
            category_scores.get(category, 0.0) * weight
            for category, weight in self.WEIGHTS.items()
        )

        return round(overall, 2)
