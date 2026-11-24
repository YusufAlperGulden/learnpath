"""Prerequisite learning path and explainable recommendation routes (FR05–FR07)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_student
from app.models.user import User
from app.schemas.recommendation import (
    LearningPathResponse,
    RecommendationResponse,
    RecommenderStrategy,
)
from app.services.recommendation_service import (
    compute_learning_path,
    generate_student_recommendations,
)

router = APIRouter(
    tags=["Learning Path & Recommendations"],
    dependencies=[Depends(require_student)],
)


@router.get("/learning-path", response_model=LearningPathResponse)
def get_learning_path(
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> LearningPathResponse:
    """Returns student-accessible curriculum DAG nodes, prerequisite edges, and lock states."""
    return compute_learning_path(db, student_id=current_student.user_id)


@router.get("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    strategy: Annotated[RecommenderStrategy, Query()] = "rule_based",
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    topic_id: Annotated[UUID | None, Query()] = None,
    include_completed: Annotated[bool, Query()] = False,
) -> RecommendationResponse:
    return generate_student_recommendations(
        db,
        student=current_student,
        strategy=strategy,
        limit=limit,
        target_topic_id=topic_id,
        include_completed=include_completed,
    )
