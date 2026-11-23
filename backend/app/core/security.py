"""Argon2 password hashing, RBAC access JWTs, and stateless exam session tokens."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.enums import TestType, UserRole

password_hasher = PasswordHash.recommended()


class TokenValidationError(Exception):
    """Raised when an access or test-session JWT fails verification."""


def hash_password(plain_password: str) -> str:
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_hasher.verify(plain_password, password_hash)


def create_access_token(
    user_id: UUID,
    role: UserRole,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "token_type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise TokenValidationError("Invalid or expired authentication token.") from exc

    if payload.get("token_type") != "access" or "sub" not in payload or "role" not in payload:
        raise TokenValidationError("Invalid access token claims.")
    return payload


def create_test_session_token(
    *,
    student_id: UUID,
    attempt_id: UUID,
    test_type: TestType,
    target_topic_id: UUID | None,
    question_ids: list[UUID],
    started_at: datetime | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Issues a signed, stateless exam session token (RAD v2.0 Section 3.3).

    Binding `attempt_id`, `student_id`, and `question_ids` inside the signed JWT
    prevents draft-row pollution on GET while blocking token replay and question
    cherry-picking on POST /assessments/submit.
    """
    issued_at = started_at if started_at is not None else datetime.now(UTC)
    expire = issued_at + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.TEST_SESSION_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(student_id),
        "attempt_id": str(attempt_id),
        "test_type": test_type.value,
        "target_topic_id": str(target_topic_id) if target_topic_id else None,
        "question_ids": [str(qid) for qid in question_ids],
        "started_at": issued_at.isoformat(),
        "token_type": "test_session",
        "iat": int(issued_at.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_test_session_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise TokenValidationError("Invalid or expired test session token.") from exc

    required_keys = {"sub", "attempt_id", "test_type", "question_ids", "started_at"}
    if payload.get("token_type") != "test_session" or not required_keys.issubset(payload):
        raise TokenValidationError("Malformed test session token claims.")
    return payload
