"""Dual progress, bookmark, and feedback contract routes (Increment 4)."""

from fastapi import APIRouter, Depends

from app.core.deps import require_student
from app.schemas.progress import BookmarkRead, ResourceProgressRead, TopicProgressRead

router = APIRouter(
    tags=["Progress, Bookmarks & Feedback"],
    dependencies=[Depends(require_student)],
)


@router.get("/progress/topics", response_model=list[TopicProgressRead])
def list_topic_progress() -> list[TopicProgressRead]:
    return []


@router.get("/progress/resources", response_model=list[ResourceProgressRead])
def list_resource_progress() -> list[ResourceProgressRead]:
    return []


@router.get("/bookmarks", response_model=list[BookmarkRead])
def list_bookmarks() -> list[BookmarkRead]:
    return []
