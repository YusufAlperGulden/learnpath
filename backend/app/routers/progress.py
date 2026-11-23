"""Dual progress, bookmark, and 1–5 feedback endpoints (FR08–FR09)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_student
from app.models.user import User
from app.schemas.progress import (
    BookmarkCreateRequest,
    BookmarkDetailRead,
    FeedbackRead,
    FeedbackUpsertRequest,
    ResourceProgressRead,
    ResourceProgressUpdateRequest,
    StudyResourceHistoryItem,
    TopicProgressRead,
    TopicProgressToggleRequest,
)
from app.services.progress_service import (
    delete_student_feedback,
    list_student_bookmarks,
    list_student_feedback,
    list_student_resource_history,
    list_student_resource_progress,
    list_student_topic_progress,
    record_resource_open,
    remove_student_bookmark,
    save_student_bookmark,
    set_resource_progress_status,
    toggle_manual_topic_completion,
    upsert_student_feedback,
)

router = APIRouter(
    tags=["Progress, Bookmarks & Feedback"],
    dependencies=[Depends(require_student)],
)


@router.get("/progress/topics", response_model=list[TopicProgressRead])
def list_topic_progress(
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TopicProgressRead]:
    return list_student_topic_progress(db, student_id=current_student.user_id)


@router.put("/progress/topics/{topic_id}", response_model=TopicProgressRead)
def put_topic_manual_completion(
    topic_id: UUID,
    payload: TopicProgressToggleRequest,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> TopicProgressRead:
    return toggle_manual_topic_completion(
        db,
        student_id=current_student.user_id,
        topic_id=topic_id,
        is_manually_completed=payload.is_manually_completed,
    )


@router.get("/progress/resources", response_model=list[ResourceProgressRead])
def list_resource_progress(
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ResourceProgressRead]:
    return list_student_resource_progress(db, student_id=current_student.user_id)


@router.get("/progress/resources/history", response_model=list[StudyResourceHistoryItem])
def list_resource_history(
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> list[StudyResourceHistoryItem]:
    return list_student_resource_history(db, student_id=current_student.user_id)


@router.post("/progress/resources/{resource_id}/open", response_model=ResourceProgressRead)
def post_resource_open(
    resource_id: UUID,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> ResourceProgressRead:
    return record_resource_open(
        db,
        student_id=current_student.user_id,
        resource_id=resource_id,
    )


@router.put("/progress/resources/{resource_id}", response_model=ResourceProgressRead)
def put_resource_progress(
    resource_id: UUID,
    payload: ResourceProgressUpdateRequest,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> ResourceProgressRead:
    return set_resource_progress_status(
        db,
        student_id=current_student.user_id,
        resource_id=resource_id,
        target_status=payload.status,
    )


@router.get("/bookmarks", response_model=list[BookmarkDetailRead])
def list_bookmarks(
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> list[BookmarkDetailRead]:
    return list_student_bookmarks(db, student_id=current_student.user_id)


@router.post(
    "/bookmarks",
    response_model=BookmarkDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def post_bookmark(
    payload: BookmarkCreateRequest,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> BookmarkDetailRead:
    return save_student_bookmark(
        db,
        student_id=current_student.user_id,
        resource_id=payload.resource_id,
    )


@router.delete("/bookmarks/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    resource_id: UUID,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    remove_student_bookmark(
        db,
        student_id=current_student.user_id,
        resource_id=resource_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/feedback", response_model=list[FeedbackRead])
def list_feedback(
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FeedbackRead]:
    return list_student_feedback(db, student_id=current_student.user_id)


@router.post("/feedback", response_model=FeedbackRead)
@router.put("/feedback", response_model=FeedbackRead)
def upsert_feedback(
    payload: FeedbackUpsertRequest,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> FeedbackRead:
    return upsert_student_feedback(
        db,
        student_id=current_student.user_id,
        payload=payload,
    )


@router.delete("/feedback/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_feedback(
    resource_id: UUID,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    delete_student_feedback(
        db,
        student_id=current_student.user_id,
        resource_id=resource_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
