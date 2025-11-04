"""AI intelligence layer for SpecFlow.

This module provides the core AI capabilities that make SpecFlow valuable:
- Feature extraction from unstructured text
- Acceptance criteria generation in Given/When/Then format
- Ambiguity detection and requirement clarity analysis
- Quality scoring for Definition of Ready assessment
"""

from specflow.intelligence.analyzer import AmbiguityAnalyzer
from specflow.intelligence.extractor import FeatureExtractor
from specflow.intelligence.generator import CriteriaGenerator
from specflow.intelligence.scorer import QualityScorer

__all__ = [
    "FeatureExtractor",
    "CriteriaGenerator",
    "AmbiguityAnalyzer",
    "QualityScorer",
]
