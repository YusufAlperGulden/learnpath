"""Learning path DAG and explainable recommendation contracts (FR05–FR07, Section 3.3)."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import (
    ContentType,
    DifficultyLevel,
    MasteryStatus,
    SupportedLanguage,
)

RecommenderStrategy = Literal["rule_based", "popularity", "cbf", "cf", "hybrid"]


class LearningPathNode(BaseModel):
    topic_id: UUID
    name: str
    slug: str
    description: str
    display_order: int
    is_locked: bool
    unmet_prerequisite_ids: list[UUID] = Field(default_factory=list)
    is_manually_completed: bool = False
    latest_score_percent: float | None = None
    mastery_status: MasteryStatus = MasteryStatus.UNKNOWN


class LearningPathEdge(BaseModel):
    prerequisite_topic_id: UUID
    topic_id: UUID


class LearningPathResponse(BaseModel):
    nodes: list[LearningPathNode]
    edges: list[LearningPathEdge]
    recommended_next_topic_id: UUID | None = None


class PriorityTopicSummary(BaseModel):
    topic_id: UUID
    name: str
    score_percent: float | None
    mastery_status: MasteryStatus


class RecommendedResourceItem(BaseModel):
    resource_id: UUID
    title: str
    description: str
    external_url: str
    content_type: ContentType
    difficulty: DifficultyLevel
    language: SupportedLanguage
    estimated_minutes: int | None = None
    topic_id: UUID
    topic_name: str
    rank: int = Field(ge=1)
    score: float | None = None
    format_fallback_used: bool = False
    rationale: str


class RecommendationResponse(BaseModel):
    strategy_used: RecommenderStrategy
    fallback_applied: bool
    fallback_reason: str | None = None
    priority_topics: list[PriorityTopicSummary]
    items: list[RecommendedResourceItem]
