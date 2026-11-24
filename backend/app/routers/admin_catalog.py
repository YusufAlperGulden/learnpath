"""Admin curriculum DAG, resource catalog CRUD, soft-deactivation, and question versioning (FR10–FR12)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.enums import ContentType, DifficultyLevel, SupportedLanguage
from app.core.logging_config import get_logger
from app.models.assessment import Answer, TestAttempt, TopicScore
from app.models.catalog import Question, Resource, Topic, TopicPrerequisite
from app.models.user import User
from app.schemas.catalog import (
    ActiveStatusPatch,
    QuestionAdminRead,
    QuestionCreate,
    QuestionUpdate,
    ResourceCreate,
    ResourceRead,
    ResourceUpdate,
    TopicCreate,
    TopicRead,
    TopicUpdate,
)
from app.services.dag_validator import (
    DAGCycleError,
    apply_question_update,
    is_question_answered,
    notify_catalog_changed,
    validate_prerequisite_dag,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin Catalog & DAG"],
    dependencies=[Depends(require_admin)],
)
logger = get_logger("admin_catalog")


def _load_topic_counts(
    db: Session,
) -> tuple[dict[UUID, int], dict[UUID, int]]:
    res_counts = dict(
        db.execute(
            select(Resource.topic_id, func.count(Resource.resource_id))
            .where(Resource.is_active.is_(True))
            .group_by(Resource.topic_id)
        ).all()
    )
    q_counts = dict(
        db.execute(
            select(Question.topic_id, func.count(Question.question_id))
            .where(Question.is_active.is_(True))
            .group_by(Question.topic_id)
        ).all()
    )
    return res_counts, q_counts


def _to_topic_read(
    topic: Topic,
    res_counts: dict[UUID, int] | None = None,
    q_counts: dict[UUID, int] | None = None,
) -> TopicRead:
    return TopicRead(
        topic_id=topic.topic_id,
        name=topic.name,
        slug=topic.slug,
        description=topic.description,
        display_order=topic.display_order,
        prerequisite_topic_ids=[link.prerequisite_topic_id for link in topic.prerequisite_links],
        active_resource_count=(res_counts or {}).get(topic.topic_id, 0),
        active_question_count=(q_counts or {}).get(topic.topic_id, 0),
    )


def _to_resource_read(resource: Resource, topic_name: str | None = None) -> ResourceRead:
    resolved_topic_name = topic_name
    if resolved_topic_name is None and "topic" in resource.__dict__ and resource.topic is not None:
        resolved_topic_name = resource.topic.name

    return ResourceRead(
        resource_id=resource.resource_id,
        topic_id=resource.topic_id,
        topic_name=resolved_topic_name,
        created_by=resource.created_by,
        title=resource.title,
        description=resource.description,
        external_url=resource.external_url,
        content_type=ContentType(resource.content_type),
        difficulty=DifficultyLevel(resource.difficulty),
        language=SupportedLanguage(resource.language),
        estimated_minutes=resource.estimated_minutes,
        is_active=resource.is_active,
        created_at=resource.created_at,
    )


def _to_question_read(
    question: Question,
    *,
    is_answered: bool,
    topic_name: str | None = None,
) -> QuestionAdminRead:
    resolved_topic_name = topic_name
    if resolved_topic_name is None and "topic" in question.__dict__ and question.topic is not None:
        resolved_topic_name = question.topic.name

    return QuestionAdminRead(
        question_id=question.question_id,
        topic_id=question.topic_id,
        topic_name=resolved_topic_name,
        created_by=question.created_by,
        question_text=question.question_text,
        code_snippet=question.code_snippet,
        option_a=question.option_a,
        option_b=question.option_b,
        option_c=question.option_c,
        option_d=question.option_d,
        correct_option=question.correct_option,  # type: ignore[arg-type]
        explanation=question.explanation,
        difficulty=DifficultyLevel(question.difficulty),
        version=question.version,
        previous_question_id=question.previous_question_id,
        is_active=question.is_active,
        is_answered=is_answered,
        created_at=question.created_at,
    )


def _validate_prerequisite_ids_exist(db: Session, prereq_ids: list[UUID]) -> None:
    if not prereq_ids:
        return
    found_ids = set(
        db.scalars(select(Topic.topic_id).where(Topic.topic_id.in_(prereq_ids))).all()
    )
    missing = set(prereq_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown prerequisite topic IDs: {[str(m) for m in sorted(missing, key=str)]}",
        )


# ---------------------------------------------------------------------------
# 1. Topics & Prerequisite DAG (/api/v1/admin/topics)
# ---------------------------------------------------------------------------


@router.get("/topics", response_model=list[TopicRead])
def list_admin_topics(db: Annotated[Session, Depends(get_db)]) -> list[TopicRead]:
    stmt = (
        select(Topic)
        .options(selectinload(Topic.prerequisite_links))
        .order_by(Topic.display_order.asc(), Topic.name.asc())
    )
    topics = db.scalars(stmt).all()
    res_counts, q_counts = _load_topic_counts(db)
    return [_to_topic_read(t, res_counts, q_counts) for t in topics]


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

    _validate_prerequisite_ids_exist(db, payload.prerequisite_topic_ids)

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
    notify_catalog_changed()
    logger.info("Created topic slug=%s topic_id=%s", topic.slug, topic.topic_id)
    refreshed = db.scalar(
        select(Topic)
        .options(selectinload(Topic.prerequisite_links))
        .where(Topic.topic_id == topic.topic_id)
    )
    assert refreshed is not None
    res_counts, q_counts = _load_topic_counts(db)
    return _to_topic_read(refreshed, res_counts, q_counts)


@router.put("/topics/{topic_id}", response_model=TopicRead)
def update_topic(
    topic_id: UUID,
    payload: TopicUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> TopicRead:
    topic = db.scalar(
        select(Topic)
        .options(selectinload(Topic.prerequisite_links))
        .where(Topic.topic_id == topic_id)
    )
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    if payload.slug is not None and payload.slug != topic.slug:
        conflict = db.scalar(select(Topic).where(Topic.slug == payload.slug))
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Topic slug '{payload.slug}' already exists.",
            )
        topic.slug = payload.slug

    if payload.name is not None:
        topic.name = payload.name.strip()
    if payload.description is not None:
        topic.description = payload.description.strip()
    if payload.display_order is not None:
        topic.display_order = payload.display_order

    if payload.prerequisite_topic_ids is not None:
        _validate_prerequisite_ids_exist(db, payload.prerequisite_topic_ids)
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

        topic.prerequisite_links.clear()
        db.flush()
        for prereq_id in set(payload.prerequisite_topic_ids):
            topic.prerequisite_links.append(
                TopicPrerequisite(topic_id=topic.topic_id, prerequisite_topic_id=prereq_id)
            )

    db.commit()
    notify_catalog_changed()
    logger.info("Updated topic topic_id=%s slug=%s", topic.topic_id, topic.slug)

    refreshed = db.scalar(
        select(Topic)
        .options(selectinload(Topic.prerequisite_links))
        .where(Topic.topic_id == topic_id)
    )
    assert refreshed is not None
    res_counts, q_counts = _load_topic_counts(db)
    return _to_topic_read(refreshed, res_counts, q_counts)


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(
    topic_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    has_dependents = db.scalar(
        select(func.count())
        .select_from(TopicPrerequisite)
        .where(TopicPrerequisite.prerequisite_topic_id == topic_id)
    )
    has_resources = db.scalar(
        select(func.count()).select_from(Resource).where(Resource.topic_id == topic_id)
    )
    has_questions = db.scalar(
        select(func.count()).select_from(Question).where(Question.topic_id == topic_id)
    )
    has_attempts = db.scalar(
        select(func.count())
        .select_from(TestAttempt)
        .where(TestAttempt.target_topic_id == topic_id)
    )
    has_scores = db.scalar(
        select(func.count()).select_from(TopicScore).where(TopicScore.topic_id == topic_id)
    )

    if any(c and c > 0 for c in (has_dependents, has_resources, has_questions, has_attempts, has_scores)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot delete a topic that is referenced by dependent topics, resources, "
                "questions, or exam history."
            ),
        )

    db.delete(topic)
    db.commit()
    notify_catalog_changed()
    logger.info("Deleted unreferenced topic topic_id=%s", topic_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 2. Resources Catalog & Soft-Deactivation (/api/v1/admin/resources)
# ---------------------------------------------------------------------------


@router.get("/resources", response_model=list[ResourceRead])
def list_admin_resources(
    db: Annotated[Session, Depends(get_db)],
    topic_id: Annotated[UUID | None, Query()] = None,
    content_type: Annotated[ContentType | None, Query()] = None,
    difficulty: Annotated[DifficultyLevel | None, Query()] = None,
    language: Annotated[SupportedLanguage | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> list[ResourceRead]:
    stmt = select(Resource).options(selectinload(Resource.topic))
    if topic_id is not None:
        stmt = stmt.where(Resource.topic_id == topic_id)
    if content_type is not None:
        stmt = stmt.where(Resource.content_type == content_type.value)
    if difficulty is not None:
        stmt = stmt.where(Resource.difficulty == difficulty.value)
    if language is not None:
        stmt = stmt.where(Resource.language == language.value)
    if is_active is not None:
        stmt = stmt.where(Resource.is_active.is_(is_active))
    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Resource.title).like(pattern),
                func.lower(Resource.description).like(pattern),
                func.lower(Resource.external_url).like(pattern),
            )
        )

    stmt = stmt.order_by(Resource.is_active.desc(), Resource.created_at.desc())
    resources = db.scalars(stmt).all()
    return [_to_resource_read(r) for r in resources]


@router.post("/resources", response_model=ResourceRead, status_code=status.HTTP_201_CREATED)
def create_resource(
    payload: ResourceCreate,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ResourceRead:
    url_str = str(payload.external_url)
    existing = db.scalar(select(Resource).where(Resource.external_url == url_str))
    if existing is not None:
        state_label = "active" if existing.is_active else "inactive"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Duplicate URL: '{existing.title}' already uses this external_url "
                f"(resource_id={existing.resource_id}, status={state_label})."
            ),
        )

    topic = db.get(Topic, payload.topic_id)
    if topic is None:
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
    notify_catalog_changed()
    logger.info("Created resource resource_id=%s topic_id=%s", resource.resource_id, topic.topic_id)
    return _to_resource_read(resource, topic_name=topic.name)


@router.put("/resources/{resource_id}", response_model=ResourceRead)
def update_resource(
    resource_id: UUID,
    payload: ResourceUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ResourceRead:
    resource = db.scalar(
        select(Resource).options(selectinload(Resource.topic)).where(Resource.resource_id == resource_id)
    )
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    fields_set = payload.model_fields_set

    if "topic_id" in fields_set and payload.topic_id is not None:
        new_topic = db.get(Topic, payload.topic_id)
        if new_topic is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")
        resource.topic_id = payload.topic_id
        resource.topic = new_topic

    if "external_url" in fields_set and payload.external_url is not None:
        url_str = str(payload.external_url)
        if url_str != resource.external_url:
            conflict = db.scalar(
                select(Resource).where(
                    Resource.external_url == url_str,
                    Resource.resource_id != resource_id,
                )
            )
            if conflict is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Duplicate URL: '{conflict.title}' already uses this external_url "
                        f"(resource_id={conflict.resource_id})."
                    ),
                )
            resource.external_url = url_str

    if "title" in fields_set and payload.title is not None:
        resource.title = payload.title.strip()
    if "description" in fields_set and payload.description is not None:
        resource.description = payload.description.strip()
    if "content_type" in fields_set and payload.content_type is not None:
        resource.content_type = payload.content_type.value
    if "difficulty" in fields_set and payload.difficulty is not None:
        resource.difficulty = payload.difficulty.value
    if "language" in fields_set and payload.language is not None:
        resource.language = payload.language.value
    if "estimated_minutes" in fields_set:
        resource.estimated_minutes = payload.estimated_minutes
    if "is_active" in fields_set and payload.is_active is not None:
        resource.is_active = payload.is_active

    db.commit()
    db.refresh(resource)
    notify_catalog_changed()
    topic = db.get(Topic, resource.topic_id)
    logger.info(
        "Updated resource resource_id=%s is_active=%s",
        resource.resource_id,
        resource.is_active,
    )
    return _to_resource_read(resource, topic_name=topic.name if topic else None)


@router.patch("/resources/{resource_id}/status", response_model=ResourceRead)
def patch_resource_status(
    resource_id: UUID,
    payload: ActiveStatusPatch,
    db: Annotated[Session, Depends(get_db)],
) -> ResourceRead:
    resource = db.scalar(
        select(Resource).options(selectinload(Resource.topic)).where(Resource.resource_id == resource_id)
    )
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    resource.is_active = payload.is_active
    db.commit()
    db.refresh(resource)
    notify_catalog_changed()
    topic = db.get(Topic, resource.topic_id)
    logger.info(
        "Toggled resource status resource_id=%s is_active=%s",
        resource.resource_id,
        resource.is_active,
    )
    return _to_resource_read(resource, topic_name=topic.name if topic else None)


@router.delete("/resources/{resource_id}", response_model=ResourceRead)
def soft_deactivate_resource(
    resource_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ResourceRead:
    """Soft-deactivates a resource (`is_active=False`) instead of deleting historical FK rows (FR10)."""
    resource = db.scalar(
        select(Resource).options(selectinload(Resource.topic)).where(Resource.resource_id == resource_id)
    )
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    resource.is_active = False
    db.commit()
    db.refresh(resource)
    notify_catalog_changed()
    topic = db.get(Topic, resource.topic_id)
    logger.info("Soft-deactivated resource resource_id=%s", resource.resource_id)
    return _to_resource_read(resource, topic_name=topic.name if topic else None)


# ---------------------------------------------------------------------------
# 3. Versioned Question Bank (/api/v1/admin/questions)
# ---------------------------------------------------------------------------


@router.get("/questions", response_model=list[QuestionAdminRead])
def list_admin_questions(
    db: Annotated[Session, Depends(get_db)],
    topic_id: Annotated[UUID | None, Query()] = None,
    difficulty: Annotated[DifficultyLevel | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> list[QuestionAdminRead]:
    stmt = select(Question).options(selectinload(Question.topic))
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty.value)
    if is_active is not None:
        stmt = stmt.where(Question.is_active.is_(is_active))
    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Question.question_text).like(pattern),
                func.lower(Question.explanation).like(pattern),
            )
        )

    stmt = stmt.order_by(Question.is_active.desc(), Question.created_at.desc())
    questions = db.scalars(stmt).all()
    if not questions:
        return []

    q_ids = [q.question_id for q in questions]
    answered_ids = set(
        db.scalars(select(Answer.question_id).where(Answer.question_id.in_(q_ids)).distinct()).all()
    )

    return [
        _to_question_read(q, is_answered=(q.question_id in answered_ids))
        for q in questions
    ]


@router.post("/questions", response_model=QuestionAdminRead, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreate,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> QuestionAdminRead:
    topic = db.get(Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    snippet = (
        payload.code_snippet
        if payload.code_snippet and payload.code_snippet.strip()
        else None
    )
    question = Question(
        topic_id=payload.topic_id,
        created_by=current_admin.user_id,
        question_text=payload.question_text.strip(),
        code_snippet=snippet,
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
    logger.info("Created question question_id=%s topic_id=%s", question.question_id, topic.topic_id)
    return _to_question_read(question, is_answered=False, topic_name=topic.name)


@router.put("/questions/{question_id}", response_model=QuestionAdminRead)
def update_question(
    question_id: UUID,
    payload: QuestionUpdate,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> QuestionAdminRead:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    if (
        "topic_id" in payload.model_fields_set
        and payload.topic_id is not None
        and db.get(Topic, payload.topic_id) is None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    updated_question, versioned = apply_question_update(
        db=db,
        question=question,
        payload=payload,
        admin_user_id=current_admin.user_id,
    )
    db.commit()
    db.refresh(updated_question)
    topic = db.get(Topic, updated_question.topic_id)

    if versioned:
        logger.info(
            "Versioned answered question old_id=%s -> new_id=%s version=%d",
            question_id,
            updated_question.question_id,
            updated_question.version,
        )
    else:
        logger.info("Updated question in-place question_id=%s", updated_question.question_id)

    answered = is_question_answered(db, updated_question.question_id)
    return _to_question_read(
        updated_question,
        is_answered=answered,
        topic_name=topic.name if topic else None,
    )


@router.patch("/questions/{question_id}/status", response_model=QuestionAdminRead)
def patch_question_status(
    question_id: UUID,
    payload: ActiveStatusPatch,
    db: Annotated[Session, Depends(get_db)],
) -> QuestionAdminRead:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    question.is_active = payload.is_active
    db.commit()
    db.refresh(question)
    topic = db.get(Topic, question.topic_id)
    answered = is_question_answered(db, question.question_id)
    logger.info(
        "Toggled question status question_id=%s is_active=%s",
        question.question_id,
        question.is_active,
    )
    return _to_question_read(
        question,
        is_answered=answered,
        topic_name=topic.name if topic else None,
    )


@router.delete("/questions/{question_id}", response_model=QuestionAdminRead)
def soft_deactivate_question(
    question_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> QuestionAdminRead:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    question.is_active = False
    db.commit()
    db.refresh(question)
    topic = db.get(Topic, question.topic_id)
    answered = is_question_answered(db, question.question_id)
    logger.info("Soft-deactivated question question_id=%s", question.question_id)
    return _to_question_read(
        question,
        is_answered=answered,
        topic_name=topic.name if topic else None,
    )


@router.get("/questions/{question_id}/lineage", response_model=list[QuestionAdminRead])
def get_question_lineage(
    question_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[QuestionAdminRead]:
    """Returns the chronological version chain (v1 -> ... -> latest) containing `question_id`."""
    target = db.get(Question, question_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    # Walk backwards to root v1
    chain_back: list[Question] = [target]
    visited: set[UUID] = {target.question_id}
    curr = target
    while curr.previous_question_id is not None and curr.previous_question_id not in visited:
        prev = db.get(Question, curr.previous_question_id)
        if prev is None:
            break
        chain_back.append(prev)
        visited.add(prev.question_id)
        curr = prev

    chain = list(reversed(chain_back))

    # Walk forward from target to any newer descendants
    frontier = target
    while True:
        nxt = db.scalar(
            select(Question)
            .where(Question.previous_question_id == frontier.question_id)
            .order_by(Question.version.desc())
        )
        if nxt is None or nxt.question_id in visited:
            break
        chain.append(nxt)
        visited.add(nxt.question_id)
        frontier = nxt

    q_ids = [q.question_id for q in chain]
    answered_ids = set(
        db.scalars(select(Answer.question_id).where(Answer.question_id.in_(q_ids)).distinct()).all()
    )
    topics_by_id = {
        t.topic_id: t.name
        for t in db.scalars(select(Topic).where(Topic.topic_id.in_({q.topic_id for q in chain}))).all()
    }

    return [
        _to_question_read(
            q,
            is_answered=(q.question_id in answered_ids),
            topic_name=topics_by_id.get(q.topic_id),
        )
        for q in chain
    ]
