"""Regression tests: concurrent duplicate-insert races must not surface as HTTP 500."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalog import Resource
from app.models.progress import ResourceProgress, SavedResource
from app.models.user import User
from app.services.progress_service import record_resource_open, save_student_bookmark
from scripts.seed_data import seed_database
from tests.test_foundation import db_session  # noqa: F401


def _fail_first_commit(db: Session, monkeypatch) -> list[int]:  # type: ignore[no-untyped-def]
    """Makes the next db.commit() raise IntegrityError once, simulating a lost insert race."""
    real_commit = db.commit
    calls = [0]

    def flaky_commit() -> None:
        calls[0] += 1
        if calls[0] == 1:
            raise IntegrityError("INSERT", {}, Exception("duplicate key (simulated race)"))
        real_commit()

    monkeypatch.setattr(db, "commit", flaky_commit)
    return calls


def test_resource_open_and_bookmark_recover_from_duplicate_insert_race(
    db_session: Session,  # noqa: F811
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    seed_database(db_session)
    student = db_session.scalar(select(User).where(User.email == "student@learnpath.local"))
    resource = db_session.scalar(select(Resource).limit(1))
    assert student is not None and resource is not None

    calls = _fail_first_commit(db_session, monkeypatch)
    opened = record_resource_open(
        db_session, student_id=student.user_id, resource_id=resource.resource_id
    )
    assert opened.status.value == "OPENED"
    assert calls[0] == 2  # first commit lost the race, retry succeeded
    assert db_session.scalar(select(func.count()).select_from(ResourceProgress)) == 1

    calls = _fail_first_commit(db_session, monkeypatch)
    saved = save_student_bookmark(
        db_session, student_id=student.user_id, resource_id=resource.resource_id
    )
    assert saved.resource_id == resource.resource_id
    assert calls[0] == 2
    assert db_session.scalar(select(func.count()).select_from(SavedResource)) == 1


def test_idempotent_seed_short_circuits_without_rehashing(
    db_session: Session,  # noqa: F811
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    import scripts.seed_data as seed_data_mod
    import scripts.seed_interactions as seed_inter_mod

    first = seed_inter_mod.seed_interaction_cohort(db_session)
    assert first.cohort_students == 48
    assert first.total_feedback_rows >= 600

    def _forbid_argon2(_pw: str) -> str:
        raise AssertionError("hash_password must not run on an already-seeded database")

    monkeypatch.setattr(seed_data_mod, "hash_password", _forbid_argon2)
    monkeypatch.setattr(seed_inter_mod, "hash_password", _forbid_argon2)

    second = seed_inter_mod.seed_interaction_cohort(db_session)
    assert second.cohort_students == 48
    assert second.total_feedback_rows == first.total_feedback_rows


def test_cbf_unseen_candidate_scoring_does_not_mutate_shared_matrix() -> None:
    from uuid import uuid4

    from app.core.enums import (
        ContentType,
        DifficultyLevel,
        ExperienceLevel,
        SupportedLanguage,
    )
    from app.services.recommenders.base import (
        CandidateResource,
        StudentRecommendationContext,
    )
    from app.services.recommenders.cbf import ContentBasedRecommender

    topic_id = uuid4()
    base_res = CandidateResource(
        resource_id=uuid4(),
        topic_id=topic_id,
        topic_name="Variables & Data Types",
        topic_display_order=1,
        title="Python Variables Visual Guide",
        description="Step by step introduction to Python types, integers, and strings.",
        content_type=ContentType.VIDEO,
        difficulty=DifficultyLevel.BEGINNER,
        language=SupportedLanguage.EN,
        estimated_minutes=15,
        external_url="https://example.com/vars",
    )
    unseen_res = CandidateResource(
        resource_id=uuid4(),
        topic_id=topic_id,
        topic_name="Variables & Data Types",
        topic_display_order=1,
        title="Dynamic Python Strings Exercise",
        description="Hands-on practice with Python strings and numeric precision.",
        content_type=ContentType.EXERCISE,
        difficulty=DifficultyLevel.BEGINNER,
        language=SupportedLanguage.EN,
        estimated_minutes=20,
        external_url="https://example.com/strings",
    )
    cbf = ContentBasedRecommender().fit([base_res])
    assert cbf._tfidf_matrix is not None
    original_rows = cbf._tfidf_matrix.shape[0]
    original_keys = set(cbf._index_by_resource_id.keys())

    ctx = StudentRecommendationContext(
        student_id=uuid4(),
        experience_level=ExperienceLevel.BEGINNER,
        learning_goal="PYTHON_FUNDAMENTALS",
        preferred_formats=[ContentType.VIDEO, ContentType.EXERCISE],
        preferred_language=SupportedLanguage.EN,
    )
    scores = cbf.compute_cbf_scores([base_res, unseen_res], ctx)
    assert base_res.resource_id in scores
    assert unseen_res.resource_id in scores
    assert 0.0 <= scores[unseen_res.resource_id][0] <= 1.0
    # Cached matrix and index map remain immutable for safe multi-threaded sharing
    assert cbf._tfidf_matrix.shape[0] == original_rows
    assert set(cbf._index_by_resource_id.keys()) == original_keys


