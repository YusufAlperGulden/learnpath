"""Dual progress, bookmark, and 1–5 feedback service logic (FR08–FR09)."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    ContentType,
    DifficultyLevel,
    MasteryStatus,
    ResourceProgressStatus,
    SupportedLanguage,
)
from app.core.logging_config import get_logger
from app.models.catalog import Resource, Topic
from app.models.progress import Feedback, ResourceProgress, SavedResource, TopicProgress
from app.schemas.progress import (
    BookmarkDetailRead,
    FeedbackRead,
    FeedbackUpsertRequest,
    ResourceProgressRead,
    StudyResourceHistoryItem,
    TopicProgressRead,
)

logger = get_logger("progress")


# ---------------------------------------------------------------------------
# 1. Dual Topic Progress (Manual Completion vs Exam Mastery)
# ---------------------------------------------------------------------------


def list_student_topic_progress(db: Session, *, student_id: UUID) -> list[TopicProgressRead]:
    rows = db.scalars(
        select(TopicProgress)
        .options(selectinload(TopicProgress.topic))
        .where(TopicProgress.student_id == student_id)
    ).all()
    rows.sort(key=lambda r: (r.topic.display_order if r.topic else 0, str(r.topic_id)))

    return [
        TopicProgressRead(
            student_id=row.student_id,
            topic_id=row.topic_id,
            topic_name=row.topic.name if row.topic else None,
            is_manually_completed=row.is_manually_completed,
            manually_completed_at=row.manually_completed_at,
            latest_score_percent=row.latest_score_percent,
            mastery_status=MasteryStatus(row.mastery_status),
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def toggle_manual_topic_completion(
    db: Session,
    *,
    student_id: UUID,
    topic_id: UUID,
    is_manually_completed: bool,
) -> TopicProgressRead:
    """Updates self-reported study completion WITHOUT modifying exam mastery_status (FR08)."""
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    now = datetime.now(UTC)
    prog = db.get(TopicProgress, (student_id, topic_id))
    if prog is None:
        prog = TopicProgress(
            student_id=student_id,
            topic_id=topic_id,
            is_manually_completed=is_manually_completed,
            manually_completed_at=now if is_manually_completed else None,
            latest_score_percent=None,
            mastery_status=MasteryStatus.UNKNOWN.value,
            updated_at=now,
        )
        db.add(prog)
    else:
        prog.is_manually_completed = is_manually_completed
        prog.manually_completed_at = now if is_manually_completed else None
        prog.updated_at = now

    db.commit()
    db.refresh(prog)
    logger.info(
        "Updated manual topic completion student_id=%s topic_id=%s completed=%s mastery=%s",
        student_id,
        topic_id,
        prog.is_manually_completed,
        prog.mastery_status,
    )
    return TopicProgressRead(
        student_id=prog.student_id,
        topic_id=prog.topic_id,
        topic_name=topic.name,
        is_manually_completed=prog.is_manually_completed,
        manually_completed_at=prog.manually_completed_at,
        latest_score_percent=prog.latest_score_percent,
        mastery_status=MasteryStatus(prog.mastery_status),
        updated_at=prog.updated_at,
    )


# ---------------------------------------------------------------------------
# 2. Resource Progress (OPENED vs COMPLETED)
# ---------------------------------------------------------------------------


def list_student_resource_progress(
    db: Session,
    *,
    student_id: UUID,
) -> list[ResourceProgressRead]:
    rows = db.scalars(
        select(ResourceProgress)
        .where(ResourceProgress.student_id == student_id)
        .order_by(ResourceProgress.last_accessed_at.desc())
    ).all()
    return [ResourceProgressRead.model_validate(r) for r in rows]


def list_student_resource_history(
    db: Session,
    *,
    student_id: UUID,
) -> list[StudyResourceHistoryItem]:
    rows = db.scalars(
        select(ResourceProgress)
        .options(selectinload(ResourceProgress.resource).selectinload(Resource.topic))
        .where(ResourceProgress.student_id == student_id)
        .order_by(ResourceProgress.last_accessed_at.desc())
    ).all()
    if not rows:
        return []

    r_ids = [r.resource_id for r in rows]
    bookmarked_ids = set(
        db.scalars(
            select(SavedResource.resource_id).where(
                SavedResource.student_id == student_id,
                SavedResource.resource_id.in_(r_ids),
            )
        ).all()
    )
    feedback_by_res = {
        fb.resource_id: fb
        for fb in db.scalars(
            select(Feedback).where(
                Feedback.student_id == student_id,
                Feedback.resource_id.in_(r_ids),
            )
        ).all()
    }

    items: list[StudyResourceHistoryItem] = []
    for row in rows:
        res = row.resource
        fb = feedback_by_res.get(res.resource_id)
        items.append(
            StudyResourceHistoryItem(
                resource_id=res.resource_id,
                topic_id=res.topic_id,
                topic_name=res.topic.name if res.topic else "Topic",
                title=res.title,
                description=res.description,
                external_url=res.external_url,
                content_type=ContentType(res.content_type),
                difficulty=DifficultyLevel(res.difficulty),
                language=SupportedLanguage(res.language),
                estimated_minutes=res.estimated_minutes,
                is_active=res.is_active,
                status=ResourceProgressStatus(row.status),
                first_opened_at=row.first_opened_at,
                completed_at=row.completed_at,
                last_accessed_at=row.last_accessed_at,
                is_bookmarked=res.resource_id in bookmarked_ids,
                my_rating=fb.rating if fb is not None else None,
                my_comment=fb.comment if fb is not None else None,
            )
        )
    return items


def record_resource_open(
    db: Session,
    *,
    student_id: UUID,
    resource_id: UUID,
) -> ResourceProgressRead:
    """Marks a resource OPENED on first click or refreshes last_accessed_at without demoting COMPLETED."""
    if db.get(Resource, resource_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    now = datetime.now(UTC)
    prog = db.get(ResourceProgress, (student_id, resource_id))
    if prog is None:
        prog = ResourceProgress(
            student_id=student_id,
            resource_id=resource_id,
            status=ResourceProgressStatus.OPENED.value,
            first_opened_at=now,
            completed_at=None,
            last_accessed_at=now,
        )
        db.add(prog)
    else:
        prog.last_accessed_at = now

    db.commit()
    db.refresh(prog)
    return ResourceProgressRead.model_validate(prog)


def set_resource_progress_status(
    db: Session,
    *,
    student_id: UUID,
    resource_id: UUID,
    target_status: ResourceProgressStatus,
) -> ResourceProgressRead:
    """Explicitly transitions a resource between OPENED and COMPLETED (FR08)."""
    if db.get(Resource, resource_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    now = datetime.now(UTC)
    prog = db.get(ResourceProgress, (student_id, resource_id))
    if prog is None:
        prog = ResourceProgress(
            student_id=student_id,
            resource_id=resource_id,
            status=target_status.value,
            first_opened_at=now,
            completed_at=now if target_status == ResourceProgressStatus.COMPLETED else None,
            last_accessed_at=now,
        )
        db.add(prog)
    else:
        prog.status = target_status.value
        prog.last_accessed_at = now
        if target_status == ResourceProgressStatus.COMPLETED:
            prog.completed_at = prog.completed_at or now
        else:
            prog.completed_at = None

    db.commit()
    db.refresh(prog)
    logger.info(
        "Updated resource progress student_id=%s resource_id=%s status=%s",
        student_id,
        resource_id,
        prog.status,
    )
    return ResourceProgressRead.model_validate(prog)


# ---------------------------------------------------------------------------
# 3. Saved Resource Bookmarks
# ---------------------------------------------------------------------------


def _build_bookmark_detail(
    saved: SavedResource,
    res: Resource,
    progress_by_res: dict[UUID, ResourceProgress],
    feedback_by_res: dict[UUID, Feedback],
) -> BookmarkDetailRead:
    prog = progress_by_res.get(res.resource_id)
    fb = feedback_by_res.get(res.resource_id)
    return BookmarkDetailRead(
        student_id=saved.student_id,
        resource_id=saved.resource_id,
        saved_at=saved.saved_at,
        topic_id=res.topic_id,
        topic_name=res.topic.name if res.topic else "Topic",
        title=res.title,
        description=res.description,
        external_url=res.external_url,
        content_type=ContentType(res.content_type),
        difficulty=DifficultyLevel(res.difficulty),
        language=SupportedLanguage(res.language),
        estimated_minutes=res.estimated_minutes,
        is_active=res.is_active,
        progress_status=ResourceProgressStatus(prog.status) if prog is not None else None,
        my_rating=fb.rating if fb is not None else None,
        my_comment=fb.comment if fb is not None else None,
    )


def list_student_bookmarks(db: Session, *, student_id: UUID) -> list[BookmarkDetailRead]:
    saved_rows = db.scalars(
        select(SavedResource)
        .options(selectinload(SavedResource.resource).selectinload(Resource.topic))
        .where(SavedResource.student_id == student_id)
        .order_by(SavedResource.saved_at.desc())
    ).all()
    if not saved_rows:
        return []

    r_ids = [s.resource_id for s in saved_rows]
    progress_by_res = {
        p.resource_id: p
        for p in db.scalars(
            select(ResourceProgress).where(
                ResourceProgress.student_id == student_id,
                ResourceProgress.resource_id.in_(r_ids),
            )
        ).all()
    }
    feedback_by_res = {
        fb.resource_id: fb
        for fb in db.scalars(
            select(Feedback).where(
                Feedback.student_id == student_id,
                Feedback.resource_id.in_(r_ids),
            )
        ).all()
    }

    return [
        _build_bookmark_detail(row, row.resource, progress_by_res, feedback_by_res)
        for row in saved_rows
    ]


def save_student_bookmark(
    db: Session,
    *,
    student_id: UUID,
    resource_id: UUID,
) -> BookmarkDetailRead:
    """Idempotently bookmarks `(student_id, resource_id)` without duplicate-PK errors."""
    res = db.scalar(
        select(Resource)
        .options(selectinload(Resource.topic))
        .where(Resource.resource_id == resource_id)
    )
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    saved = db.get(SavedResource, (student_id, resource_id))
    if saved is None:
        saved = SavedResource(
            student_id=student_id,
            resource_id=resource_id,
            saved_at=datetime.now(UTC),
        )
        db.add(saved)
        db.commit()
        db.refresh(saved)
        logger.info("Saved bookmark student_id=%s resource_id=%s", student_id, resource_id)

    prog = db.get(ResourceProgress, (student_id, resource_id))
    fb = db.scalar(
        select(Feedback).where(
            Feedback.student_id == student_id,
            Feedback.resource_id == resource_id,
        )
    )
    return _build_bookmark_detail(
        saved,
        res,
        {resource_id: prog} if prog is not None else {},
        {resource_id: fb} if fb is not None else {},
    )


def remove_student_bookmark(
    db: Session,
    *,
    student_id: UUID,
    resource_id: UUID,
) -> None:
    saved = db.get(SavedResource, (student_id, resource_id))
    if saved is not None:
        db.delete(saved)
        db.commit()
        logger.info("Removed bookmark student_id=%s resource_id=%s", student_id, resource_id)


# ---------------------------------------------------------------------------
# 4. 1–5 Star Feedback & Comments
# ---------------------------------------------------------------------------


def list_student_feedback(db: Session, *, student_id: UUID) -> list[FeedbackRead]:
    rows = db.scalars(
        select(Feedback)
        .where(Feedback.student_id == student_id)
        .order_by(Feedback.created_at.desc())
    ).all()
    return [FeedbackRead.model_validate(r) for r in rows]


def upsert_student_feedback(
    db: Session,
    *,
    student_id: UUID,
    payload: FeedbackUpsertRequest,
) -> FeedbackRead:
    """Creates or updates `(student_id, resource_id)` 1–5 rating and optional comment (FR09)."""
    if db.get(Resource, payload.resource_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    clean_comment = (
        payload.comment.strip() if payload.comment and payload.comment.strip() else None
    )
    now = datetime.now(UTC)

    existing = db.scalar(
        select(Feedback).where(
            Feedback.student_id == student_id,
            Feedback.resource_id == payload.resource_id,
        )
    )
    if existing is None:
        existing = Feedback(
            student_id=student_id,
            resource_id=payload.resource_id,
            rating=payload.rating,
            comment=clean_comment,
            created_at=now,
        )
        db.add(existing)
    else:
        existing.rating = payload.rating
        existing.comment = clean_comment
        existing.created_at = now

    db.commit()
    db.refresh(existing)
    logger.info(
        "Upserted resource feedback student_id=%s resource_id=%s rating=%d",
        student_id,
        payload.resource_id,
        existing.rating,
    )
    return FeedbackRead.model_validate(existing)


def delete_student_feedback(
    db: Session,
    *,
    student_id: UUID,
    resource_id: UUID,
) -> None:
    existing = db.scalar(
        select(Feedback).where(
            Feedback.student_id == student_id,
            Feedback.resource_id == resource_id,
        )
    )
    if existing is not None:
        db.delete(existing)
        db.commit()
        logger.info("Deleted feedback student_id=%s resource_id=%s", student_id, resource_id)
