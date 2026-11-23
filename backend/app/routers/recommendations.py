"""Prerequisite learning path and explainable recommendation contract routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_student
from app.core.enums import MasteryStatus
from app.models.catalog import Topic
from app.models.progress import TopicProgress
from app.models.user import User
from app.schemas.recommendation import (
    LearningPathEdge,
    LearningPathNode,
    LearningPathResponse,
    RecommendationResponse,
    RecommenderStrategy,
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
    topics = db.scalars(
        select(Topic)
        .options(selectinload(Topic.prerequisite_links))
        .order_by(Topic.display_order.asc(), Topic.name.asc())
    ).all()
    progress_rows = db.scalars(
        select(TopicProgress).where(TopicProgress.student_id == current_student.user_id)
    ).all()
    progress_by_topic = {row.topic_id: row for row in progress_rows}

    nodes: list[LearningPathNode] = []
    edges: list[LearningPathEdge] = []
    recommended_next_topic_id = None

    for topic in topics:
        unmet_prereqs = [
            link.prerequisite_topic_id
            for link in topic.prerequisite_links
            if (
                progress_by_topic.get(link.prerequisite_topic_id) is None
                or progress_by_topic[link.prerequisite_topic_id].mastery_status
                != MasteryStatus.MASTERED.value
            )
        ]
        for link in topic.prerequisite_links:
            edges.append(
                LearningPathEdge(
                    prerequisite_topic_id=link.prerequisite_topic_id,
                    topic_id=topic.topic_id,
                )
            )

        prog = progress_by_topic.get(topic.topic_id)
        mastery = (
            MasteryStatus(prog.mastery_status) if prog is not None else MasteryStatus.UNKNOWN
        )
        is_locked = len(unmet_prereqs) > 0

        if (
            recommended_next_topic_id is None
            and not is_locked
            and mastery != MasteryStatus.MASTERED
        ):
            recommended_next_topic_id = topic.topic_id

        nodes.append(
            LearningPathNode(
                topic_id=topic.topic_id,
                name=topic.name,
                slug=topic.slug,
                description=topic.description,
                display_order=topic.display_order,
                is_locked=is_locked,
                unmet_prerequisite_ids=unmet_prereqs,
                is_manually_completed=prog.is_manually_completed if prog is not None else False,
                latest_score_percent=prog.latest_score_percent if prog is not None else None,
                mastery_status=mastery,
            )
        )

    return LearningPathResponse(
        nodes=nodes,
        edges=edges,
        recommended_next_topic_id=recommended_next_topic_id,
    )


@router.get("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    strategy: Annotated[RecommenderStrategy, Query()] = "rule_based",
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> RecommendationResponse:
    _ = limit
    return RecommendationResponse(
        strategy_used=strategy,
        fallback_applied=False,
        fallback_reason=None,
        priority_topics=[],
        items=[],
    )
