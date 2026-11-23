"""Curriculum DAG, Resource Catalog, and Versioned Question ORM models (Tables 3–6 of 13)."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import SupportedLanguage


class Topic(Base):
    __tablename__ = "topics"

    topic_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    prerequisite_links: Mapped[list["TopicPrerequisite"]] = relationship(
        "TopicPrerequisite",
        foreign_keys="TopicPrerequisite.topic_id",
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    dependent_links: Mapped[list["TopicPrerequisite"]] = relationship(
        "TopicPrerequisite",
        foreign_keys="TopicPrerequisite.prerequisite_topic_id",
        back_populates="prerequisite_topic",
        cascade="all, delete-orphan",
    )
    resources: Mapped[list["Resource"]] = relationship("Resource", back_populates="topic")
    questions: Mapped[list["Question"]] = relationship("Question", back_populates="topic")


class TopicPrerequisite(Base):
    __tablename__ = "topic_prerequisites"
    __table_args__ = (
        CheckConstraint("topic_id <> prerequisite_topic_id", name="no_self_prerequisite"),
    )

    topic_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("topics.topic_id", ondelete="CASCADE"),
        primary_key=True,
    )
    prerequisite_topic_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("topics.topic_id", ondelete="CASCADE"),
        primary_key=True,
    )

    topic: Mapped["Topic"] = relationship(
        "Topic",
        foreign_keys=[topic_id],
        back_populates="prerequisite_links",
    )
    prerequisite_topic: Mapped["Topic"] = relationship(
        "Topic",
        foreign_keys=[prerequisite_topic_id],
        back_populates="dependent_links",
    )


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint(
            "content_type IN ('VIDEO', 'ARTICLE', 'EXERCISE')",
            name="valid_resource_content_type",
        ),
        CheckConstraint(
            "difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name="valid_resource_difficulty",
        ),
        CheckConstraint(
            "language IN ('en', 'tr')",
            name="valid_resource_language",
        ),
        CheckConstraint(
            "estimated_minutes IS NULL OR estimated_minutes > 0",
            name="positive_estimated_minutes",
        ),
    )

    resource_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    topic_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("topics.topic_id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    external_url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=SupportedLanguage.EN.value,
        server_default=SupportedLanguage.EN.value,
    )
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    topic: Mapped["Topic"] = relationship("Topic", back_populates="resources")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "correct_option IN ('A', 'B', 'C', 'D')",
            name="valid_question_correct_option",
        ),
        CheckConstraint(
            "difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name="valid_question_difficulty",
        ),
        CheckConstraint("version >= 1", name="positive_question_version"),
    )

    question_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    topic_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("topics.topic_id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    previous_question_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("questions.question_id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    topic: Mapped["Topic"] = relationship("Topic", back_populates="questions")
    previous_question: Mapped["Question | None"] = relationship(
        "Question",
        remote_side="Question.question_id",
        uselist=False,
    )
