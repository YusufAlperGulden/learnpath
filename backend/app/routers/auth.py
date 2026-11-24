"""Authentication and session endpoints: register, login, and me (FR01, NFR-14)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.enums import UserRole
from app.core.logging_config import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger("auth")


def _to_user_read(user: User) -> UserRead:
    return UserRead(
        user_id=user.user_id,
        email=user.email,
        role=UserRole(user.role),
        has_profile=user.profile is not None,
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_student(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    normalized_email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # Profile row is created on PUT /api/v1/profile so has_profile=False drives UC01 onboarding
    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        role=UserRole.STUDENT.value,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        ) from exc
    db.refresh(user)

    access_token = create_access_token(user_id=user.user_id, role=UserRole.STUDENT)
    logger.info("Registered new student user_id=%s", user.user_id)
    return TokenResponse(
        access_token=access_token,
        user=UserRead(
            user_id=user.user_id,
            email=user.email,
            role=UserRole.STUDENT,
            has_profile=False,
            created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    normalized_email = payload.email.strip().lower()
    stmt = (
        select(User)
        .options(selectinload(User.profile))
        .where(func.lower(User.email) == normalized_email)
    )
    user = db.scalar(stmt)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = UserRole(user.role)
    access_token = create_access_token(user_id=user.user_id, role=role)
    logger.info("Authenticated user_id=%s role=%s", user.user_id, role.value)
    return TokenResponse(access_token=access_token, user=_to_user_read(user))


@router.get("/me", response_model=UserRead)
def read_current_session(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    return _to_user_read(current_user)
