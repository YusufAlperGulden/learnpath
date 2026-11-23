"""Atomic exam engine ORM models: TestAttempt, Answer, and TopicScore (Tables 7–9 of 13)."""

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
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.catalog import Question, Topic
    from app.models.user import User


class TestAttempt(Base):
    __test__ = False
    __tablename__ = "test_attempts"
    __table_args__ = (
        CheckConstraint(
            "test_type IN ('DIAGNOSTIC', 'TOPIC_QUIZ')",
            name="valid_test_type",
        ),
        CheckConstraint(
            "overall_score_percent >= 0.0 AND overall_score_percent <= 100.0",
            name="valid_overall_score_percent",
        ),
    )

    attempt_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    test_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_topic_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("topics.topic_id", ondelete="RESTRICT"),
        nullable=True,
    )
    overall_score_percent: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    student: Mapped["User"] = relationship("User", back_populates="test_attempts")
    target_topic: Mapped["Topic | None"] = relationship("Topic")
    answers: Mapped[list["Answer"]] = relationship(
        "Answer",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )
    topic_scores: Mapped[list["TopicScore"]] = relationship(
        "TopicScore",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        CheckConstraint(
            "selected_option IS NULL OR selected_option IN ('A', 'B', 'C', 'D')",
            name="valid_selected_option_or_null",
        ),
    )

    attempt_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("test_attempts.attempt_id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("questions.question_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    selected_option: Mapped[str | None] = mapped_column(String(1), nullable=True)
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    attempt: Mapped["TestAttempt"] = relationship("TestAttempt", back_populates="answers")
    question: Mapped["Question"] = relationship("Question")


class TopicScore(Base):
    __tablename__ = "topic_scores"
    __table_args__ = (
        CheckConstraint("correct_count >= 0", name="non_negative_correct_count"),
        CheckConstraint(
            "question_count > 0 AND correct_count <= question_count",
            name="valid_question_count_bounds",
        ),
        CheckConstraint(
            "score_percent >= 0.0 AND score_percent <= 100.0",
            name="valid_topic_score_percent",
        ),
    )

    attempt_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("test_attempts.attempt_id", ondelete="CASCADE"),
        primary_key=True,
    )
    topic_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("topics.topic_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    score_percent: Mapped[float] = mapped_column(Float, nullable=False)

    attempt: Mapped["TestAttempt"] = relationship("TestAttempt", back_populates="topic_scores")
    topic: Mapped["Topic"] = relationship("Topic")
