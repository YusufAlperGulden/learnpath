"""User and StudentProfile ORM models (Tables 1–2 of 13)."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import ExperienceLevel, SupportedLanguage, UserRole

if TYPE_CHECKING:
    from app.models.assessment import TestAttempt
    from app.models.progress import (
        Feedback,
        ResourceProgress,
        SavedResource,
        TopicProgress,
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('STUDENT', 'ADMIN')", name="valid_user_role"),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.STUDENT.value,
        server_default=UserRole.STUDENT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    profile: Mapped["StudentProfile | None"] = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    test_attempts: Mapped[list["TestAttempt"]] = relationship(
        "TestAttempt",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    topic_progress_items: Mapped[list["TopicProgress"]] = relationship(
        "TopicProgress",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    resource_progress_items: Mapped[list["ResourceProgress"]] = relationship(
        "ResourceProgress",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    saved_resources: Mapped[list["SavedResource"]] = relationship(
        "SavedResource",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    feedback_items: Mapped[list["Feedback"]] = relationship(
        "Feedback",
        back_populates="student",
        cascade="all, delete-orphan",
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint(
            "experience_level IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name="valid_experience_level",
        ),
        CheckConstraint(
            "preferred_language IN ('en', 'tr')",
            name="valid_preferred_language",
        ),
    )

    student_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    learning_goal: Mapped[str] = mapped_column(String(255), nullable=False)
    experience_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ExperienceLevel.BEGINNER.value,
    )
    preferred_formats: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
    )
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=SupportedLanguage.EN.value,
        server_default=SupportedLanguage.EN.value,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")
