"""Student profile read and upsert endpoints supporting multi-format JSONB (FR02)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_student
from app.core.logging_config import get_logger
from app.models.user import StudentProfile, User
from app.schemas.profile import StudentProfileRead, StudentProfileUpsert

router = APIRouter(prefix="/profile", tags=["Student Profile"])
logger = get_logger("profile")


@router.get("", response_model=StudentProfileRead)
def get_my_profile(
    current_student: Annotated[User, Depends(require_student)],
) -> StudentProfileRead:
    if current_student.profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile has not been configured yet.",
        )
    return StudentProfileRead.model_validate(current_student.profile)


@router.put("", response_model=StudentProfileRead)
def upsert_my_profile(
    payload: StudentProfileUpsert,
    current_student: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> StudentProfileRead:
    serialized_formats = [fmt.value for fmt in payload.preferred_formats]
    profile = current_student.profile

    if profile is None:
        profile = StudentProfile(
            student_id=current_student.user_id,
            display_name=payload.display_name.strip(),
            learning_goal=payload.learning_goal.strip(),
            experience_level=payload.experience_level.value,
            preferred_formats=serialized_formats,
            preferred_language=payload.preferred_language.value,
        )
        db.add(profile)
    else:
        profile.display_name = payload.display_name.strip()
        profile.learning_goal = payload.learning_goal.strip()
        profile.experience_level = payload.experience_level.value
        profile.preferred_formats = serialized_formats
        profile.preferred_language = payload.preferred_language.value
        profile.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(profile)
    logger.info(
        "Updated student profile student_id=%s level=%s formats=%s",
        current_student.user_id,
        profile.experience_level,
        serialized_formats,
    )
    return StudentProfileRead.model_validate(profile)
