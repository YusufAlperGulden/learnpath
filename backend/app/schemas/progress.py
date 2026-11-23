"""Dual progress, bookmark, and 1–5 feedback Pydantic v2 schemas (FR08–FR09)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    ContentType,
    DifficultyLevel,
    MasteryStatus,
    ResourceProgressStatus,
    SupportedLanguage,
)


class TopicProgressToggleRequest(BaseModel):
    is_manually_completed: bool


class TopicProgressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    topic_id: UUID
    topic_name: str | None = None
    is_manually_completed: bool
    manually_completed_at: datetime | None
    latest_score_percent: float | None
    mastery_status: MasteryStatus
    updated_at: datetime


class ResourceProgressUpdateRequest(BaseModel):
    status: ResourceProgressStatus


class ResourceProgressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    resource_id: UUID
    status: ResourceProgressStatus
    first_opened_at: datetime
    completed_at: datetime | None
    last_accessed_at: datetime


class StudyResourceHistoryItem(BaseModel):
    resource_id: UUID
    topic_id: UUID
    topic_name: str
    title: str
    description: str
    external_url: str
    content_type: ContentType
    difficulty: DifficultyLevel
    language: SupportedLanguage
    estimated_minutes: int | None
    is_active: bool
    status: ResourceProgressStatus
    first_opened_at: datetime
    completed_at: datetime | None
    last_accessed_at: datetime
    is_bookmarked: bool = False
    my_rating: int | None = None
    my_comment: str | None = None


class BookmarkCreateRequest(BaseModel):
    resource_id: UUID


class BookmarkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    resource_id: UUID
    saved_at: datetime


class BookmarkDetailRead(BookmarkRead):
    topic_id: UUID
    topic_name: str
    title: str
    description: str
    external_url: str
    content_type: ContentType
    difficulty: DifficultyLevel
    language: SupportedLanguage
    estimated_minutes: int | None
    is_active: bool
    progress_status: ResourceProgressStatus | None = None
    my_rating: int | None = None
    my_comment: str | None = None


class FeedbackUpsertRequest(BaseModel):
    resource_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feedback_id: UUID
    student_id: UUID
    resource_id: UUID
    rating: int
    comment: str | None
    created_at: datetime
