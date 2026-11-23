"""Admin curriculum DAG, resource catalog, and versioned question routes (FR10–FR12)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.catalog import Question, Resource, Topic, TopicPrerequisite
from app.models.user import User
from app.schemas.catalog import (
    QuestionAdminRead,
    QuestionCreate,
    ResourceCreate,
    ResourceRead,
    TopicCreate,
    TopicRead,
)
from app.services.dag_validator import DAGCycleError, validate_prerequisite_dag

router = APIRouter(
    prefix="/admin",
    tags=["Admin Catalog & DAG"],
    dependencies=[Depends(require_admin)],
)


def _to_topic_read(topic: Topic) -> TopicRead:
    return TopicRead(
        topic_id=topic.topic_id,
        name=topic.name,
        slug=topic.slug,
        description=topic.description,
        display_order=topic.display_order,
        prerequisite_topic_ids=[link.prerequisite_topic_id for link in topic.prerequisite_links],
    )


@router.get("/topics", response_model=list[TopicRead])
def list_admin_topics(db: Annotated[Session, Depends(get_db)]) -> list[TopicRead]:
    stmt = (
        select(Topic)
        .options(selectinload(Topic.prerequisite_links))
        .order_by(Topic.display_order.asc(), Topic.name.asc())
    )
    topics = db.scalars(stmt).all()
    return [_to_topic_read(t) for t in topics]


@router.post("/topics", response_model=TopicRead, status_code=status.HTTP_201_CREATED)
def create_topic(
    payload: TopicCreate,
    db: Annotated[Session, Depends(get_db)],
) -> TopicRead:
    existing_slug = db.scalar(select(Topic).where(Topic.slug == payload.slug))
    if existing_slug is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Topic slug '{payload.slug}' already exists.",
        )

    if payload.prerequisite_topic_ids:
        found_ids = set(
            db.scalars(
                select(Topic.topic_id).where(Topic.topic_id.in_(payload.prerequisite_topic_ids))
            ).all()
        )
        missing = set(payload.prerequisite_topic_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown prerequisite topic IDs: {[str(m) for m in missing]}",
            )

    topic = Topic(
        name=payload.name.strip(),
        slug=payload.slug,
        description=payload.description.strip(),
        display_order=payload.display_order,
    )
    db.add(topic)
    db.flush()

    existing_edges = [
        (edge.topic_id, edge.prerequisite_topic_id)
        for edge in db.scalars(select(TopicPrerequisite)).all()
    ]
    try:
        validate_prerequisite_dag(
            existing_edges=existing_edges,
            target_topic_id=topic.topic_id,
            new_prerequisite_ids=payload.prerequisite_topic_ids,
        )
    except DAGCycleError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    for prereq_id in set(payload.prerequisite_topic_ids):
        db.add(TopicPrerequisite(topic_id=topic.topic_id, prerequisite_topic_id=prereq_id))

    db.commit()
    refreshed = db.scalar(
        select(Topic)
        .options(selectinload(Topic.prerequisite_links))
        .where(Topic.topic_id == topic.topic_id)
    )
    assert refreshed is not None
    return _to_topic_read(refreshed)


@router.get("/resources", response_model=list[ResourceRead])
def list_admin_resources(db: Annotated[Session, Depends(get_db)]) -> list[ResourceRead]:
    resources = db.scalars(select(Resource).order_by(Resource.created_at.desc())).all()
    return [ResourceRead.model_validate(r) for r in resources]


@router.post("/resources", response_model=ResourceRead, status_code=status.HTTP_201_CREATED)
def create_resource(
    payload: ResourceCreate,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ResourceRead:
    url_str = str(payload.external_url)
    existing = db.scalar(select(Resource).where(Resource.external_url == url_str))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Resource URL already exists (resource_id={existing.resource_id}, "
                f"is_active={existing.is_active})."
            ),
        )

    if db.get(Topic, payload.topic_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    resource = Resource(
        topic_id=payload.topic_id,
        created_by=current_admin.user_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        external_url=url_str,
        content_type=payload.content_type.value,
        difficulty=payload.difficulty.value,
        language=payload.language.value,
        estimated_minutes=payload.estimated_minutes,
        is_active=True,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return ResourceRead.model_validate(resource)


@router.get("/questions", response_model=list[QuestionAdminRead])
def list_admin_questions(db: Annotated[Session, Depends(get_db)]) -> list[QuestionAdminRead]:
    questions = db.scalars(select(Question).order_by(Question.created_at.desc())).all()
    return [QuestionAdminRead.model_validate(q) for q in questions]


@router.post("/questions", response_model=QuestionAdminRead, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreate,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> QuestionAdminRead:
    if db.get(Topic, payload.topic_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    question = Question(
        topic_id=payload.topic_id,
        created_by=current_admin.user_id,
        question_text=payload.question_text.strip(),
        code_snippet=payload.code_snippet,
        option_a=payload.option_a.strip(),
        option_b=payload.option_b.strip(),
        option_c=payload.option_c.strip(),
        option_d=payload.option_d.strip(),
        correct_option=payload.correct_option.value,
        explanation=payload.explanation.strip(),
        difficulty=payload.difficulty.value,
        version=1,
        is_active=True,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return QuestionAdminRead.model_validate(question)
