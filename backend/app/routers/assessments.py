"""Assessment contract routes scheduled for full engine implementation in Increment 3."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import require_student
from app.core.enums import TestType
from app.models.user import User
from app.schemas.assessment import (
    AssessmentAttemptDetailResponse,
    AssessmentAttemptSummary,
    AssessmentQuestionsResponse,
    AssessmentSubmitRequest,
)

router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"],
    dependencies=[Depends(require_student)],
)


@router.get("/questions", response_model=AssessmentQuestionsResponse)
def get_assessment_questions(
    current_student: Annotated[User, Depends(require_student)],
    test_type: Annotated[TestType, Query()] = TestType.DIAGNOSTIC,
    target_topic_id: Annotated[UUID | None, Query()] = None,
) -> AssessmentQuestionsResponse:
    _ = (current_student, test_type, target_topic_id)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Assessment question selector is scheduled for Increment 3.",
    )


@router.post("/submit", response_model=AssessmentAttemptDetailResponse)
def submit_assessment(
    payload: AssessmentSubmitRequest,
    current_student: Annotated[User, Depends(require_student)],
) -> AssessmentAttemptDetailResponse:
    _ = (payload, current_student)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Atomic assessment submission service is scheduled for Increment 3.",
    )


@router.get("/attempts", response_model=list[AssessmentAttemptSummary])
def list_attempts() -> list[AssessmentAttemptSummary]:
    return []
