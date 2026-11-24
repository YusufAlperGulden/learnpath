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

