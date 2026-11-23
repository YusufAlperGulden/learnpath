"""Dual progress, bookmark, and rating ORM models (Tables 10–13 of 13)."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import MasteryStatus

if TYPE_CHECKING:
    from app.models.catalog import Resource, Topic
    from app.models.user import User


class TopicProgress(Base):
    """Table 10 (13th RAD v2.0 addition): Decouples manual study tracking from exam mastery."""

    __tablename__ = "topic_progress"
    __table_args__ = (
        CheckConstraint(
            "mastery_status IN ('UNKNOWN', 'NEEDS_PRACTICE', 'MASTERED')",
            name="valid_mastery_status",
        ),
        CheckConstraint(
            "latest_score_percent IS NULL OR (latest_score_percent >= 0.0 AND latest_score_percent <= 100.0)",
            name="valid_latest_score_percent",
        ),
    )

    student_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    topic_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("topics.topic_id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_manually_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    manually_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    latest_score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    mastery_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MasteryStatus.UNKNOWN.value,
        server_default=MasteryStatus.UNKNOWN.value,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    student: Mapped["User"] = relationship("User", back_populates="topic_progress_items")
    topic: Mapped["Topic"] = relationship("Topic")


class ResourceProgress(Base):
    __tablename__ = "resource_progress"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPENED', 'COMPLETED')",
            name="valid_resource_progress_status",
        ),
    )

    student_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    resource_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("resources.resource_id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    first_opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    student: Mapped["User"] = relationship("User", back_populates="resource_progress_items")
    resource: Mapped["Resource"] = relationship("Resource")


class SavedResource(Base):
    __tablename__ = "saved_resources"

    student_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    resource_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("resources.resource_id", ondelete="CASCADE"),
        primary_key=True,
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    student: Mapped["User"] = relationship("User", back_populates="saved_resources")
    resource: Mapped["Resource"] = relationship("Resource")


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("student_id", "resource_id", name="uq_feedback_student_resource"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="valid_feedback_rating_range"),
    )

    feedback_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    resource_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("resources.resource_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    student: Mapped["User"] = relationship("User", back_populates="feedback_items")
    resource: Mapped["Resource"] = relationship("Resource")
