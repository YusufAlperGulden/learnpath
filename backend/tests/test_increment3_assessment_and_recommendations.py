"""Increment 3 test suite: atomic assessments, skipped questions, DAG locks, and rule recommender."""

import time
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import create_access_token
from app.models.assessment import Answer, TestAttempt
from app.models.catalog import Question, Topic
from app.models.user import User
from scripts.seed_data import seed_database
from tests.test_foundation import client, db_session  # noqa: F401


def _auth_headers_for_email(db: Session, email: str, role: UserRole) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    token = create_access_token(user_id=user.user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


def test_stateless_question_delivery_hides_answers_and_writes_zero_draft_rows(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    seed_database(db_session)
    student_headers = _auth_headers_for_email(
        db_session, "student@learnpath.local", UserRole.STUDENT
    )

    res = client.get(
        "/api/v1/assessments/questions?test_type=DIAGNOSTIC",
        headers=student_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["test_type"] == "DIAGNOSTIC"
    assert len(body["questions"]) == 12  # 2 stratified questions across 6 topics

    # Strict FR03 check: answer key & explanation must NEVER appear before submission
    raw_text = res.text
    assert "correct_option" not in raw_text
    assert "explanation" not in raw_text

    # Zero draft TestAttempt rows in DB prior to submission
    attempt_count = db_session.scalar(select(func.count()).select_from(TestAttempt))
    assert attempt_count == 0


def test_malformed_or_tampered_submissions_return_422_without_orphan_rows(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    seed_database(db_session)
    student_headers = _auth_headers_for_email(
        db_session, "student@learnpath.local", UserRole.STUDENT
    )

    packet = client.get(
        "/api/v1/assessments/questions?test_type=DIAGNOSTIC",
        headers=student_headers,
    ).json()

    # 1. Invalid option value 'E' -> HTTP 422
    bad_opt = client.post(
        "/api/v1/assessments/submit",
        headers=student_headers,
        json={
            "attempt_id": packet["attempt_id"],
            "test_session_token": packet["test_session_token"],
            "answers": [
                {"question_id": q["question_id"], "selected_option": "E"}
                for q in packet["questions"]
            ],
        },
    )
    assert bad_opt.status_code == 422

    # 2. Missing question from answers array -> HTTP 422
    partial = client.post(
        "/api/v1/assessments/submit",
        headers=student_headers,
        json={
            "attempt_id": packet["attempt_id"],
            "test_session_token": packet["test_session_token"],
            "answers": [
                {"question_id": q["question_id"], "selected_option": None}
                for q in packet["questions"][:-1]
            ],
        },
    )
    assert partial.status_code == 422

    # 3. Forged attempt_id mismatching signed token -> HTTP 422 (blocks token replay)
    forged_attempt = client.post(
        "/api/v1/assessments/submit",
        headers=student_headers,
        json={
            "attempt_id": str(uuid4()),
            "test_session_token": packet["test_session_token"],
            "answers": [
                {"question_id": q["question_id"], "selected_option": None}
                for q in packet["questions"]
            ],
        },
    )
    assert forged_attempt.status_code == 422

    assert db_session.scalar(select(func.count()).select_from(TestAttempt)) == 0


def test_atomic_submit_skipped_answers_idempotency_mid_exam_edit_and_latency_budget(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    seed_database(db_session)
    student_headers = _auth_headers_for_email(
        db_session, "student@learnpath.local", UserRole.STUDENT
    )
    admin_headers = _auth_headers_for_email(
        db_session, "admin@learnpath.local", UserRole.ADMIN
    )

    packet = client.get(
        "/api/v1/assessments/questions?test_type=DIAGNOSTIC",
        headers=student_headers,
    ).json()

    # Lookup ground-truth correct options from DB so we can craft exact test scores:
    # - Variables: 2/2 correct -> 100% (MASTERED)
    # - Operators: 0/2 (1 wrong, 1 skipped) -> 0% (NEEDS_PRACTICE)
    # - Remaining topics: skipped (selected_option = None)
    q_models = {
        str(q.question_id): q
        for q in db_session.scalars(select(Question)).all()
    }
    vars_topic = db_session.scalar(select(Topic).where(Topic.slug == "variables"))
    ops_topic = db_session.scalar(select(Topic).where(Topic.slug == "operators"))
    cond_topic = db_session.scalar(select(Topic).where(Topic.slug == "conditionals"))
    assert vars_topic and ops_topic and cond_topic

    # Simulate an admin editing one served question WHILE student is mid-exam
    first_qid = packet["questions"][0]["question_id"]
    admin_edit = client.put(
        f"/api/v1/admin/questions/{first_qid}",
        headers=admin_headers,
        json={"explanation": "Updated explanation while student session is active."},
    )
    assert admin_edit.status_code == 200

    answers_payload = []
    ops_seen = 0
    for q in packet["questions"]:
        qid = q["question_id"]
        model = q_models[qid]
        if model.topic_id == vars_topic.topic_id:
            choice = model.correct_option
        elif model.topic_id == ops_topic.topic_id and ops_seen == 0:
            ops_seen += 1
            choice = "A" if model.correct_option != "A" else "B"  # intentionally wrong
        else:
            choice = None  # intentionally skipped
        answers_payload.append({"question_id": qid, "selected_option": choice})

    submit_body = {
        "attempt_id": packet["attempt_id"],
        "test_session_token": packet["test_session_token"],
        "answers": answers_payload,
    }

    # Measure NFR-05 end-to-end server budget: submit + recommendations < 2.0s
    t0 = time.perf_counter()
    submit_res = client.post(
        "/api/v1/assessments/submit",
        headers=student_headers,
        json=submit_body,
    )
    rec_res = client.get(
        "/api/v1/recommendations?strategy=rule_based&limit=5",
        headers=student_headers,
    )
    elapsed_sec = time.perf_counter() - t0
    assert elapsed_sec < 2.0, f"NFR-05 budget exceeded: {elapsed_sec:.3f}s"

    assert submit_res.status_code == 200
    detail = submit_res.json()
    # 2 correct out of 12 = 16.67%
    assert detail["overall_score_percent"] == 16.67
    assert any(a["is_skipped"] and a["selected_option"] is None for a in detail["answers"])
    assert all("explanation" in a and a["explanation"] for a in detail["answers"])

    # Verify DB stored NULL selected_option & is_correct=False on skipped rows
    skipped_db_rows = db_session.scalars(
        select(Answer).where(
            Answer.attempt_id == detail["attempt_id"]  # type: ignore[arg-type]
            if False
            else Answer.selected_option.is_(None)
        )
    ).all()
    assert len(skipped_db_rows) == 9
    assert all(row.is_correct is False for row in skipped_db_rows)

    # Idempotency check: submitting the exact same payload twice does NOT duplicate TestAttempt
    retry_res = client.post(
        "/api/v1/assessments/submit",
        headers=student_headers,
        json=submit_body,
    )
    assert retry_res.status_code == 200
    assert retry_res.json()["attempt_id"] == detail["attempt_id"]
    assert db_session.scalar(select(func.count()).select_from(TestAttempt)) == 1

    # Verify DAG lock state: Variables is MASTERED -> Operators is UNLOCKED, Conditionals is LOCKED
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["strategy_used"] == "rule_based"
    # Operators (0% NEEDS_PRACTICE, unlocked) must be the top priority topic!
    assert rec_data["priority_topics"][0]["topic_id"] == str(ops_topic.topic_id)
    assert len(rec_data["items"]) == 5
    assert all("rationale" in item and len(item["rationale"]) > 20 for item in rec_data["items"])

    # Taking TOPIC_QUIZ on locked Conditionals returns HTTP 403
    locked_quiz = client.get(
        f"/api/v1/assessments/questions?test_type=TOPIC_QUIZ&target_topic_id={cond_topic.topic_id}",
        headers=student_headers,
    )
    assert locked_quiz.status_code == 403

    # Taking TOPIC_QUIZ on unlocked Operators succeeds with 6 questions
    unlocked_quiz = client.get(
        f"/api/v1/assessments/questions?test_type=TOPIC_QUIZ&target_topic_id={ops_topic.topic_id}",
        headers=student_headers,
    )
    assert unlocked_quiz.status_code == 200
    assert len(unlocked_quiz.json()["questions"]) == 6

    # Requesting recommendations on locked Conditionals redirects to unlocked prerequisite Operators!
    locked_rec = client.get(
        f"/api/v1/recommendations?topic_id={cond_topic.topic_id}",
        headers=student_headers,
    ).json()
    assert locked_rec["fallback_applied"] is True
    assert locked_rec["fallback_reason"] == "prerequisite_not_mastered"
    assert [p["topic_id"] for p in locked_rec["priority_topics"]] == [str(ops_topic.topic_id)]


def test_format_relaxation_fallback_when_preferred_format_unavailable(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    seed_database(db_session)
    student_headers = _auth_headers_for_email(
        db_session, "student@learnpath.local", UserRole.STUDENT
    )

    vars_topic = db_session.scalar(select(Topic).where(Topic.slug == "variables"))
    assert vars_topic is not None

    # In seeded Variables, Turkish ('tr') has VIDEO + EXERCISE, and 0 ARTICLE resources.
    prof_res = client.put(
        "/api/v1/profile",
        headers=student_headers,
        json={
            "display_name": "Turkish Article Learner",
            "learning_goal": "PYTHON_FUNDAMENTALS",
            "experience_level": "BEGINNER",
            "preferred_formats": ["ARTICLE"],
            "preferred_language": "tr",
        },
    )
    assert prof_res.status_code == 200

    rec_res = client.get(
        f"/api/v1/recommendations?topic_id={vars_topic.topic_id}&limit=5",
        headers=student_headers,
    )
    assert rec_res.status_code == 200
    rec_body = rec_res.json()
    assert rec_body["fallback_applied"] is True
    assert rec_body["fallback_reason"] == "preferred_format_relaxed"
    assert len(rec_body["items"]) == 2
    assert all(item["language"] == "tr" for item in rec_body["items"])
    assert all(item["format_fallback_used"] is True for item in rec_body["items"])
    assert all("format relaxation" in item["rationale"] for item in rec_body["items"])
