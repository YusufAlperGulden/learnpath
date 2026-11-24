"""Explainable Rule-Based Recommender (Increment 3 live baseline — FR06, FR07)."""

from app.core.config import settings
from app.core.enums import (
    ContentType,
    DifficultyLevel,
    ExperienceLevel,
    MasteryStatus,
)
from app.services.recommenders.base import (
    BaseRecommender,
    CandidateResource,
    RankedCandidate,
    StudentRecommendationContext,
)

_FORMAT_LABELS: dict[ContentType, str] = {
    ContentType.VIDEO: "Video",
    ContentType.ARTICLE: "Article",
    ContentType.EXERCISE: "Interactive Exercise",
}

_GOAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "DATA_SCIENCE": ("data", "numeric", "precision", "clean", "pipeline", "tabular", "aggregation"),
    "WEB_DEVELOPMENT": ("api", "backend", "payload", "network", "unicode", "modular", "routing"),
    "AUTOMATION": ("automation", "script", "stream", "log", "file", "state", "workflow"),
    "ALGORITHMS_PREP": ("algorithm", "complexity", "iteration", "structure", "loop", "function"),
    "PYTHON_FUNDAMENTALS": ("beginner", "fundamental", "step-by-step", "visual", "core", "basics"),
}


def _difficulty_alignment_score(
    resource_diff: DifficultyLevel,
    topic_score: float | None,
    experience_level: ExperienceLevel,
) -> tuple[float, DifficultyLevel]:
    if topic_score is not None:
        if topic_score < 45.0:
            target = DifficultyLevel.BEGINNER
        elif topic_score < settings.MASTERY_THRESHOLD_PERCENT:
            target = DifficultyLevel.INTERMEDIATE
        else:
            target = DifficultyLevel.ADVANCED
    else:
        target = DifficultyLevel(experience_level.value)

    tier_pos = {
        DifficultyLevel.BEGINNER: 0,
        DifficultyLevel.INTERMEDIATE: 1,
        DifficultyLevel.ADVANCED: 2,
    }
    distance = abs(tier_pos[resource_diff] - tier_pos[target])
    if distance == 0:
        return 20.0, target
    if distance == 1:
        return 12.0, target
    return 4.0, target


def _goal_alignment_bonus(candidate: CandidateResource, learning_goal: str) -> float:
    normalized_goal = learning_goal.strip().upper()
    keywords = _GOAL_KEYWORDS.get(normalized_goal)
    if not keywords:
        raw_tokens = [tok.lower() for tok in learning_goal.replace("_", " ").split() if len(tok) >= 3]
        keywords = tuple(raw_tokens)

    if not keywords:
        return 0.0

    haystack = f"{candidate.title} {candidate.description}".lower()
    hits = sum(1 for kw in keywords if kw in haystack)
    return min(hits * 1.5, 4.5)


def _build_rule_rationale(
    candidate: CandidateResource,
    context: StudentRecommendationContext,
    *,
    format_fallback_used: bool,
) -> str:
    threshold = settings.MASTERY_THRESHOLD_PERCENT
    topic_score = context.topic_scores.get(candidate.topic_id)
    mastery = context.topic_mastery.get(candidate.topic_id, MasteryStatus.UNKNOWN)

    if topic_score is not None and topic_score < threshold:
        topic_clause = (
            f"Recommended because your latest {candidate.topic_name} score is "
            f"{topic_score:.0f}% (below the {threshold:.0f}% mastery threshold)"
        )
    elif mastery == MasteryStatus.UNKNOWN:
        topic_clause = (
            f"Recommended because {candidate.topic_name} is your next unlocked curriculum topic"
        )
    else:
        score_txt = f"{topic_score:.0f}%" if topic_score is not None else "mastered"
        topic_clause = (
            f"Recommended for deeper reinforcement in {candidate.topic_name} ({score_txt})"
        )

    fmt_label = _FORMAT_LABELS[candidate.content_type]
    if not format_fallback_used:
        format_clause = f"matches your {fmt_label} format preference"
    else:
        preferred_names = ", ".join(_FORMAT_LABELS[f] for f in context.preferred_formats)
        format_clause = (
            f"included via format relaxation ({fmt_label}) because no additional unseen "
            f"{preferred_names} resources remained for this topic"
        )

    diff_label = candidate.difficulty.value.capitalize()
    return f"{topic_clause}, {format_clause}, and provides {diff_label}-level practice."


class RuleBasedRecommender(BaseRecommender):
    """Transparent deterministic scorer combining topic urgency, format preference, and difficulty."""

    strategy_name = "rule_based"

    def rank(
        self,
        candidates: list[CandidateResource],
        context: StudentRecommendationContext,
        limit: int = 5,
    ) -> list[RankedCandidate]:
        if not candidates or limit <= 0:
            return []

        threshold = settings.MASTERY_THRESHOLD_PERCENT
        scored: list[tuple[tuple[float, int, str], RankedCandidate]] = []

        for cand in candidates:
            topic_score = context.topic_scores.get(cand.topic_id)
            mastery = context.topic_mastery.get(cand.topic_id, MasteryStatus.UNKNOWN)

            # 1. Topic urgency (0..40)
            if mastery == MasteryStatus.NEEDS_PRACTICE and topic_score is not None:
                urgency_pts = 40.0 - min(max(topic_score, 0.0), threshold) * 0.25
            elif mastery == MasteryStatus.UNKNOWN:
                urgency_pts = 24.0 - min(cand.topic_display_order, 10) * 0.6
            else:
                urgency_pts = 10.0

            # 2. Preferred format match (0 or 30)
            matches_format = cand.content_type in context.preferred_formats
            format_pts = 30.0 if matches_format else 0.0
            format_fallback_used = not matches_format

            # 3. Difficulty alignment (4..20)
            diff_pts, _ = _difficulty_alignment_score(
                cand.difficulty,
                topic_score,
                context.experience_level,
            )

            # 4. Learning goal lexical alignment (0..4.5)
            goal_pts = _goal_alignment_bonus(cand, context.learning_goal)

            total_score = round(urgency_pts + format_pts + diff_pts + goal_pts, 4)
            rationale = _build_rule_rationale(
                cand,
                context,
                format_fallback_used=format_fallback_used,
            )

            ranked_item = RankedCandidate(
                candidate=cand,
                score=total_score,
                rationale=rationale,
                format_fallback_used=format_fallback_used,
            )
            sort_key = (-total_score, cand.topic_display_order, str(cand.resource_id))
            scored.append((sort_key, ranked_item))

        scored.sort(key=lambda pair: pair[0])
        return [item for _, item in scored[:limit]]
