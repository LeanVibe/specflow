"""Ticket-related API routes."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from specflow.api.routes.prd import prd_store
from specflow.api.schemas import (
    TestCaseSchema,
    TicketBatchResponse,
    TicketCreateRequest,
    TicketDraftSchema,
    TicketPreviewRequest,
    TicketPreviewResponse,
)
from specflow.models import TicketBatch, TicketDraft, TicketPriority, TicketType

router = APIRouter()

# In-memory storage for ticket batches (replace with database in production)
batch_store: dict[UUID, TicketBatch] = {}


def create_ticket_draft_from_feature(feature_id: UUID, title: str, description: str, acceptance_criteria: list[str]) -> TicketDraft:
    """Create a TicketDraft from feature data.

    Args:
        feature_id: Feature UUID.
        title: Ticket title.
        description: Ticket description.
        acceptance_criteria: List of acceptance criteria.

    Returns:
        TicketDraft instance.
    """
    return TicketDraft(
        feature_id=feature_id,
        title=title,
        description=description,
        acceptance_criteria=acceptance_criteria,
        ticket_type=TicketType.STORY,
        priority=TicketPriority.MEDIUM,
    )


@router.post("/preview", response_model=TicketPreviewResponse)
async def preview_tickets(request: TicketPreviewRequest) -> TicketPreviewResponse:
    """Preview tickets without creating in Jira.

    Args:
        request: Ticket preview request.

    Returns:
        Preview with ticket drafts.

    Raises:
        HTTPException: If PRD not found.
    """
    # Get PRD
    if request.prd_id not in prd_store:
        raise HTTPException(status_code=404, detail=f"PRD {request.prd_id} not found")

    prd = prd_store[request.prd_id]

    # Filter features if specific IDs provided
    features = prd.features
    if request.feature_ids:
        features = [f for f in features if f.feature_id in request.feature_ids]

    # Convert features to ticket drafts
    drafts = []
    for feature in features:
        draft = create_ticket_draft_from_feature(
            feature_id=feature.feature_id,
            title=feature.name,
            description=feature.description,
            acceptance_criteria=feature.acceptance_criteria,
        )
        drafts.append(draft)

    # Calculate estimated time (rough estimate: 2 seconds per ticket)
    estimated_time = len(drafts) * 2.0

    # Validate drafts and collect warnings
    warnings = []
    for draft in drafts:
        if not draft.has_acceptance_criteria:
            warnings.append(f"Draft '{draft.title}' has no acceptance criteria")
        if not draft.has_test_cases:
            warnings.append(f"Draft '{draft.title}' has no test cases")

    # Convert drafts to schemas
    draft_schemas = [
        TicketDraftSchema(
            draft_id=draft.draft_id,
            feature_id=draft.feature_id,
            ticket_type=draft.ticket_type,
            title=draft.title,
            description=draft.description,
            acceptance_criteria=draft.acceptance_criteria,
            test_cases=[
                TestCaseSchema(
                    test_id=tc.test_id,
                    name=tc.name,
                    test_type=tc.test_type,
                    description=tc.description,
                    given=tc.given,
                    when=tc.when,
                    then=tc.then,
                )
                for tc in draft.test_cases
            ],
            priority=draft.priority,
            labels=draft.labels,
            story_points=draft.story_points,
            is_complete_draft=draft.is_complete_draft,
        )
        for draft in drafts
    ]

    preview_id = uuid4()
    return TicketPreviewResponse(
        preview_id=preview_id,
        prd_id=request.prd_id,
        project_key=request.project_key,
        drafts=draft_schemas,
        ticket_count=len(drafts),
        estimated_create_time=estimated_time,
        warnings=warnings,
        has_warnings=len(warnings) > 0,
        created_at=datetime.now(UTC),
    )


@router.post("/create", response_model=TicketBatchResponse)
async def create_tickets(request: TicketCreateRequest) -> TicketBatchResponse:
    """Create tickets in Jira.

    Args:
        request: Ticket creation request.

    Returns:
        Batch creation result.

    Raises:
        HTTPException: If PRD not found or OAuth not configured.
    """
    # Get PRD
    if request.prd_id not in prd_store:
        raise HTTPException(status_code=404, detail=f"PRD {request.prd_id} not found")

    # Check OAuth token (placeholder - would check actual token in production)
    raise HTTPException(
        status_code=500,
        detail="Jira integration requires OAuth authentication. Please connect your Jira account first.",
    )


@router.get("/batch/{batch_id}", response_model=TicketBatchResponse)
async def get_batch_status(batch_id: UUID) -> TicketBatchResponse:
    """Get batch creation status.

    Args:
        batch_id: Batch UUID.

    Returns:
        Batch status with created tickets.

    Raises:
        HTTPException: If batch not found.
    """
    if batch_id not in batch_store:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    batch = batch_store[batch_id]

    return TicketBatchResponse(
        batch_id=batch.batch_id,
        prd_id=batch.prd_id,
        project_key=batch.project_key,
        total_count=batch.total_count,
        success_count=batch.success_count,
        failed_count=batch.failed_count,
        success_rate=batch.success_rate,
        status=batch.status,
        created_tickets=[],  # Would populate from batch.created_tickets
        failed_drafts=[],  # Would populate from batch.failed_drafts
        is_complete=batch.is_complete,
        has_failures=batch.has_failures,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
    )
