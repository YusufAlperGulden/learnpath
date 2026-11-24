"""Increment 5 test suite: chronological split, Popularity/CBF/CF/Hybrid, and cold-start honesty."""

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import (
    ContentType,
    DifficultyLevel,
    ExperienceLevel,
    SupportedLanguage,
    UserRole,
)
from app.core.security import create_access_token
from app.models.user import User
from app.services.recommenders import (
    CandidateResource,
    CollaborativeFilteringRecommender,
    InteractionRecord,
    PopularityRecommender,
    StudentRecommendationContext,
)
from experiments.split_dataset import (
    deduplicate_interactions,
    run_split_and_validation_tuning,
    split_interactions_chronologically,
)
from scripts.seed_interactions import seed_interaction_cohort
from tests.test_foundation import client, db_session  # noqa: F401


def _headers_for_email(db: Session, email: str, role: UserRole) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    token = create_access_token(user_id=user.user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


def test_pre_split_deduplication_and_leak_free_chronological_partitioning() -> None:
    u1, u2 = uuid4(), uuid4()
    r1, r2, r3, r4, r5, r6 = (uuid4() for _ in range(6))
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)

    raw = [
        # Duplicate (u1, r1): early rating 2.0 later updated to 5.0 -> must deduplicate to 1 row (5.0)
        InteractionRecord(u1, r1, 2.0, t0 + timedelta(days=1)),
        InteractionRecord(u1, r2, 4.0, t0 + timedelta(days=2)),
        InteractionRecord(u2, r2, 5.0, t0 + timedelta(days=3)),
        InteractionRecord(u1, r1, 5.0, t0 + timedelta(days=4)),
        InteractionRecord(u2, r3, 3.0, t0 + timedelta(days=5)),
        InteractionRecord(u1, r4, 5.0, t0 + timedelta(days=6)),
        InteractionRecord(u2, r5, 4.0, t0 + timedelta(days=7)),
        InteractionRecord(u1, r6, 5.0, t0 + timedelta(days=8)),
    ]

    deduped, removed = deduplicate_interactions(raw)
    assert removed == 1
    assert len(deduped) == 7
    r1_entry = next(x for x in deduped if x.student_id == u1 and x.resource_id == r1)
    assert r1_entry.rating == 5.0

    split = split_interactions_chronologically(raw, train_ratio=0.60, val_ratio=0.20)
    assert split.duplicates_removed == 1
    assert len(split.train) + len(split.validation) + len(split.test) == 7

    max_train_ts = max(x.created_at for x in split.train if x.created_at is not None)
    min_val_ts = min(x.created_at for x in split.validation if x.created_at is not None)
    max_val_ts = max(x.created_at for x in split.validation if x.created_at is not None)
    min_test_ts = min(x.created_at for x in split.test if x.created_at is not None)

    assert max_train_ts <= min_val_ts
    assert max_val_ts <= min_test_ts


def test_popularity_tiebreak_and_unknown_aware_cf_semantics() -> None:
    topic_id = uuid4()
    c_high_uuid = CandidateResource(
        resource_id=uuid4(),
        topic_id=topic_id,
        topic_name="Loops",
        topic_display_order=1,
        title="Resource Z",
        description="Loops practice exercises.",
        external_url="https://example.org/z",
        content_type=ContentType.VIDEO,
        difficulty=DifficultyLevel.BEGINNER,
        language=SupportedLanguage.EN,
    )
    c_low_uuid = CandidateResource(
        resource_id=uuid4(),
        topic_id=topic_id,
        topic_name="Loops",
        topic_display_order=1,
        title="Resource A",
        description="Loops video walkthrough.",
        external_url="https://example.org/a",
        content_type=ContentType.VIDEO,
        difficulty=DifficultyLevel.BEGINNER,
        language=SupportedLanguage.EN,
    )
    ctx = StudentRecommendationContext(
        student_id=uuid4(),
        experience_level=ExperienceLevel.BEGINNER,
        preferred_formats=(ContentType.VIDEO,),
        preferred_language=SupportedLanguage.EN,
        learning_goal="PYTHON_FUNDAMENTALS",
    )

    # Equal popularity (0 ratings each) must break ties by str(resource_id) ascending
    pop = PopularityRecommender().fit([])
    ranked_pop = pop.rank([c_high_uuid, c_low_uuid], ctx, limit=2)
    expected_order = sorted(
        [c_high_uuid.resource_id, c_low_uuid.resource_id],
        key=str,
    )
    assert [r.candidate.resource_id for r in ranked_pop] == expected_order

    # Unknown-aware CF check: unrated items in the catalog must NOT lower user means or flip predictions
    u_target, n1, n2 = uuid4(), uuid4(), uuid4()
    r_shared_1, r_shared_2, r_cand = uuid4(), uuid4(), uuid4()
    interactions = [
        InteractionRecord(u_target, r_shared_1, 5.0),
        InteractionRecord(u_target, r_shared_2, 4.0),
        InteractionRecord(n1, r_shared_1, 5.0),
        InteractionRecord(n1, r_shared_2, 4.0),
        InteractionRecord(n1, r_cand, 5.0),
        InteractionRecord(n2, r_shared_1, 5.0),
        InteractionRecord(n2, r_shared_2, 4.0),
        InteractionRecord(n2, r_cand, 5.0),
    ]
    cf = CollaborativeFilteringRecommender(min_common_items=2, min_neighbors=2).fit(interactions)

    cand_obj = CandidateResource(
        resource_id=r_cand,
        topic_id=topic_id,
        topic_name="Loops",
        topic_display_order=1,
        title="Peer Favorite Loops Guide",
        description="Loved by similar Python learners.",
        external_url="https://example.org/peer",
        content_type=ContentType.VIDEO,
        difficulty=DifficultyLevel.BEGINNER,
        language=SupportedLanguage.EN,
    )
    unrated_extra = CandidateResource(
        resource_id=uuid4(),
        topic_id=topic_id,
        topic_name="Loops",
        topic_display_order=1,
        title="Brand New Unrated Item",
        description="Zero ratings so far.",
        external_url="https://example.org/new",
        content_type=ContentType.VIDEO,
        difficulty=DifficultyLevel.BEGINNER,
        language=SupportedLanguage.EN,
    )

    warm_ctx = StudentRecommendationContext(
        student_id=u_target,
        experience_level=ExperienceLevel.BEGINNER,
        preferred_formats=(ContentType.VIDEO,),
        preferred_language=SupportedLanguage.EN,
        learning_goal="PYTHON_FUNDAMENTALS",
    )
    pred_single = cf.predict_candidates([cand_obj], warm_ctx)[r_cand]
    pred_with_unrated = cf.predict_candidates([cand_obj, unrated_extra], warm_ctx)[r_cand]
    assert pred_single.has_sufficient_support is True
    assert pred_single.predicted_rating == pred_with_unrated.predicted_rating
    assert pred_single.predicted_rating >= 4.5


