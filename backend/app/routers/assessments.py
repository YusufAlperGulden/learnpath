"""Assessment routes: stateless question delivery, atomic submission, and attempt review (FR03–FR04)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_student
from app.core.enums import TestType
from app.models.user import User
from app.schemas.assessment import (
    AssessmentAttemptDetailResponse,
    AssessmentAttemptSummary,
    AssessmentQuestionsResponse,
    AssessmentSubmitRequest,
)
from app.services.assessment_service import (
    get_student_attempt_detail,
    list_student_attempts,
    prepare_assessment_questions,
    submit_assessment_atomic,
)

router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"],
    dependencies=[Depends(require_student)],
)


@router.get("/questions", response_model=AssessmentQuestionsResponse)
def get_assessment_questions(
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    test_type: Annotated[TestType, Query()] = TestType.DIAGNOSTIC,
    target_topic_id: Annotated[UUID | None, Query()] = None,
) -> AssessmentQuestionsResponse:
    return prepare_assessment_questions(
        db,
        student_id=current_student.user_id,
        test_type=test_type,
        target_topic_id=target_topic_id,
    )


@router.post("/submit", response_model=AssessmentAttemptDetailResponse)
def submit_assessment(
    payload: AssessmentSubmitRequest,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> AssessmentAttemptDetailResponse:
    return submit_assessment_atomic(
        db,
        student_id=current_student.user_id,
        payload=payload,
    )


@router.get("/attempts", response_model=list[AssessmentAttemptSummary])
def list_attempts(
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> list[AssessmentAttemptSummary]:
    return list_student_attempts(db, student_id=current_student.user_id)


@router.get("/attempts/{attempt_id}", response_model=AssessmentAttemptDetailResponse)
def get_attempt_detail(
    attempt_id: UUID,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> AssessmentAttemptDetailResponse:
    return get_student_attempt_detail(
        db,
        student_id=current_student.user_id,
        attempt_id=attempt_id,
    )
