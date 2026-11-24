"""User-Based Collaborative Filtering treating unrated items strictly as unknown (RAD v2.0)."""

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
class CFPrediction:
    normalized_score: float
    predicted_rating: float
    neighbor_count: int
    has_sufficient_support: bool


class CollaborativeFilteringRecommender(BaseRecommender):
    """Sparse user-resource matrix recommender where missing entries remain unknown (never 0).

    Uses mean-centered shrinkage similarity over co-rated items only, and enforces cold-start
    honesty by never claiming peer similarity when neighbor overlap is insufficient.
    """

    strategy_name = "cf"

    def __init__(
        self,
        *,
        min_common_items: int = 2,
        min_neighbors: int = 2,
        shrinkage_beta: float = 3.0,
    ) -> None:
        self.min_common_items = min_common_items
        self.min_neighbors = min_neighbors
        self.shrinkage_beta = shrinkage_beta
        self._ratings_by_user: dict[UUID, dict[UUID, float]] = {}
        self._users_by_resource: dict[UUID, set[UUID]] = defaultdict(set)
        self._user_means: dict[UUID, float] = {}

    def fit(self, interactions: Sequence[InteractionRecord]) -> "CollaborativeFilteringRecommender":
        self._ratings_by_user.clear()
        self._users_by_resource.clear()
        self._user_means.clear()

        grouped: dict[UUID, dict[UUID, float]] = defaultdict(dict)
        for rec in interactions:
            grouped[rec.student_id][rec.resource_id] = float(rec.rating)

        for uid, item_map in grouped.items():
            if not item_map:
                continue
            self._ratings_by_user[uid] = dict(item_map)
            self._user_means[uid] = sum(item_map.values()) / len(item_map)
            for rid in item_map:
                self._users_by_resource[rid].add(uid)

        return self

    def _resolve_target_ratings(
        self,
        context: StudentRecommendationContext,
    ) -> tuple[dict[UUID, float], float]:
        merged: dict[UUID, float] = {}
        if context.student_id in self._ratings_by_user:
            merged.update(self._ratings_by_user[context.student_id])
        if context.user_ratings:
            merged.update({rid: float(val) for rid, val in context.user_ratings.items()})

        if not merged:
            return {}, 3.5
        return merged, sum(merged.values()) / len(merged)

    def _user_similarity(
        self,
        target_ratings: dict[UUID, float],
        target_mean: float,
        neighbor_id: UUID,
    ) -> float:
        neighbor_ratings = self._ratings_by_user.get(neighbor_id)
        if not neighbor_ratings:
            return 0.0

        common_ids = [rid for rid in target_ratings if rid in neighbor_ratings]
        n_common = len(common_ids)
        if n_common < self.min_common_items:
            return 0.0

        neighbor_mean = self._user_means[neighbor_id]
        num = 0.0
        norm_u = 0.0
        norm_v = 0.0

        for rid in common_ids:
            du = target_ratings[rid] - target_mean
            dv = neighbor_ratings[rid] - neighbor_mean
            num += du * dv
            norm_u += du * du
            norm_v += dv * dv

        denom = math.sqrt(norm_u) * math.sqrt(norm_v)
        if denom > 1e-9:
            raw_sim = num / denom
        else:
            # Handle constant-rating users (e.g., both rated co-rated items 5.0/5.0) without NaN
            mean_diff = sum(
                abs(target_ratings[rid] - neighbor_ratings[rid]) for rid in common_ids
            ) / n_common
            raw_sim = max(0.0, 1.0 - mean_diff / 2.0)

        if raw_sim <= 0.0:
            return 0.0

        shrinkage = n_common / (n_common + self.shrinkage_beta)
        return raw_sim * shrinkage

    def predict_candidates(
        self,
        candidates: Sequence[CandidateResource],
        context: StudentRecommendationContext,
    ) -> dict[UUID, CFPrediction]:
        if not candidates:
            return {}

        target_ratings, target_mean = self._resolve_target_ratings(context)
        if len(target_ratings) < self.min_common_items:
            return {
                cand.resource_id: CFPrediction(
                    normalized_score=0.0,
                    predicted_rating=target_mean,
                    neighbor_count=0,
                    has_sufficient_support=False,
                )
                for cand in candidates
            }

        # Compute similarities once across candidate-relevant neighbors
        candidate_neighbor_ids: set[UUID] = set()
        for cand in candidates:
            candidate_neighbor_ids.update(self._users_by_resource.get(cand.resource_id, set()))
        candidate_neighbor_ids.discard(context.student_id)

        sim_by_neighbor: dict[UUID, float] = {}
        for nid in candidate_neighbor_ids:
            sim = self._user_similarity(target_ratings, target_mean, nid)
            if sim > 0.0:
                sim_by_neighbor[nid] = sim

        predictions: dict[UUID, CFPrediction] = {}
        for cand in candidates:
            raters = self._users_by_resource.get(cand.resource_id, set())
            active_neighbors = [
                (nid, sim_by_neighbor[nid])
                for nid in raters
                if nid in sim_by_neighbor
            ]
            neighbor_cnt = len(active_neighbors)
            if neighbor_cnt < self.min_neighbors:
                predictions[cand.resource_id] = CFPrediction(
                    normalized_score=0.0,
                    predicted_rating=target_mean,
                    neighbor_count=neighbor_cnt,
                    has_sufficient_support=False,
                )
                continue

            weighted_dev = sum(
                sim * (self._ratings_by_user[nid][cand.resource_id] - self._user_means[nid])
                for nid, sim in active_neighbors
            )
            sim_sum = sum( abs(sim) for _, sim in active_neighbors )
            pred_rating = max(1.0, min(5.0, target_mean + weighted_dev / sim_sum))
            norm_score = round((pred_rating - 1.0) / 4.0, 6)

            predictions[cand.resource_id] = CFPrediction(
                normalized_score=norm_score,
                predicted_rating=round(pred_rating, 2),
                neighbor_count=neighbor_cnt,
                has_sufficient_support=True,
            )

        return predictions

    def has_collaborative_support(
        self,
        candidates: Sequence[CandidateResource],
        context: StudentRecommendationContext,
    ) -> bool:
        preds = self.predict_candidates(candidates, context)
        return any(p.has_sufficient_support for p in preds.values())

    def rank(
        self,
        candidates: list[CandidateResource],
        context: StudentRecommendationContext,
        limit: int = 5,
    ) -> list[RankedCandidate]:
        if not candidates or limit <= 0:
            return []

        preferred_set = set(context.preferred_formats)
        preds = self.predict_candidates(candidates, context)
        scored: list[tuple[tuple[int, float, int, str], RankedCandidate]] = []

        for cand in candidates:
            pred = preds[cand.resource_id]
            format_fallback = cand.content_type not in preferred_set
            final_score = round(pred.normalized_score, 6) if pred.has_sufficient_support else 0.0

            if pred.has_sufficient_support:
                rationale = (
                    f"Collaborative prediction of {pred.predicted_rating:.1f}/5 based on "
                    f"{pred.neighbor_count} learners with overlapping Python resource ratings "
                    f"in {cand.topic_name}."
                )
            else:
                rationale = (
                    f"Insufficient overlapping peer ratings for {cand.topic_name} "
                    f"(cold-start state); ordered by resource identifier without peer extrapolation."
                )

            item = RankedCandidate(
                candidate=cand,
                score=final_score,
                rationale=rationale,
                format_fallback_used=format_fallback,
            )
            sort_key = (
                0 if pred.has_sufficient_support else 1,
                -final_score,
                str(cand.resource_id),
            )
            scored.append((sort_key, item))

        scored.sort(key=lambda pair: pair[0])
        return [item for _, item in scored[:limit]]
