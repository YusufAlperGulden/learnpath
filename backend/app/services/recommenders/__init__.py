"""5-strategy explainable recommendation package."""

from app.services.recommenders.base import (
    BaseRecommender,
    CandidateResource,
    InteractionRecord,
    RankedCandidate,
    StudentRecommendationContext,
)
from app.services.recommenders.cbf import ContentBasedRecommender
from app.services.recommenders.cf import CFPrediction, CollaborativeFilteringRecommender
from app.services.recommenders.hybrid import (
    DEFAULT_VALIDATED_CBF_WEIGHT,
    HybridRankOutcome,
    HybridRecommender,
)
from app.services.recommenders.popularity import (
    PopularityRecommender,
    ResourcePopularityStats,
)
from app.services.recommenders.rule_based import RuleBasedRecommender

__all__ = [
    "DEFAULT_VALIDATED_CBF_WEIGHT",
    "BaseRecommender",
    "CFPrediction",
    "CandidateResource",
    "CollaborativeFilteringRecommender",
    "ContentBasedRecommender",
    "HybridRankOutcome",
    "HybridRecommender",
    "InteractionRecord",
    "PopularityRecommender",
    "RankedCandidate",
    "ResourcePopularityStats",
    "RuleBasedRecommender",
    "StudentRecommendationContext",
]
