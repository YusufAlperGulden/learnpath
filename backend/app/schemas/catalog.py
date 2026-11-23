"""Admin curriculum DAG, resource catalog, and versioned question schemas (FR10–FR12)."""

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.core.enums import AnswerOption, ContentType, DifficultyLevel, SupportedLanguage


class ActiveStatusPatch(BaseModel):
    is_active: bool


class TopicCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    slug: str = Field(min_length=2, max_length=150, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(min_length=5)
    display_order: int = Field(default=0, ge=0)
    prerequisite_topic_ids: list[UUID] = Field(default_factory=list)


class TopicUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    description: str | None = Field(default=None, min_length=5)
    display_order: int | None = Field(default=None, ge=0)
    prerequisite_topic_ids: list[UUID] | None = None


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: UUID
    name: str
    slug: str
    description: str
    display_order: int
    prerequisite_topic_ids: list[UUID] = Field(default_factory=list)
    active_resource_count: int = 0
    active_question_count: int = 0


class ResourceCreate(BaseModel):
    topic_id: UUID
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10)
    external_url: AnyHttpUrl
    content_type: ContentType
    difficulty: DifficultyLevel
    language: SupportedLanguage = SupportedLanguage.EN
    estimated_minutes: int | None = Field(default=None, gt=0, le=600)


class ResourceUpdate(BaseModel):
    topic_id: UUID | None = None
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    external_url: AnyHttpUrl | None = None
    content_type: ContentType | None = None
    difficulty: DifficultyLevel | None = None
    language: SupportedLanguage | None = None
    estimated_minutes: int | None = Field(default=None, gt=0, le=600)
    is_active: bool | None = None


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resource_id: UUID
    topic_id: UUID
    topic_name: str | None = None
    created_by: UUID
    title: str
    description: str
    external_url: str
    content_type: ContentType
    difficulty: DifficultyLevel
    language: SupportedLanguage
    estimated_minutes: int | None
    is_active: bool
    created_at: datetime


class QuestionCreate(BaseModel):
    topic_id: UUID
    question_text: str = Field(min_length=5)
    code_snippet: str | None = None
    option_a: str = Field(min_length=1)
    option_b: str = Field(min_length=1)
    option_c: str = Field(min_length=1)
    option_d: str = Field(min_length=1)
    correct_option: AnswerOption
    explanation: str = Field(min_length=5)
    difficulty: DifficultyLevel


class QuestionUpdate(BaseModel):
    topic_id: UUID | None = None
    question_text: str | None = Field(default=None, min_length=5)
    code_snippet: str | None = None
    option_a: str | None = Field(default=None, min_length=1)
    option_b: str | None = Field(default=None, min_length=1)
    option_c: str | None = Field(default=None, min_length=1)
    option_d: str | None = Field(default=None, min_length=1)
    correct_option: AnswerOption | None = None
    explanation: str | None = Field(default=None, min_length=5)
    difficulty: DifficultyLevel | None = None
    is_active: bool | None = None


class QuestionAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: UUID
    topic_id: UUID
    topic_name: str | None = None
    created_by: UUID
    question_text: str
    code_snippet: str | None
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: AnswerOption
    explanation: str
    difficulty: DifficultyLevel
    version: int
    previous_question_id: UUID | None
    is_active: bool
    is_answered: bool = False
    created_at: datetime
