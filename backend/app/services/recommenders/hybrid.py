"""Cold-Start-Honest Weighted Hybrid Recommender combining CBF and CF (RAD v2.0)."""

from dataclasses import dataclass

from app.services.recommenders.base import (
    BaseRecommender,
    CandidateResource,
    RankedCandidate,
    StudentRecommendationContext,
)
from app.services.recommenders.cbf import ContentBasedRecommender
from app.services.recommenders.cf import CollaborativeFilteringRecommender

DEFAULT_VALIDATED_CBF_WEIGHT = 0.60


@dataclass(frozen=True, slots=True)
class HybridRankOutcome:
    items: list[RankedCandidate]
    cold_start_fallback: bool
    cbf_weight_used: float


class HybridRecommender(BaseRecommender):
    """Blends validation-selected CBF and CF scores with automatic cold-start fallback to CBF.

    Per RAD Section 3.4.4.3 & Section 4.4:
    - When a student lacks sufficient collaborative neighbor overlap, Hybrid automatically
      falls back to Content-Based Filtering (`fallback_reason = 'cold_start_insufficient_neighbors'`)
      and NEVER fabricates collaborative explanations.
    """

    strategy_name = "hybrid"

    def __init__(
        self,
        *,
        cbf: ContentBasedRecommender,
        cf: CollaborativeFilteringRecommender,
        cbf_weight: float = DEFAULT_VALIDATED_CBF_WEIGHT,
    ) -> None:
        if not 0.0 <= cbf_weight <= 1.0:
            raise ValueError("cbf_weight must lie in [0.0, 1.0].")
        self.cbf = cbf
        self.cf = cf
        self.cbf_weight = cbf_weight

    def rank_with_diagnostics(
        self,
        candidates: list[CandidateResource],
        context: StudentRecommendationContext,
        limit: int = 5,
    ) -> HybridRankOutcome:
        if not candidates or limit <= 0:
            return HybridRankOutcome(
                items=[],
                cold_start_fallback=False,
                cbf_weight_used=self.cbf_weight,
            )

        cf_preds = self.cf.predict_candidates(candidates, context)
        has_any_cf_support = any(p.has_sufficient_support for p in cf_preds.values())

        # Cold-start safeguard: pure CBF scoring & truthful CBF rationale
        if not has_any_cf_support:
            cbf_items = self.cbf.rank(candidates, context, limit=limit)
            return HybridRankOutcome(
                items=cbf_items,
                cold_start_fallback=True,
                cbf_weight_used=1.0,
            )

        raw_cbf = self.cbf.compute_cbf_scores(candidates, context)
        cbf_vals = [pair[0] for pair in raw_cbf.values()]
        min_cbf = min(cbf_vals)
        max_cbf = max(cbf_vals)
        span_cbf = max_cbf - min_cbf

        preferred_set = set(context.preferred_formats)
        cf_weight = 1.0 - self.cbf_weight

        scored: list[tuple[tuple[float, str], RankedCandidate]] = []
        for cand in candidates:
            raw_val, top_terms = raw_cbf[cand.resource_id]
            # Map CBF onto a comparable [0.15..0.90] scale matching CF normalized ratings
            cbf_val = (
                0.15 + 0.75 * ((raw_val - min_cbf) / span_cbf)
                if span_cbf > 1e-6
                else raw_val
            )
            cf_pred = cf_preds[cand.resource_id]
            format_fallback = cand.content_type not in preferred_set

            if cf_pred.has_sufficient_support:
                blended = round(
                    self.cbf_weight * cbf_val + cf_weight * cf_pred.normalized_score,
                    6,
                )
                base_cbf_rationale = self.cbf.build_cbf_rationale(
                    cand,
                    context,
                    top_terms=top_terms,
                    format_fallback_used=format_fallback,
                ).rstrip(".")
                rationale = (
                    f"{base_cbf_rationale}, reinforced by {cf_pred.predicted_rating:.1f}/5 "
                    f"predicted peer rating from {cf_pred.neighbor_count} similar learners."
                )
            else:
                # Item lacks neighbor ratings -> fall back to CBF score without 0-rating penalty
                blended = round(cbf_val, 6) if self.cbf_weight > 0.0 else 0.0
                rationale = self.cbf.build_cbf_rationale(
                    cand,
                    context,
                    top_terms=top_terms,
                    format_fallback_used=format_fallback,
                )

            item = RankedCandidate(
                candidate=cand,
                score=blended,
                rationale=rationale,
                format_fallback_used=format_fallback,
            )
            scored.append(((-blended, str(cand.resource_id)), item))

        scored.sort(key=lambda pair: pair[0])
        return HybridRankOutcome(
            items=[item for _, item in scored[:limit]],
            cold_start_fallback=False,
            cbf_weight_used=self.cbf_weight,
        )

    def rank(
        self,
        candidates: list[CandidateResource],
        context: StudentRecommendationContext,
        limit: int = 5,
    ) -> list[RankedCandidate]:
        return self.rank_with_diagnostics(candidates, context, limit=limit).items
