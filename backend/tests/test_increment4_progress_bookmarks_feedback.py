"""Increment 4 test suite: dual progress, OPENED vs COMPLETED, bookmarks, feedback, and e2e flow."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import create_access_token
from app.models.catalog import Question, Topic
from app.models.progress import Feedback, SavedResource
from app.models.user import User
from scripts.seed_data import seed_database
from tests.test_foundation import client, db_session  # noqa: F401


def _headers(db: Session, email: str, role: UserRole) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    token = create_access_token(user_id=user.user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


def test_manual_topic_completion_never_bypasses_exam_mastery_prerequisite_lock(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    seed_database(db_session)
    student_headers = _headers(db_session, "student@learnpath.local", UserRole.STUDENT)

    vars_topic = db_session.scalar(select(Topic).where(Topic.slug == "variables"))
    ops_topic = db_session.scalar(select(Topic).where(Topic.slug == "operators"))
    assert vars_topic and ops_topic

    # 1. Manually complete Variables without taking an exam
    toggle_res = client.put(
        f"/api/v1/progress/topics/{vars_topic.topic_id}",
        headers=student_headers,
        json={"is_manually_completed": True},
    )
    assert toggle_res.status_code == 200
    body = toggle_res.json()
    assert body["is_manually_completed"] is True
    assert body["manually_completed_at"] is not None
    assert body["mastery_status"] == "UNKNOWN"
    assert body["latest_score_percent"] is None

    # 2. Operators MUST remain locked because Variables mastery_status != MASTERED
    lp = client.get("/api/v1/learning-path", headers=student_headers).json()
    nodes_by_slug = {n["slug"]: n for n in lp["nodes"]}
    assert nodes_by_slug["variables"]["is_manually_completed"] is True
    assert nodes_by_slug["operators"]["is_locked"] is True

    locked_quiz = client.get(
        f"/api/v1/assessments/questions?test_type=TOPIC_QUIZ&target_topic_id={ops_topic.topic_id}",
        headers=student_headers,
    )
    assert locked_quiz.status_code == 403

    # 3. Pass Variables TOPIC_QUIZ (100% >= 70%) -> unlocks Operators while preserving manual flag
    quiz_packet = client.get(
        f"/api/v1/assessments/questions?test_type=TOPIC_QUIZ&target_topic_id={vars_topic.topic_id}",
        headers=student_headers,
    ).json()
    q_by_id = {str(q.question_id): q for q in db_session.scalars(select(Question)).all()}

    pass_submit = client.post(
        "/api/v1/assessments/submit",
        headers=student_headers,
        json={
            "attempt_id": quiz_packet["attempt_id"],
            "test_session_token": quiz_packet["test_session_token"],
            "answers": [
                {
                    "question_id": q["question_id"],
                    "selected_option": q_by_id[q["question_id"]].correct_option,
                }
                for q in quiz_packet["questions"]
            ],
        },
    )
    assert pass_submit.status_code == 200

    lp_after_pass = client.get("/api/v1/learning-path", headers=student_headers).json()
    after_nodes = {n["slug"]: n for n in lp_after_pass["nodes"]}
    assert after_nodes["variables"]["mastery_status"] == "MASTERED"
    assert after_nodes["variables"]["is_manually_completed"] is True
    assert after_nodes["operators"]["is_locked"] is False

    # 4. Retake Variables TOPIC_QUIZ with 0% -> recalculates to NEEDS_PRACTICE & re-locks Operators
    retake_packet = client.get(
        f"/api/v1/assessments/questions?test_type=TOPIC_QUIZ&target_topic_id={vars_topic.topic_id}",
        headers=student_headers,
    ).json()
    fail_submit = client.post(
        "/api/v1/assessments/submit",
        headers=student_headers,
        json={
            "attempt_id": retake_packet["attempt_id"],
            "test_session_token": retake_packet["test_session_token"],
            "answers": [
                {"question_id": q["question_id"], "selected_option": None}
                for q in retake_packet["questions"]
            ],
        },
    )
    assert fail_submit.status_code == 200

    lp_after_fail = client.get("/api/v1/learning-path", headers=student_headers).json()
    fail_nodes = {n["slug"]: n for n in lp_after_fail["nodes"]}
    assert fail_nodes["variables"]["mastery_status"] == "NEEDS_PRACTICE"
    assert fail_nodes["variables"]["is_manually_completed"] is True
    assert fail_nodes["operators"]["is_locked"] is True


def test_opened_vs_completed_resource_progress_and_recommendation_rotation(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    seed_database(db_session)
    student_headers = _headers(db_session, "student@learnpath.local", UserRole.STUDENT)

    initial_recs = client.get(
        "/api/v1/recommendations?limit=5",
        headers=student_headers,
    ).json()
    top_res_id = initial_recs["items"][0]["resource_id"]

    # 1. Opening an external link marks OPENED and keeps it in recommendations
    open_res = client.post(
        f"/api/v1/progress/resources/{top_res_id}/open",
        headers=student_headers,
    )
    assert open_res.status_code == 200
    assert open_res.json()["status"] == "OPENED"

    after_open_recs = client.get(
        "/api/v1/recommendations?limit=5",
        headers=student_headers,
    ).json()
    top_after_open = next(
        item for item in after_open_recs["items"] if item["resource_id"] == top_res_id
    )
    assert top_after_open["progress_status"] == "OPENED"

    # 2. Marking COMPLETED rotates the resource out of unseen recommendations
    comp_res = client.put(
        f"/api/v1/progress/resources/{top_res_id}",
        headers=student_headers,
        json={"status": "COMPLETED"},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"
    assert comp_res.json()["completed_at"] is not None

    # 3. Re-opening an already COMPLETED resource refreshes access timestamp without demoting status
    reopen_click = client.post(
        f"/api/v1/progress/resources/{top_res_id}/open",
        headers=student_headers,
    )
    assert reopen_click.status_code == 200
    assert reopen_click.json()["status"] == "COMPLETED"

    after_comp_recs = client.get(
        "/api/v1/recommendations?limit=5",
        headers=student_headers,
    ).json()
    returned_ids = {item["resource_id"] for item in after_comp_recs["items"]}
    assert top_res_id not in returned_ids

    # 4. Explicit revision action (?include_completed=true) re-offers completed items (RAD 3.4.4.3)
    revision_recs = client.get(
        "/api/v1/recommendations?limit=5&include_completed=true",
        headers=student_headers,
    ).json()
    revision_ids = {item["resource_id"] for item in revision_recs["items"]}
    assert top_res_id in revision_ids

    history = client.get(
        "/api/v1/progress/resources/history",
        headers=student_headers,
    ).json()
    assert len(history) == 1
    assert history[0]["resource_id"] == top_res_id
    assert history[0]["status"] == "COMPLETED"


def test_bookmarks_idempotency_soft_delete_resilience_and_feedback_upsert(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    seed_database(db_session)
    student_headers = _headers(db_session, "student@learnpath.local", UserRole.STUDENT)
    admin_headers = _headers(db_session, "admin@learnpath.local", UserRole.ADMIN)

    recs = client.get("/api/v1/recommendations?limit=5", headers=student_headers).json()
    res_id = recs["items"][0]["resource_id"]

    # 1. Bookmarking twice is idempotent on composite PK (student_id, resource_id)
    b1 = client.post(
        "/api/v1/bookmarks",
        headers=student_headers,
        json={"resource_id": res_id},
    )
    b2 = client.post(
        "/api/v1/bookmarks",
        headers=student_headers,
        json={"resource_id": res_id},
    )
    assert b1.status_code == 201
    assert b2.status_code == 201
    assert db_session.scalar(select(func.count()).select_from(SavedResource)) == 1

    # 2. Rating validation (0 and 6 rejected with HTTP 422)
    bad_low = client.put(
        "/api/v1/feedback",
        headers=student_headers,
        json={"resource_id": res_id, "rating": 0},
    )
    bad_high = client.put(
        "/api/v1/feedback",
        headers=student_headers,
        json={"resource_id": res_id, "rating": 6},
    )
    assert bad_low.status_code == 422
    assert bad_high.status_code == 422

    # 3. Valid 1..5 rating upsert updates single row on (student_id, resource_id)
    fb1 = client.post(
        "/api/v1/feedback",
        headers=student_headers,
        json={"resource_id": res_id, "rating": 4, "comment": "Helpful intro"},
    )
    assert fb1.status_code == 200
    assert fb1.json()["rating"] == 4

    fb2 = client.put(
        "/api/v1/feedback",
        headers=student_headers,
        json={"resource_id": res_id, "rating": 5, "comment": "Mastered topic thanks to this!"},
    )
    assert fb2.status_code == 200
    assert fb2.json()["rating"] == 5
    assert db_session.scalar(select(func.count()).select_from(Feedback)) == 1

    # 4. Admin soft-deactivates the resource -> student's bookmark & rating still load cleanly!
    deact = client.delete(f"/api/v1/admin/resources/{res_id}", headers=admin_headers)
    assert deact.status_code == 200

    bookmarks = client.get("/api/v1/bookmarks", headers=student_headers).json()
    assert len(bookmarks) == 1
    assert bookmarks[0]["resource_id"] == res_id
    assert bookmarks[0]["is_active"] is False
    assert bookmarks[0]["my_rating"] == 5

    # 5. Removing bookmark is idempotent
    del1 = client.delete(f"/api/v1/bookmarks/{res_id}", headers=student_headers)
    del2 = client.delete(f"/api/v1/bookmarks/{res_id}", headers=student_headers)
    assert del1.status_code == 204
    assert del2.status_code == 204
    assert client.get("/api/v1/bookmarks", headers=student_headers).json() == []
