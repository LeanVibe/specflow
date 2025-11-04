"""PRD-related API routes."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException

from specflow.api.schemas import (
    AmbiguityIssueSchema,
    FeatureQualitySchema,
    FeatureSchema,
    PRDAnalysisResponse,
    PRDParseRequest,
    PRDResponse,
)
from specflow.intelligence import AmbiguityAnalyzer, QualityScorer
from specflow.models import PRD, Feature
from specflow.parsers import MarkdownParser

router = APIRouter()

# In-memory storage for PRDs (replace with database in production)
prd_store: dict[UUID, PRD] = {}


def feature_to_schema(feature: Feature) -> FeatureSchema:
    """Convert Feature model to FeatureSchema for API response.

    Args:
        feature: Feature model to convert.

    Returns:
        FeatureSchema for API response.
    """
    return FeatureSchema(
        feature_id=feature.feature_id,
        name=feature.name,
        description=feature.description,
        user_story=feature.user_story,
        requirement_count=feature.requirement_count,
        acceptance_criteria_count=feature.acceptance_criteria_count,
        priority=feature.priority,
        complexity=feature.complexity,
        estimated_days=feature.estimated_days,
        is_complete=feature.is_complete,
        tags=feature.tags,
    )


@router.post("/parse", response_model=PRDResponse)
async def parse_prd(request: PRDParseRequest) -> PRDResponse:
    """Parse PRD content into structured format.

    Args:
        request: PRD parse request with content and format.

    Returns:
        Parsed PRD with features and metadata.

    Raises:
        HTTPException: If parsing fails or format is unsupported.
    """
    try:
        # Select parser based on format
        if request.format == "markdown":
            parser = MarkdownParser()
            prd = parser.parse(request.content)
        elif request.format == "notion":
            raise HTTPException(
                status_code=400,
                detail="Notion format parser not yet supported. Use markdown for now.",
            )
        elif request.format == "gdocs":
            raise HTTPException(
                status_code=400,
                detail="Google Docs format parser not yet supported. Use markdown for now.",
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported format: {request.format}"
            )

        # Store PRD in memory
        prd_store[prd.prd_id] = prd

        # Convert to response schema
        return PRDResponse(
            prd_id=prd.prd_id,
            title=prd.title,
            feature_count=prd.feature_count,
            total_requirements=prd.total_requirements,
            completion_percentage=prd.completion_percentage,
            features=[feature_to_schema(f) for f in prd.features],
            created_at=prd.created_at,
        )
    except Exception as e:
        # If not already an HTTPException, wrap it
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=500, detail=f"Failed to parse PRD: {str(e)}"
        ) from e


@router.get("/{prd_id}", response_model=PRDResponse)
async def get_prd(prd_id: UUID) -> PRDResponse:
    """Retrieve parsed PRD by ID.

    Args:
        prd_id: UUID of the PRD to retrieve.

    Returns:
        PRD with features and metadata.

    Raises:
        HTTPException: If PRD not found.
    """
    if prd_id not in prd_store:
        raise HTTPException(status_code=404, detail=f"PRD {prd_id} not found")

    prd = prd_store[prd_id]
    return PRDResponse(
        prd_id=prd.prd_id,
        title=prd.title,
        feature_count=prd.feature_count,
        total_requirements=prd.total_requirements,
        completion_percentage=prd.completion_percentage,
        features=[feature_to_schema(f) for f in prd.features],
        created_at=prd.created_at,
    )


@router.post("/{prd_id}/analyze", response_model=PRDAnalysisResponse)
async def analyze_prd(prd_id: UUID) -> PRDAnalysisResponse:
    """Analyze PRD for ambiguities and quality.

    Args:
        prd_id: UUID of the PRD to analyze.

    Returns:
        Analysis report with ambiguity issues and quality scores.

    Raises:
        HTTPException: If PRD not found.
    """
    if prd_id not in prd_store:
        raise HTTPException(status_code=404, detail=f"PRD {prd_id} not found")

    prd = prd_store[prd_id]

    # Run analyzers
    ambiguity_analyzer = AmbiguityAnalyzer()
    quality_scorer = QualityScorer()

    # Detect ambiguities
    ambiguity_report = ambiguity_analyzer.detect_ambiguities(prd)

    # Score feature quality
    feature_scores = [quality_scorer.score_readiness(feature) for feature in prd.features]

    # Calculate average quality score
    avg_quality = (
        sum(score.overall_score for score in feature_scores) / len(feature_scores)
        if feature_scores
        else 0.0
    )

    # Count critical issues and warnings
    critical_count = sum(
        1 for issue in ambiguity_report.issues if issue.severity.value == "critical"
    )
    warning_count = sum(
        1 for issue in ambiguity_report.issues if issue.severity.value in ("high", "medium")
    )

    # Convert to response schemas
    ambiguity_issues = [
        AmbiguityIssueSchema(
            issue_type=issue.issue_type.value,
            severity=issue.severity.value,
            location=issue.location,
            description=issue.description,
            suggestion=issue.suggestion,
        )
        for issue in ambiguity_report.issues
    ]

    quality_schemas = [
        FeatureQualitySchema(
            feature_id=score.feature_id,
            feature_name=next(
                (f.name for f in prd.features if f.feature_id == score.feature_id), "Unknown"
            ),
            overall_score=score.overall_score,
            completeness_score=score.completeness_score,
            clarity_score=score.clarity_score,
            testability_score=score.testability_score,
            is_ready=score.is_ready,
            missing_elements=score.missing_elements,
        )
        for score in feature_scores
    ]

    return PRDAnalysisResponse(
        prd_id=prd_id,
        ambiguity_count=len(ambiguity_report.issues),
        critical_issues=critical_count,
        warnings=warning_count,
        average_quality_score=avg_quality,
        ambiguity_issues=ambiguity_issues,
        feature_quality_scores=quality_schemas,
        analyzed_at=datetime.now(UTC),
    )
