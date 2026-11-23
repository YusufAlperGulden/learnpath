"""Student profile Pydantic v2 schemas supporting multi-format selection (FR02)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import ContentType, ExperienceLevel, SupportedLanguage


class StudentProfileUpsert(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    learning_goal: str = Field(min_length=2, max_length=255)
    experience_level: ExperienceLevel
    preferred_formats: list[ContentType] = Field(min_length=1)
    preferred_language: SupportedLanguage = SupportedLanguage.EN

    @field_validator("preferred_formats")
    @classmethod
    def deduplicate_formats(cls, value: list[ContentType]) -> list[ContentType]:
        seen: list[ContentType] = []
        for item in value:
            if item not in seen:
                seen.append(item)
        if not seen:
            raise ValueError("preferred_formats must contain at least one format.")
        return seen


class StudentProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    display_name: str
    learning_goal: str
    experience_level: ExperienceLevel
    preferred_formats: list[ContentType]
    preferred_language: SupportedLanguage
    updated_at: datetime
