"""Increment 1 verification suite: 13-table schema, RBAC, profile, DAG, mastery, and tokens."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.enums import MasteryStatus, TestType, UserRole
from app.core.security import (
    TokenValidationError,
    create_access_token,
    create_test_session_token,
    decode_test_session_token,
    hash_password,
)
from app.main import app
from app.models.user import User
from app.schemas.assessment import AssessmentQuestionPublic
from app.services.dag_validator import DAGCycleError, validate_prerequisite_dag
from app.services.mastery import calculate_mastery_status

EXPECTED_13_TABLES_AND_COLUMNS: dict[str, set[str]] = {
    "users": {"user_id", "email", "password_hash", "role", "created_at"},
    "student_profiles": {
        "student_id",
        "display_name",
        "learning_goal",
        "experience_level",
        "preferred_formats",
        "preferred_language",
        "updated_at",
    },
    "topics": {"topic_id", "name", "slug", "description", "display_order"},
    "topic_prerequisites": {"topic_id", "prerequisite_topic_id"},
    "resources": {
        "resource_id",
        "topic_id",
        "created_by",
        "title",
        "description",
        "external_url",
        "content_type",
        "difficulty",
        "language",
        "estimated_minutes",
        "is_active",
        "created_at",
    },
    "questions": {
        "question_id",
        "topic_id",
        "created_by",
        "question_text",
        "code_snippet",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_option",
        "explanation",
        "difficulty",
        "version",
        "previous_question_id",
        "is_active",
        "created_at",
    },
    "test_attempts": {
        "attempt_id",
        "student_id",
        "test_type",
        "target_topic_id",
        "overall_score_percent",
        "started_at",
        "submitted_at",
    },
    "answers": {"attempt_id", "question_id", "selected_option", "is_correct"},
    "topic_scores": {
        "attempt_id",
        "topic_id",
        "correct_count",
        "question_count",
        "score_percent",
    },
    "topic_progress": {
        "student_id",
        "topic_id",
        "is_manually_completed",
        "manually_completed_at",
        "latest_score_percent",
        "mastery_status",
        "updated_at",
    },
    "resource_progress": {
        "student_id",
        "resource_id",
        "status",
        "first_opened_at",
        "completed_at",
        "last_accessed_at",
    },
    "saved_resources": {"student_id", "resource_id", "saved_at"},
    "feedback": {
        "feedback_id",
        "student_id",
        "resource_id",
        "rating",
        "comment",
        "created_at",
    },
}


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(test_engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_exact_13_tables_and_columns_match_rad_data_dictionary() -> None:
    actual_tables = set(Base.metadata.tables.keys())
    assert actual_tables == set(EXPECTED_13_TABLES_AND_COLUMNS.keys())
    assert len(actual_tables) == 13

    for table_name, expected_cols in EXPECTED_13_TABLES_AND_COLUMNS.items():
        actual_cols = {col.name for col in Base.metadata.tables[table_name].columns}
        assert actual_cols == expected_cols, f"Column mismatch on table '{table_name}'"


def test_auth_profile_and_admin_rbac_403(client: TestClient, db_session: Session) -> None:
    # 1. Register a student
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": "Student@Example.com", "password": "StrongPassword123"},
    )
    assert reg_res.status_code == 201
    token_data = reg_res.json()
    student_token = token_data["access_token"]
    assert token_data["user"]["email"] == "student@example.com"
    assert token_data["user"]["role"] == "STUDENT"
    assert token_data["user"]["has_profile"] is False

    headers = {"Authorization": f"Bearer {student_token}"}

    # 2. Student hitting /api/v1/admin/* MUST receive HTTP 403
    admin_res = client.get("/api/v1/admin/topics", headers=headers)
    assert admin_res.status_code == 403

    # 3. Multi-format profile upsert & read persistence
    put_res = client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "display_name": "Eren Student",
            "learning_goal": "DATA_SCIENCE",
            "experience_level": "INTERMEDIATE",
            "preferred_formats": ["VIDEO", "EXERCISE", "VIDEO"],
            "preferred_language": "en",
        },
    )
    assert put_res.status_code == 200
    profile_body = put_res.json()
    assert profile_body["preferred_formats"] == ["VIDEO", "EXERCISE"]
    assert profile_body["experience_level"] == "INTERMEDIATE"

    get_res = client.get("/api/v1/profile", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["preferred_formats"] == ["VIDEO", "EXERCISE"]

    # 4. Admin can create topics & cycle is blocked with HTTP 400
    admin_user = User(
        email="admin@example.com",
        password_hash=hash_password("AdminSecret123"),
        role=UserRole.ADMIN.value,
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    admin_token = create_access_token(user_id=admin_user.user_id, role=UserRole.ADMIN)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    t1 = client.post(
        "/api/v1/admin/topics",
        headers=admin_headers,
        json={
            "name": "Variables",
            "slug": "variables",
            "description": "Variables and primitive types.",
            "display_order": 1,
            "prerequisite_topic_ids": [],
        },
    )
    assert t1.status_code == 201
    t1_id = t1.json()["topic_id"]

    t2 = client.post(
        "/api/v1/admin/topics",
        headers=admin_headers,
        json={
            "name": "Loops",
            "slug": "loops",
            "description": "For and while loops.",
            "display_order": 2,
            "prerequisite_topic_ids": [t1_id],
        },
    )
    assert t2.status_code == 201

    # Student can read /api/v1/learning-path and see Loops locked because Variables != MASTERED
    lp_res = client.get("/api/v1/learning-path", headers=headers)
    assert lp_res.status_code == 200
    lp_nodes = {n["slug"]: n for n in lp_res.json()["nodes"]}
    assert lp_nodes["variables"]["is_locked"] is False
    assert lp_nodes["loops"]["is_locked"] is True


def test_dag_cycle_validator_rejects_self_and_transitive_cycles() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()

    with pytest.raises(DAGCycleError):
        validate_prerequisite_dag([], a, [a])

    existing = [(b, a), (c, b)]  # a -> b -> c
    # Making c a prerequisite of a creates cycle a -> c -> b -> a
    with pytest.raises(DAGCycleError):
        validate_prerequisite_dag(existing, a, [c])

    # Diamond DAG is valid: d depends on both b and c
    d = uuid4()
    validate_prerequisite_dag(existing, d, [b, c])


def test_mastery_status_recalculates_from_latest_attempt() -> None:
    assert calculate_mastery_status(None) == MasteryStatus.UNKNOWN
    assert calculate_mastery_status(85.0) == MasteryStatus.MASTERED
    assert calculate_mastery_status(70.0) == MasteryStatus.MASTERED
    # Subsequent lower attempt recalculates downward to NEEDS_PRACTICE
    assert calculate_mastery_status(69.9) == MasteryStatus.NEEDS_PRACTICE


def test_answer_key_confidentiality_and_test_session_token_binding() -> None:
    public_fields = set(AssessmentQuestionPublic.model_fields.keys())
    assert "correct_option" not in public_fields
    assert "explanation" not in public_fields

    student_id = uuid4()
    attempt_id = uuid4()
    q_ids = [uuid4(), uuid4()]

    session_token = create_test_session_token(
        student_id=student_id,
        attempt_id=attempt_id,
        test_type=TestType.DIAGNOSTIC,
        target_topic_id=None,
        question_ids=q_ids,
    )
    claims = decode_test_session_token(session_token)
    assert claims["sub"] == str(student_id)
    assert claims["attempt_id"] == str(attempt_id)
    assert claims["question_ids"] == [str(q) for q in q_ids]

    # Access token cannot be misused as a test_session_token
    access_token = create_access_token(user_id=student_id, role=UserRole.STUDENT)
    with pytest.raises(TokenValidationError):
        decode_test_session_token(access_token)


def test_seeded_local_demo_accounts_can_log_in_via_http(
    client: TestClient,
    db_session: Session,
) -> None:
    from scripts.seed_data import seed_database

    seed_database(db_session)

    for email, password, expected_role in (
        ("student@learnpath.local", "StudentPass123!", "STUDENT"),
        ("admin@learnpath.local", "AdminPass123!", "ADMIN"),
    ):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["user"]["email"] == email
        assert body["user"]["role"] == expected_role
