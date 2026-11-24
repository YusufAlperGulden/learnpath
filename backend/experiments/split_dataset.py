"""Chronological Train / Validation / Test splitter, deduplicator, and Hybrid weight tuner.

Follows RAD v2.0 Section 2.4 & Section 3.4.4:
1. Deduplicates repeated `(student_id, resource_id)` pairs prior to splitting (retaining latest).
2. Splits strictly chronologically into Train (70%), Validation (15%), and Test (15%).
3. Treats ratings >= 4 as relevant positive ground truth.
4. Enforces identical prerequisite-unlocked, language-matched unseen candidate pools across models.
5. Tunes Hybrid `cbf_weight` exclusively on the Validation split (fitted only on Train).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    ContentType,
    DifficultyLevel,
    ExperienceLevel,
    SupportedLanguage,
)
from app.core.logging_config import configure_logging, get_logger
from app.models.catalog import Resource
from app.models.progress import Feedback
from app.models.user import User
from app.services.recommendation_service import compute_learning_path
from app.services.recommenders import (
    CandidateResource,
    CollaborativeFilteringRecommender,
    ContentBasedRecommender,
    HybridRecommender,
    InteractionRecord,
    StudentRecommendationContext,
)
from experiments.metrics import (
    ndcg_at_k,
    open_experiment_session,
    precision_at_k,
    recall_at_k,
)
from scripts.seed_interactions import seed_interaction_cohort

logger = get_logger("experiments.split")

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
RELEVANCE_RATING_THRESHOLD = 4.0

__all__ = [
    "ARTIFACTS_DIR",
    "RELEVANCE_RATING_THRESHOLD",
    "ChronologicalSplit",
    "SplitAndTuningReport",
    "WeightGridPoint",
    "build_offline_student_context",
    "deduplicate_interactions",
    "get_eligible_unseen_candidates",
    "load_active_catalog_candidates",
    "ndcg_at_k",
    "precision_at_k",
    "recall_at_k",
    "run_split_and_validation_tuning",
    "select_hybrid_weight_on_validation",
    "split_interactions_chronologically",
]


@dataclass(frozen=True, slots=True)
class ChronologicalSplit:
    train: list[InteractionRecord]
    validation: list[InteractionRecord]
    test: list[InteractionRecord]
    raw_count: int
    deduplicated_count: int
    duplicates_removed: int
    train_end_at: str | None
    validation_end_at: str | None


@dataclass(frozen=True, slots=True)
class WeightGridPoint:
    cbf_weight: float
    cf_weight: float
    validation_ndcg_at_5: float
    validation_precision_at_5: float
    evaluated_users: int
    excluded_zero_relevant_users: int


@dataclass(frozen=True, slots=True)
class SplitAndTuningReport:
    raw_interactions: int
    deduplicated_interactions: int
    duplicates_removed: int
    train_size: int
    validation_size: int
    test_size: int
    train_end_at: str | None
    validation_end_at: str | None
    selected_cbf_weight: float
    selected_cf_weight: float
    best_validation_ndcg_at_5: float
    grid_results: list[WeightGridPoint]


def _normalize_ts(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime(1970, 1, 1, tzinfo=UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def deduplicate_interactions(
    records: Sequence[InteractionRecord],
) -> tuple[list[InteractionRecord], int]:
    """Deduplicates `(student_id, resource_id)` pairs BEFORE splitting, keeping latest timestamp."""
    indexed = list(enumerate(records))
    indexed.sort(
        key=lambda pair: (
            _normalize_ts(pair[1].created_at),
            pair[0],
        )
    )

    latest_by_pair: dict[tuple[UUID, UUID], InteractionRecord] = {}
    for _, rec in indexed:
        latest_by_pair[(rec.student_id, rec.resource_id)] = rec

    deduped = sorted(
        latest_by_pair.values(),
        key=lambda r: (_normalize_ts(r.created_at), str(r.student_id), str(r.resource_id)),
    )
    removed = len(records) - len(deduped)
    return deduped, removed


def split_interactions_chronologically(
    records: Sequence[InteractionRecord],
    *,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> ChronologicalSplit:
    """Creates leak-free chronological Train / Validation / Test partitions."""
    if not (0.0 < train_ratio < 1.0 and 0.0 < val_ratio < 1.0 and train_ratio + val_ratio < 1.0):
        raise ValueError("train_ratio and val_ratio must be positive and sum to < 1.0.")

    deduped, removed = deduplicate_interactions(records)
    n = len(deduped)
    if n == 0:
        return ChronologicalSplit(
            train=[],
            validation=[],
            test=[],
            raw_count=len(records),
            deduplicated_count=0,
            duplicates_removed=removed,
            train_end_at=None,
            validation_end_at=None,
        )

    train_end = max(1, round(n * train_ratio))
    val_end = max(train_end + 1, round(n * (train_ratio + val_ratio)))
    val_end = min(val_end, max(train_end, n - 1))

    train = deduped[:train_end]
    validation = deduped[train_end:val_end]
    test = deduped[val_end:]

    return ChronologicalSplit(
        train=train,
        validation=validation,
        test=test,
        raw_count=len(records),
        deduplicated_count=n,
        duplicates_removed=removed,
        train_end_at=_normalize_ts(train[-1].created_at).isoformat() if train else None,
        validation_end_at=(
            _normalize_ts(validation[-1].created_at).isoformat() if validation else None
        ),
    )


def load_active_catalog_candidates(db: Session) -> list[CandidateResource]:
    rows = db.scalars(
        select(Resource)
        .options(selectinload(Resource.topic))
        .where(Resource.is_active.is_(True))
        .order_by(Resource.resource_id.asc())
    ).all()
    candidates = [
        CandidateResource(
            resource_id=r.resource_id,
            topic_id=r.topic_id,
            topic_name=r.topic.name if r.topic else "Python",
            topic_display_order=r.topic.display_order if r.topic else 0,
            title=r.title,
            description=r.description,
            external_url=r.external_url,
            content_type=ContentType(r.content_type),
            difficulty=DifficultyLevel(r.difficulty),
            language=SupportedLanguage(r.language),
            estimated_minutes=r.estimated_minutes,
        )
        for r in rows
    ]
    candidates.sort(key=lambda c: str(c.resource_id))
    return candidates


def get_eligible_unseen_candidates(
    db: Session,
    *,
    student_id: UUID,
    preferred_language: SupportedLanguage,
    seen_resource_ids: set[UUID],
    catalog: Sequence[CandidateResource],
) -> list[CandidateResource]:
    """Returns identical prerequisite-unlocked, language-matched, unseen candidates for a query."""
    path = compute_learning_path(db, student_id=student_id)
    unlocked_topic_ids = {node.topic_id for node in path.nodes if not node.is_locked}
    return [
        c
        for c in catalog
        if c.language == preferred_language
        and c.topic_id in unlocked_topic_ids
        and c.resource_id not in seen_resource_ids
    ]


def build_offline_student_context(
    db: Session,
    student: User,
    history_interactions: Sequence[InteractionRecord],
) -> StudentRecommendationContext:
    """Constructs leak-free student context using ONLY historical interactions up to split cutoff."""
    profile = student.profile
    if profile is not None:
        exp = ExperienceLevel(profile.experience_level)
        formats = tuple(ContentType(f) for f in profile.preferred_formats)
        lang = SupportedLanguage(profile.preferred_language)
        goal = profile.learning_goal
    else:
        exp = ExperienceLevel.BEGINNER
        formats = (ContentType.VIDEO, ContentType.ARTICLE, ContentType.EXERCISE)
        lang = SupportedLanguage.EN
        goal = "PYTHON_FUNDAMENTALS"

    path = compute_learning_path(db, student_id=student.user_id)
    user_ratings = {rec.resource_id: float(rec.rating) for rec in history_interactions}
    pos_ids = tuple(
        sorted(
            (rid for rid, val in user_ratings.items() if val >= RELEVANCE_RATING_THRESHOLD),
            key=str,
        )
    )

    return StudentRecommendationContext(
        student_id=student.user_id,
        experience_level=exp,
        preferred_formats=formats,
        preferred_language=lang,
        learning_goal=goal,
        topic_scores={
            n.topic_id: n.latest_score_percent
            for n in path.nodes
            if n.latest_score_percent is not None
        },
        topic_mastery={n.topic_id: n.mastery_status for n in path.nodes},
        positive_history_resource_ids=pos_ids,
        user_ratings=user_ratings,
    )


def select_hybrid_weight_on_validation(
    db: Session,
    split: ChronologicalSplit,
    *,
    k: int = 5,
    weight_grid: Sequence[float] = (0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0),
    cbf_recommender: ContentBasedRecommender | None = None,
) -> tuple[float, list[WeightGridPoint]]:
    """Selects Hybrid `cbf_weight` solely on the Validation partition (fitted on Train only)."""
    catalog = load_active_catalog_candidates(db)
    cbf = cbf_recommender if cbf_recommender is not None else ContentBasedRecommender().fit(catalog)
    if not cbf.is_fitted:
        cbf.fit(catalog)
    cf = CollaborativeFilteringRecommender().fit(split.train)

    train_by_user: dict[UUID, list[InteractionRecord]] = defaultdict(list)
    for rec in split.train:
        train_by_user[rec.student_id].append(rec)

    val_by_user: dict[UUID, list[InteractionRecord]] = defaultdict(list)
    for rec in split.validation:
        val_by_user[rec.student_id].append(rec)

    eval_user_ids = sorted(val_by_user.keys(), key=str)
    users_by_id = {
        u.user_id: u
        for u in db.scalars(
            select(User)
            .options(selectinload(User.profile))
            .where(User.user_id.in_(eval_user_ids))
        ).all()
    }

    # Precompute student contexts and eligible candidate pools once per validation user
    prepared_queries: list[
        tuple[StudentRecommendationContext, list[CandidateResource], set[UUID]]
    ] = []
    excluded_zero_rel = 0
    for uid in eval_user_ids:
        user = users_by_id.get(uid)
        if user is None:
            continue
        hist = train_by_user.get(uid, [])
        seen_train_ids = {r.resource_id for r in hist}
        ctx = build_offline_student_context(db, user, hist)
        eligible_candidates = get_eligible_unseen_candidates(
            db,
            student_id=uid,
            preferred_language=ctx.preferred_language,
            seen_resource_ids=seen_train_ids,
            catalog=catalog,
        )
        eligible_ids = {c.resource_id for c in eligible_candidates}
        rel_ids = {
            r.resource_id
            for r in val_by_user[uid]
            if r.rating >= RELEVANCE_RATING_THRESHOLD and r.resource_id in eligible_ids
        }
        if not rel_ids:
            excluded_zero_rel += 1
            continue
        prepared_queries.append((ctx, eligible_candidates, rel_ids))

    grid_points: list[WeightGridPoint] = []
    best_weight = 0.60
    best_key = (-1.0, -1.0, -1.0)

    for weight in weight_grid:
        w = round(float(weight), 2)
        hybrid = HybridRecommender(cbf=cbf, cf=cf, cbf_weight=w)
        ndcgs: list[float] = []
        precisions: list[float] = []

        for ctx, eligible_candidates, rel_ids in prepared_queries:
            ranked = hybrid.rank(eligible_candidates, ctx, limit=k)
            rec_ids = [item.candidate.resource_id for item in ranked]
            ndcgs.append(ndcg_at_k(rec_ids, rel_ids, k=k))
            precisions.append(precision_at_k(rec_ids, rel_ids, k=k))

        mean_ndcg = round(sum(ndcgs) / len(ndcgs), 6) if ndcgs else 0.0
        mean_prec = round(sum(precisions) / len(precisions), 6) if precisions else 0.0
        grid_points.append(
            WeightGridPoint(
                cbf_weight=w,
                cf_weight=round(1.0 - w, 2),
                validation_ndcg_at_5=mean_ndcg,
                validation_precision_at_5=mean_prec,
                evaluated_users=len(ndcgs),
                excluded_zero_relevant_users=excluded_zero_rel,
            )
        )
        # Prefer interior hybrid weights over extremes when validation NDCG ties
        balance_tiebreak = -abs(w - 0.55)
        cand_key = (mean_ndcg, mean_prec, balance_tiebreak)
        if cand_key > best_key:
            best_key = cand_key
            best_weight = w

    return best_weight, grid_points


def load_or_seed_interactions(db: Session) -> list[InteractionRecord]:
    """Loads persisted feedback rows, seeding the documented 48-learner cohort if empty."""
    raw_rows = db.scalars(select(Feedback)).all()
    if len(raw_rows) < 50:
        seed_interaction_cohort(db)
        raw_rows = db.scalars(select(Feedback)).all()

    return [
        InteractionRecord(
            student_id=row.student_id,
            resource_id=row.resource_id,
            rating=float(row.rating),
            created_at=row.created_at,
        )
        for row in raw_rows
    ]


def run_split_and_validation_tuning(
    db: Session,
    *,
    write_artifacts: bool = True,
) -> SplitAndTuningReport:
    interactions = load_or_seed_interactions(db)
    split = split_interactions_chronologically(interactions)
    best_weight, grid_points = select_hybrid_weight_on_validation(db, split)
    best_ndcg = max((pt.validation_ndcg_at_5 for pt in grid_points), default=0.0)

    report = SplitAndTuningReport(
        raw_interactions=split.raw_count,
        deduplicated_interactions=split.deduplicated_count,
        duplicates_removed=split.duplicates_removed,
        train_size=len(split.train),
        validation_size=len(split.validation),
        test_size=len(split.test),
        train_end_at=split.train_end_at,
        validation_end_at=split.validation_end_at,
        selected_cbf_weight=best_weight,
        selected_cf_weight=round(1.0 - best_weight, 2),
        best_validation_ndcg_at_5=best_ndcg,
        grid_results=grid_points,
    )

    if write_artifacts:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "split_summary.json").write_text(
            json.dumps(asdict(report), indent=2),
            encoding="utf-8",
        )
        (ARTIFACTS_DIR / "hybrid_tuning.json").write_text(
            json.dumps(
                {
                    "selected_cbf_weight": report.selected_cbf_weight,
                    "selected_cf_weight": report.selected_cf_weight,
                    "best_validation_ndcg_at_5": report.best_validation_ndcg_at_5,
                    "grid_results": [asdict(g) for g in grid_points],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info(
            "Saved split & validation tuning artifacts: train=%d val=%d test=%d "
            "best_cbf_weight=%.2f (val NDCG@5=%.4f)",
            report.train_size,
            report.validation_size,
            report.test_size,
            report.selected_cbf_weight,
            report.best_validation_ndcg_at_5,
        )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run chronological Train/Val/Test split and validation Hybrid weight tuning."
    )
    parser.add_argument(
        "--db",
        choices=("auto", "postgres", "sqlite"),
        default="auto",
        help="Database connection mode (defaults to 'auto').",
    )
    args = parser.parse_args()

    configure_logging()
    with open_experiment_session(args.db) as (db, _backend):
        report = run_split_and_validation_tuning(db, write_artifacts=True)
        print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
