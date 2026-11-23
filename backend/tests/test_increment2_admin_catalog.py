"""Increment 2 test suite: DAG cycle updates, soft-deactivation, question versioning, and seed data."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ResourceProgressStatus, TestType, UserRole
from app.core.security import create_access_token, hash_password
from app.models.assessment import Answer, TestAttempt
from app.models.catalog import Question, Resource
from app.models.progress import Feedback, ResourceProgress, SavedResource
from app.models.user import User
from app.services.dag_validator import get_catalog_generation
from scripts.seed_data import seed_database
from tests.test_foundation import client, db_session  # noqa: F401


def _create_admin_and_student(db: Session) -> tuple[User, dict[str, str], User]:
    admin = User(
        email="admin-inc2@learnpath.local",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN.value,
    )
    student = User(
        email="student-inc2@learnpath.local",
        password_hash=hash_password("StudentPass123!"),
        role=UserRole.STUDENT.value,
    )
    db.add_all([admin, student])
    db.commit()
    db.refresh(admin)
    db.refresh(student)

    token = create_access_token(user_id=admin.user_id, role=UserRole.ADMIN)
    return admin, {"Authorization": f"Bearer {token}"}, student


def test_admin_topic_dag_update_cycle_rejection_and_safe_delete(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    _, admin_headers, _ = _create_admin_and_student(db_session)

    t_vars = client.post(
        "/api/v1/admin/topics",
        headers=admin_headers,
        json={
            "name": "Variables",
            "slug": "variables",
            "description": "Variables and primitive types.",
            "display_order": 1,
            "prerequisite_topic_ids": [],
        },
    ).json()

    t_ops = client.post(
        "/api/v1/admin/topics",
        headers=admin_headers,
        json={
            "name": "Operators",
            "slug": "operators",
            "description": "Arithmetic and boolean operators.",
            "display_order": 2,
            "prerequisite_topic_ids": [t_vars["topic_id"]],
        },
    ).json()

    t_cond = client.post(
        "/api/v1/admin/topics",
        headers=admin_headers,
        json={
            "name": "Conditionals",
            "slug": "conditionals",
            "description": "If, elif, else branching.",
            "display_order": 3,
            "prerequisite_topic_ids": [t_ops["topic_id"]],
        },
    ).json()

    # Attempting to make Variables depend on Conditionals creates Variables -> Conditionals -> Operators -> Variables
    cycle_res = client.put(
        f"/api/v1/admin/topics/{t_vars['topic_id']}",
        headers=admin_headers,
        json={"prerequisite_topic_ids": [t_cond["topic_id"]]},
    )
    assert cycle_res.status_code == 400
    assert "Circular prerequisite" in cycle_res.json()["detail"]

    # Deleting Variables fails with 409 because Operators depends on it
    del_conflict = client.delete(
        f"/api/v1/admin/topics/{t_vars['topic_id']}",
        headers=admin_headers,
    )
    assert del_conflict.status_code == 409

    # Deleting an unreferenced topic succeeds with 204
    t_leaf = client.post(
        "/api/v1/admin/topics",
        headers=admin_headers,
        json={
            "name": "Optional Appendix",
            "slug": "optional-appendix",
            "description": "Standalone optional reading.",
            "display_order": 99,
            "prerequisite_topic_ids": [],
        },
    ).json()
    del_ok = client.delete(
        f"/api/v1/admin/topics/{t_leaf['topic_id']}",
        headers=admin_headers,
    )
    assert del_ok.status_code == 204


def test_resource_crud_duplicate_url_409_and_fk_safe_soft_deactivation(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    _, admin_headers, student = _create_admin_and_student(db_session)

    topic = client.post(
        "/api/v1/admin/topics",
        headers=admin_headers,
        json={
            "name": "Loops",
            "slug": "loops",
            "description": "For and while iteration.",
            "display_order": 1,
            "prerequisite_topic_ids": [],
        },
    ).json()

    gen_before = get_catalog_generation()

    created = client.post(
        "/api/v1/admin/resources",
        headers=admin_headers,
        json={
            "topic_id": topic["topic_id"],
            "title": "Python Loops Deep Dive",
            "description": "Comprehensive video on for/while loops, break, continue, and range.",
            "external_url": "https://example.org/python-loops-guide",
            "content_type": "VIDEO",
            "difficulty": "BEGINNER",
            "language": "en",
            "estimated_minutes": 18,
        },
    )
    assert created.status_code == 201
    res_data = created.json()
    res_id = res_data["resource_id"]
    assert get_catalog_generation() > gen_before

    # Duplicate URL must return HTTP 409 Conflict
    dup = client.post(
        "/api/v1/admin/resources",
        headers=admin_headers,
        json={
            "topic_id": topic["topic_id"],
            "title": "Duplicate URL Attempt",
            "description": "Another description trying to reuse the exact same external URL.",
            "external_url": "https://example.org/python-loops-guide",
            "content_type": "ARTICLE",
            "difficulty": "INTERMEDIATE",
            "language": "en",
            "estimated_minutes": 12,
        },
    )
    assert dup.status_code == 409
    assert "Duplicate URL" in dup.json()["detail"]

    # Attach student bookmark, resource progress, and rating to verify FK preservation
    resource_orm = db_session.scalar(
        select(Resource).where(Resource.resource_id == res_data["resource_id"])  # type: ignore[arg-type]
        if False
        else select(Resource)
    )
    assert resource_orm is not None
    db_session.add_all(
        [
            SavedResource(student_id=student.user_id, resource_id=resource_orm.resource_id),
            ResourceProgress(
                student_id=student.user_id,
                resource_id=resource_orm.resource_id,
                status=ResourceProgressStatus.OPENED.value,
            ),
            Feedback(
                student_id=student.user_id,
                resource_id=resource_orm.resource_id,
                rating=5,
                comment="Very clear explanation!",
            ),
        ]
    )
    db_session.commit()

    # DELETE soft-deactivates (is_active=False) without breaking student history
    deact = client.delete(f"/api/v1/admin/resources/{res_id}", headers=admin_headers)
    assert deact.status_code == 200
    assert deact.json()["is_active"] is False

    active_list = client.get(
        "/api/v1/admin/resources?is_active=true",
        headers=admin_headers,
    ).json()
    assert len(active_list) == 0

    assert (
        db_session.get(SavedResource, (student.user_id, resource_orm.resource_id)) is not None
    )
    assert (
        db_session.get(ResourceProgress, (student.user_id, resource_orm.resource_id)) is not None
    )
    assert (
        db_session.scalar(
            select(Feedback).where(Feedback.resource_id == resource_orm.resource_id)
        )
        is not None
    )

    # Reactivate via PATCH /status
    react = client.patch(
        f"/api/v1/admin/resources/{res_id}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert react.status_code == 200
    assert react.json()["is_active"] is True


def test_question_versioning_preserves_historical_answers_on_edit(
    client: TestClient,  # noqa: F811
    db_session: Session,  # noqa: F811
) -> None:
    _, admin_headers, student = _create_admin_and_student(db_session)

    topic = client.post(
        "/api/v1/admin/topics",
        headers=admin_headers,
        json={
            "name": "Functions",
            "slug": "functions",
            "description": "Parameters, return values, and scope.",
            "display_order": 1,
            "prerequisite_topic_ids": [],
        },
    ).json()

    # 1. Create v1 question
    q_create = client.post(
        "/api/v1/admin/questions",
        headers=admin_headers,
        json={
            "topic_id": topic["topic_id"],
            "question_text": "What does a function without a return statement return?",
            "code_snippet": "def noop():\n    pass",
            "option_a": "0",
            "option_b": "None",
            "option_c": "False",
            "option_d": "''",
            "correct_option": "B",
            "explanation": "Functions without an explicit return value implicitly return None.",
            "difficulty": "BEGINNER",
        },
    )
    assert q_create.status_code == 201
    v1_id = q_create.json()["question_id"]
    assert q_create.json()["version"] == 1
    assert q_create.json()["is_answered"] is False

    # 2. Editing BEFORE any student answers updates v1 in-place
    in_place = client.put(
        f"/api/v1/admin/questions/{v1_id}",
        headers=admin_headers,
        json={"question_text": "What value does `noop()` return in Python?"},
    )
    assert in_place.status_code == 200
    assert in_place.json()["question_id"] == v1_id
    assert in_place.json()["version"] == 1

    # 3. Record a student TestAttempt + Answer referencing v1
    v1_orm = db_session.scalar(select(Question))
    assert v1_orm is not None
    attempt = TestAttempt(
        student_id=student.user_id,
        test_type=TestType.DIAGNOSTIC.value,
        target_topic_id=None,
        overall_score_percent=100.0,
        started_at=datetime.now(UTC),
    )
    db_session.add(attempt)
    db_session.flush()
    db_session.add(
        Answer(
            attempt_id=attempt.attempt_id,
            question_id=v1_orm.question_id,
            selected_option="B",
            is_correct=True,
        )
    )
    db_session.commit()

    # 4. Editing v1 AFTER it was answered must deactivate v1 untouched and mint v2
    versioned = client.put(
        f"/api/v1/admin/questions/{v1_id}",
        headers=admin_headers,
        json={
            "question_text": "What does `noop()` return when called?",
            "correct_option": "C",
            "option_b": "0",
            "option_c": "None",
        },
    )
    assert versioned.status_code == 200
    v2_body = versioned.json()
    assert v2_body["question_id"] != v1_id
    assert v2_body["version"] == 2
    assert v2_body["previous_question_id"] == v1_id
    assert v2_body["is_active"] is True
    assert v2_body["is_answered"] is False
    assert v2_body["correct_option"] == "C"

    # Verify historical v1 row & student Answer were NOT mutated
    db_session.expire_all()
    v1_after = db_session.get(Question, v1_orm.question_id)
    assert v1_after is not None
    assert v1_after.is_active is False
    assert v1_after.version == 1
    assert v1_after.correct_option == "B"
    assert v1_after.question_text == "What value does `noop()` return in Python?"

    historical_answer = db_session.get(Answer, (attempt.attempt_id, v1_orm.question_id))
    assert historical_answer is not None
    assert historical_answer.selected_option == "B"
    assert historical_answer.is_correct is True

    # 5. Lineage endpoint returns [v1, v2] in chronological order
    lineage_res = client.get(
        f"/api/v1/admin/questions/{v1_id}/lineage",
        headers=admin_headers,
    )
    assert lineage_res.status_code == 200
    lineage_items = lineage_res.json()
    assert [item["version"] for item in lineage_items] == [1, 2]
    assert lineage_items[0]["is_answered"] is True
    assert lineage_items[1]["is_answered"] is False


def test_expanded_curriculum_seed_is_complete_and_idempotent(
    db_session: Session,  # noqa: F811
) -> None:
    first_run = seed_database(db_session)
    assert first_run.topics_total == 6
    assert first_run.resources_total == 54
    assert first_run.questions_total == 36

    # Running a second time must be 100% idempotent with zero duplicate rows
    second_run = seed_database(db_session)
    assert second_run.topics_total == 6
    assert second_run.resources_total == 54
    assert second_run.questions_total == 36
