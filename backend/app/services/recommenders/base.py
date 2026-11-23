"""Shared candidate, context, and base ranker interface for all 5 recommendation strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from app.core.enums import (
    ContentType,
    DifficultyLevel,
    ExperienceLevel,
    MasteryStatus,
    SupportedLanguage,
)


@dataclass(frozen=True, slots=True)
class CandidateResource:
    resource_id: UUID
    topic_id: UUID
    topic_name: str
    topic_display_order: int
    title: str
    description: str
    external_url: str
    content_type: ContentType
    difficulty: DifficultyLevel
    language: SupportedLanguage
    estimated_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class StudentRecommendationContext:
    student_id: UUID
    experience_level: ExperienceLevel
    preferred_formats: tuple[ContentType, ...]
    preferred_language: SupportedLanguage
    learning_goal: str
    topic_scores: dict[UUID, float] = field(default_factory=dict)
    topic_mastery: dict[UUID, MasteryStatus] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    candidate: CandidateResource
    score: float
    rationale: str
    format_fallback_used: bool = False


class BaseRecommender(ABC):
    strategy_name: str

    @abstractmethod
    def rank(
        self,
        candidates: list[CandidateResource],
        context: StudentRecommendationContext,
        limit: int = 5,
    ) -> list[RankedCandidate]:
        """Ranks eligible unseen candidates and attaches truthful human-readable rationales."""
