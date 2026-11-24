"""Content-Based Filtering Recommender using Scikit-learn TfidfVectorizer + cosine_similarity."""

from collections.abc import Sequence
from uuid import UUID

import numpy as np
from scipy.sparse import csr_matrix, vstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

_GOAL_QUERY_EXPANSION: dict[str, str] = {
    "DATA_SCIENCE": "data science numeric precision cleaning tabular aggregation pipelines",
    "WEB_DEVELOPMENT": "web backend api payload routing unicode modular clean architecture",
    "AUTOMATION": "automation scripting stream logs workflow state files iterators",
    "PYTHON_FUNDAMENTALS": "beginner python fundamentals visual step by step core basics practice",
}


def _compose_resource_document(res: CandidateResource) -> str:
    """Combines resource metadata and rich description into a TF-IDF document."""
    return (
        f"{res.title} {res.title} "
        f"{res.topic_name} "
        f"{res.description} "
        f"format_{res.content_type.value.lower()} "
        f"level_{res.difficulty.value.lower()} "
        f"lang_{res.language.value.lower()}"
    )


def _target_difficulty(
    topic_score: float | None,
    experience: ExperienceLevel,
) -> DifficultyLevel:
    if topic_score is not None:
        if topic_score < 45.0:
            return DifficultyLevel.BEGINNER
        if topic_score < settings.MASTERY_THRESHOLD_PERCENT:
            return DifficultyLevel.INTERMEDIATE
        return DifficultyLevel.ADVANCED
    return DifficultyLevel(experience.value)


def _difficulty_compatibility(
    resource_diff: DifficultyLevel,
    target_diff: DifficultyLevel,
) -> float:
    pos = {
        DifficultyLevel.BEGINNER: 0,
        DifficultyLevel.INTERMEDIATE: 1,
        DifficultyLevel.ADVANCED: 2,
    }
    gap = abs(pos[resource_diff] - pos[target_diff])
    if gap == 0:
        return 1.0
    if gap == 1:
        return 0.55
    return 0.15