def test_cohort_seed_validation_tuning_cold_start_honesty_and_5_live_strategies(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    # 1. Seed cohort twice to confirm idempotency
    first = seed_interaction_cohort(db_session)
    second = seed_interaction_cohort(db_session)
    assert first.cohort_students == 48
    assert first.cold_start_students == 8
    assert first.total_feedback_rows == second.total_feedback_rows
    assert first.total_feedback_rows >= 500

    # 2. Run chronological split + validation-only Hybrid weight selection
    report = run_split_and_validation_tuning(db_session, write_artifacts=False)
    assert report.duplicates_removed == 0
    assert report.train_size > report.validation_size > 0
    assert report.test_size > 0
    assert 0.0 <= report.selected_cbf_weight <= 1.0
    assert report.best_validation_ndcg_at_5 > 0.0

    # 3. Cold-start student (`student@learnpath.local` has 0 ratings) calling ?strategy=hybrid
    # MUST trigger fallback_reason='cold_start_insufficient_neighbors' and NEVER claim peer support!
    cold_headers = _headers_for_email(
        db_session, "student@learnpath.local", UserRole.STUDENT
    )
    cold_hybrid = client.get(
        "/api/v1/recommendations?strategy=hybrid&limit=5",
        headers=cold_headers,
    )
    assert cold_hybrid.status_code == 200
    cold_body = cold_hybrid.json()
    assert cold_body["strategy_used"] == "hybrid"
    assert cold_body["fallback_applied"] is True
    assert cold_body["fallback_reason"] == "cold_start_insufficient_neighbors"
    assert len(cold_body["items"]) == 5
    for item in cold_body["items"]:
        lower_rat = item["rationale"].lower()
        assert "similar learners" not in lower_rat
        assert "peer rating" not in lower_rat

    # 4. Warm-start cohort learner (`cohort-01@learnpath.local`) across all 5 live strategies
    warm_headers = _headers_for_email(
        db_session, "cohort-01@learnpath.local", UserRole.STUDENT
    )
    for strat in ("rule_based", "popularity", "cbf", "cf", "hybrid"):
        t0 = time.perf_counter()
        res = client.get(
            f"/api/v1/recommendations?strategy={strat}&limit=5",
            headers=warm_headers,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert res.status_code == 200
        data = res.json()
        assert data["strategy_used"] == strat
        assert len(data["items"]) == 5
        assert all(len(it["rationale"]) > 20 for it in data["items"])
        # Second/cached calls stay well inside the < 200ms NFR-05 target
        if strat in ("cbf", "hybrid"):
            t1 = time.perf_counter()
            cached_res = client.get(
                f"/api/v1/recommendations?strategy={strat}&limit=5",
                headers=warm_headers,
            )
            cached_ms = (time.perf_counter() - t1) * 1000.0
            assert cached_res.status_code == 200
            assert cached_ms < 200.0, f"Cached {strat} exceeded 200ms: {cached_ms:.1f}ms (first={elapsed_ms:.1f}ms)"

    warm_hybrid = client.get(
        "/api/v1/recommendations?strategy=hybrid&limit=5",
        headers=warm_headers,
    ).json()
    assert warm_hybrid["fallback_reason"] != "cold_start_insufficient_neighbors"
    assert any("similar learners" in it["rationale"].lower() for it in warm_hybrid["items"])
