"""Popularity Baseline Recommender (RAD Section 2.4 — deterministic resource_id tie-break)."""

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.services.recommenders.base import (
    BaseRecommender,
    CandidateResource,
    InteractionRecord,
    RankedCandidate,
    StudentRecommendationContext,
)


@dataclass(frozen=True, slots=True)
class ResourcePopularityStats:
    rating_count: int
    positive_count: int
    mean_rating: float
    normalized_score: float


class PopularityRecommender(BaseRecommender):
    """Non-personalized empirical popularity baseline fitted strictly on training feedback.

    Ranks unseen eligible candidates by Bayesian-damped rating quality + positive vote volume,
    breaking exact ties deterministically by `str(resource_id)` ascending (RAD v2.0).
    """

    strategy_name = "popularity"

    def __init__(self, damping_m: float = 3.0) -> None:
        self.damping_m = damping_m
        self._stats_by_resource: dict[UUID, ResourcePopularityStats] = {}
        self._global_mean: float = 3.5

    def fit(self, interactions: Sequence[InteractionRecord]) -> "PopularityRecommender":
        self._stats_by_resource.clear()
        if not interactions:
            self._global_mean = 3.5
            return self

        ratings_by_res: dict[UUID, list[float]] = defaultdict(list)
        total_sum = 0.0
        for rec in interactions:
            ratings_by_res[rec.resource_id].append(float(rec.rating))
            total_sum += float(rec.rating)

        self._global_mean = total_sum / len(interactions)

        for res_id, values in ratings_by_res.items():
            cnt = len(values)
            pos_cnt = sum(1 for v in values if v >= 4.0)
            mean_val = sum(values) / cnt
            bayesian = (cnt * mean_val + self.damping_m * self._global_mean) / (
                cnt + self.damping_m
            )
            # Map [1..5] -> [0..1] with a bounded positive-engagement volume bonus
            quality_norm = max(0.0, min(1.0, (bayesian - 1.0) / 4.0))
            volume_bonus = min(0.15, 0.04 * math.log1p(pos_cnt))
            norm_score = round(min(1.0, quality_norm * 0.85 + volume_bonus), 6)
            self._stats_by_resource[res_id] = ResourcePopularityStats(
                rating_count=cnt,
                positive_count=pos_cnt,
                mean_rating=round(mean_val, 2),
                normalized_score=norm_score,
            )

        return self

    def score_candidate(self, resource_id: UUID) -> tuple[float, ResourcePopularityStats | None]:
        stats = self._stats_by_resource.get(resource_id)
        if stats is None:
            return 0.0, None
        return stats.normalized_score, stats

    def rank(
        self,
        candidates: list[CandidateResource],
        context: StudentRecommendationContext,
        limit: int = 5,
    ) -> list[RankedCandidate]:
        if not candidates or limit <= 0:
            return []

        preferred_set = set(context.preferred_formats)
        scored: list[tuple[tuple[float, str], RankedCandidate]] = []

        for cand in candidates:
            pop_score, stats = self.score_candidate(cand.resource_id)
            format_fallback = cand.content_type not in preferred_set

            if stats is not None and stats.rating_count > 0:
                rationale = (
                    f"Ranked by catalog popularity in {cand.topic_name}: "
                    f"{stats.mean_rating:.1f}/5 average rating across {stats.rating_count} "
                    f"student evaluations ({stats.positive_count} positive)."
                )
            else:
                rationale = (
                    f"Included from the {cand.topic_name} baseline catalog "
                    f"(no historical ratings recorded yet)."
                )

            item = RankedCandidate(
                candidate=cand,
                score=pop_score,
                rationale=rationale,
                format_fallback_used=format_fallback,
            )
            # Deterministic resource_id tie-break mandated by RAD v2.0 Section 2.4
            sort_key = (-round(pop_score, 6), str(cand.resource_id))
            scored.append((sort_key, item))

        scored.sort(key=lambda pair: pair[0])
        return [item for _, item in scored[:limit]]