class ContentBasedRecommender(BaseRecommender):
    """TF-IDF + profile/proficiency content ranker fitted strictly on training/catalog text."""

    strategy_name = "cbf"

    def __init__(self) -> None:
        self._vectorizer: TfidfVectorizer | None = None
        self._tfidf_matrix: csr_matrix | None = None
        self._index_by_resource_id: dict[UUID, int] = {}
        self._feature_names: np.ndarray | None = None

    @property
    def is_fitted(self) -> bool:
        return self._vectorizer is not None and self._tfidf_matrix is not None

    def fit(self, corpus_resources: Sequence[CandidateResource]) -> "ContentBasedRecommender":
        """Fits TfidfVectorizer exclusively on resource catalog text (zero test-label leakage)."""
        self._index_by_resource_id.clear()
        if not corpus_resources:
            self._vectorizer = None
            self._tfidf_matrix = None
            self._feature_names = None
            return self

        docs = [_compose_resource_document(r) for r in corpus_resources]
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            lowercase=True,
            stop_words="english",
            max_features=4096,
        )
        matrix = vectorizer.fit_transform(docs).tocsr()

        self._vectorizer = vectorizer
        self._tfidf_matrix = matrix
        self._feature_names = vectorizer.get_feature_names_out()
        self._index_by_resource_id = {
            res.resource_id: idx for idx, res in enumerate(corpus_resources)
        }
        return self

    def _build_student_query_document(
        self,
        candidates: Sequence[CandidateResource],
        context: StudentRecommendationContext,
    ) -> str:
        goal_key = context.learning_goal.strip().upper()
        goal_terms = _GOAL_QUERY_EXPANSION.get(
            goal_key,
            context.learning_goal.replace("_", " ").lower(),
        )
        format_terms = " ".join(
            f"format_{fmt.value.lower()} {fmt.value.lower()}"
            for fmt in context.preferred_formats
        )
        topic_names = " ".join({c.topic_name for c in candidates})
        target_levels = {
            _target_difficulty(
                context.topic_scores.get(c.topic_id),
                context.experience_level,
            ).value.lower()
            for c in candidates
        }
        level_terms = " ".join(
            f"level_{lvl} {lvl}"
            for lvl in (target_levels or {context.experience_level.value.lower()})
        )
        return f"{goal_terms} {topic_names} {format_terms} {level_terms}"

    def compute_cbf_scores(
        self,
        candidates: list[CandidateResource],
        context: StudentRecommendationContext,
    ) -> dict[UUID, tuple[float, list[str]]]:
        """Returns `{resource_id: (normalized_cbf_score, top_matching_terms)}` for candidates."""
        if not candidates:
            return {}

        if not self.is_fitted:
            self.fit(candidates)

        assert self._vectorizer is not None
        assert self._tfidf_matrix is not None

        missing = [c for c in candidates if c.resource_id not in self._index_by_resource_id]
        if missing:
            # Transform unseen candidate descriptions with the ALREADY-fitted vectorizer (no refit!)
            extra_docs = [_compose_resource_document(c) for c in missing]
            extra_vecs = self._vectorizer.transform(extra_docs).tocsr()
            start_idx = self._tfidf_matrix.shape[0]
            self._tfidf_matrix = vstack([self._tfidf_matrix, extra_vecs], format="csr")
            for offset, cand in enumerate(missing):
                self._index_by_resource_id[cand.resource_id] = start_idx + offset

        query_doc = self._build_student_query_document(candidates, context)
        profile_vec = self._vectorizer.transform([query_doc]).tocsr()

        history_indices = [
            self._index_by_resource_id[rid]
            for rid in context.positive_history_resource_ids
            if rid in self._index_by_resource_id
        ]
        if history_indices:
            liked_centroid = csr_matrix(self._tfidf_matrix[history_indices].mean(axis=0))
            user_vec = csr_matrix(profile_vec * 0.55 + liked_centroid * 0.45)
        else:
            user_vec = profile_vec

        cand_indices = [self._index_by_resource_id[c.resource_id] for c in candidates]
        cand_matrix = self._tfidf_matrix[cand_indices]
        cos_sims = cosine_similarity(user_vec, cand_matrix).ravel()

        preferred_set = set(context.preferred_formats)
        threshold = settings.MASTERY_THRESHOLD_PERCENT
        user_dense = user_vec.toarray().ravel()

        results: dict[UUID, tuple[float, list[str]]] = {}
        for pos, cand in enumerate(candidates):
            tfidf_sim = float(max(0.0, min(1.0, cos_sims[pos])))
            topic_score = context.topic_scores.get(cand.topic_id)
            mastery = context.topic_mastery.get(cand.topic_id, MasteryStatus.UNKNOWN)

            target_diff = _target_difficulty(topic_score, context.experience_level)
            diff_compat = _difficulty_compatibility(cand.difficulty, target_diff)
            format_compat = 1.0 if cand.content_type in preferred_set else 0.15

            if mastery == MasteryStatus.NEEDS_PRACTICE and topic_score is not None:
                urgency = 1.0 - min(max(topic_score, 0.0), threshold) / 100.0
            elif mastery == MasteryStatus.UNKNOWN:
                urgency = max(0.4, 0.75 - cand.topic_display_order * 0.05)
            else:
                urgency = 0.3

            # Blend TF-IDF cosine similarity with structured profile/proficiency signals -> [0..1]
            blended = (
                0.45 * tfidf_sim
                + 0.25 * format_compat
                + 0.20 * diff_compat
                + 0.10 * urgency
            )
            norm_score = round(float(max(0.0, min(1.0, blended))), 6)

            top_terms: list[str] = []
            if self._feature_names is not None:
                cand_row = cand_matrix[pos].toarray().ravel()
                overlap = user_dense * cand_row
                nonzero_idx = np.flatnonzero(overlap > 0)
                if nonzero_idx.size > 0:
                    ranked_idx = nonzero_idx[np.argsort(-overlap[nonzero_idx])]
                    for feat_idx in ranked_idx:
                        term = str(self._feature_names[feat_idx])
                        if not term.startswith(("format_", "level_", "lang_")) and len(term) >= 3:
                            top_terms.append(term)
                        if len(top_terms) >= 2:
                            break

            results[cand.resource_id] = (norm_score, top_terms)

        return results

    def compute_intra_list_diversity(self, resource_ids: Sequence[UUID]) -> float:
        """Computes `1 - mean pairwise cosine_similarity` across a top-K list (`RQ4` metric)."""
        if len(resource_ids) < 2 or not self.is_fitted or self._tfidf_matrix is None:
            return 0.0

        valid_indices = [
            self._index_by_resource_id[rid]
            for rid in resource_ids
            if rid in self._index_by_resource_id
        ]
        if len(valid_indices) < 2:
            return 0.0

        sub = self._tfidf_matrix[valid_indices]
        sim_matrix = cosine_similarity(sub)
        n = len(valid_indices)
        pair_sum = 0.0
        pair_count = 0
        for i in range(n):
            for j in range(i + 1, n):
                pair_sum += float(max(0.0, min(1.0, sim_matrix[i, j])))
                pair_count += 1

        mean_sim = pair_sum / pair_count if pair_count > 0 else 0.0
        return round(float(max(0.0, min(1.0, 1.0 - mean_sim))), 6)

    def build_cbf_rationale(
        self,
        cand: CandidateResource,
        context: StudentRecommendationContext,
        *,
        top_terms: list[str],
        format_fallback_used: bool,
    ) -> str:
        threshold = settings.MASTERY_THRESHOLD_PERCENT
        topic_score = context.topic_scores.get(cand.topic_id)

        if topic_score is not None and topic_score < threshold:
            gap_clause = (
                f"Addresses your {cand.topic_name} score of {topic_score:.0f}% "
                f"(< {threshold:.0f}% mastery)"
            )
        else:
            gap_clause = f"Matches your unlocked {cand.topic_name} study path"

        fmt_label = _FORMAT_LABELS[cand.content_type]
        if not format_fallback_used:
            fmt_clause = f"aligns with your {fmt_label} format preference"
        else:
            pref_str = ", ".join(_FORMAT_LABELS[f] for f in context.preferred_formats)
            fmt_clause = (
                f"uses format relaxation ({fmt_label}) because fewer unseen {pref_str} "
                f"items were available"
            )

        term_clause = (
            f" and TF-IDF content similarity on '{', '.join(top_terms)}'"
            if top_terms
            else f" at {cand.difficulty.value.capitalize()} difficulty"
        )
        return f"{gap_clause}, {fmt_clause}{term_clause}."

    def rank(
        self,
        candidates: list[CandidateResource],
        context: StudentRecommendationContext,
        limit: int = 5,
    ) -> list[RankedCandidate]:
        if not candidates or limit <= 0:
            return []

        preferred_set = set(context.preferred_formats)
        cbf_map = self.compute_cbf_scores(candidates, context)

        scored: list[tuple[tuple[float, int, str], RankedCandidate]] = []
        for cand in candidates:
            score_val, top_terms = cbf_map[cand.resource_id]
            format_fallback = cand.content_type not in preferred_set
            rationale = self.build_cbf_rationale(
                cand,
                context,
                top_terms=top_terms,
                format_fallback_used=format_fallback,
            )
            item = RankedCandidate(
                candidate=cand,
                score=score_val,
                rationale=rationale,
                format_fallback_used=format_fallback,
            )
            scored.append(((-score_val, cand.topic_display_order, str(cand.resource_id)), item))

        scored.sort(key=lambda pair: pair[0])
        return [item for _, item in scored[:limit]]
