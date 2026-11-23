"""Initial 13-table LearnPath schema synchronized with Revised RAD v2.0.

Revision ID: 0001_initial_13_tables
Revises: None
Create Date: 2026-11-23 17:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_13_tables"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="STUDENT", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('STUDENT', 'ADMIN')",
            name=op.f("ck_users_valid_user_role"),
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. topics
    op.create_table(
        "topics",
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("topic_id", name=op.f("pk_topics")),
    )
    op.create_index(op.f("ix_topics_slug"), "topics", ["slug"], unique=True)

    # 3. student_profiles
    op.create_table(
        "student_profiles",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("learning_goal", sa.String(length=255), nullable=False),
        sa.Column("experience_level", sa.String(length=20), nullable=False),
        sa.Column(
            "preferred_formats",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "preferred_language",
            sa.String(length=10),
            server_default="en",
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "experience_level IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name=op.f("ck_student_profiles_valid_experience_level"),
        ),
        sa.CheckConstraint(
            "preferred_language IN ('en', 'tr')",
            name=op.f("ck_student_profiles_valid_preferred_language"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.user_id"],
            name=op.f("fk_student_profiles_student_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("student_id", name=op.f("pk_student_profiles")),
    )

    # 4. topic_prerequisites
    op.create_table(
        "topic_prerequisites",
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("prerequisite_topic_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "topic_id <> prerequisite_topic_id",
            name=op.f("ck_topic_prerequisites_no_self_prerequisite"),
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_topic_id"],
            ["topics.topic_id"],
            name=op.f("fk_topic_prerequisites_prerequisite_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.topic_id"],
            name=op.f("fk_topic_prerequisites_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "topic_id",
            "prerequisite_topic_id",
            name=op.f("pk_topic_prerequisites"),
        ),
    )

    # 5. resources
    op.create_table(
        "resources",
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("external_url", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=10), server_default="en", nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_type IN ('VIDEO', 'ARTICLE', 'EXERCISE')",
            name=op.f("ck_resources_valid_resource_content_type"),
        ),
        sa.CheckConstraint(
            "difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name=op.f("ck_resources_valid_resource_difficulty"),
        ),
        sa.CheckConstraint(
            "language IN ('en', 'tr')",
            name=op.f("ck_resources_valid_resource_language"),
        ),
        sa.CheckConstraint(
            "estimated_minutes IS NULL OR estimated_minutes > 0",
            name=op.f("ck_resources_positive_estimated_minutes"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
            name=op.f("fk_resources_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.topic_id"],
            name=op.f("fk_resources_topic_id_topics"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("resource_id", name=op.f("pk_resources")),
        sa.UniqueConstraint("external_url", name=op.f("uq_resources_external_url")),
    )
    op.create_index(op.f("ix_resources_topic_id"), "resources", ["topic_id"], unique=False)

    # 6. questions
    op.create_table(
        "questions",
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("option_a", sa.Text(), nullable=False),
        sa.Column("option_b", sa.Text(), nullable=False),
        sa.Column("option_c", sa.Text(), nullable=False),
        sa.Column("option_d", sa.Text(), nullable=False),
        sa.Column("correct_option", sa.String(length=1), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("previous_question_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "correct_option IN ('A', 'B', 'C', 'D')",
            name=op.f("ck_questions_valid_question_correct_option"),
        ),
        sa.CheckConstraint(
            "difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name=op.f("ck_questions_valid_question_difficulty"),
        ),
        sa.CheckConstraint(
            "version >= 1",
            name=op.f("ck_questions_positive_question_version"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
            name=op.f("fk_questions_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["previous_question_id"],
            ["questions.question_id"],
            name=op.f("fk_questions_previous_question_id_questions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.topic_id"],
            name=op.f("fk_questions_topic_id_topics"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("question_id", name=op.f("pk_questions")),
    )
    op.create_index(op.f("ix_questions_topic_id"), "questions", ["topic_id"], unique=False)

    # 7. test_attempts
    op.create_table(
        "test_attempts",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("test_type", sa.String(length=20), nullable=False),
        sa.Column("target_topic_id", sa.Uuid(), nullable=True),
        sa.Column("overall_score_percent", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "test_type IN ('DIAGNOSTIC', 'TOPIC_QUIZ')",
            name=op.f("ck_test_attempts_valid_test_type"),
        ),
        sa.CheckConstraint(
            "overall_score_percent >= 0.0 AND overall_score_percent <= 100.0",
            name=op.f("ck_test_attempts_valid_overall_score_percent"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.user_id"],
            name=op.f("fk_test_attempts_student_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_topic_id"],
            ["topics.topic_id"],
            name=op.f("fk_test_attempts_target_topic_id_topics"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("attempt_id", name=op.f("pk_test_attempts")),
    )
    op.create_index(
        op.f("ix_test_attempts_student_id"),
        "test_attempts",
        ["student_id"],
        unique=False,
    )

    # 8. answers
    op.create_table(
        "answers",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("selected_option", sa.String(length=1), nullable=True),
        sa.Column("is_correct", sa.Boolean(), server_default="false", nullable=False),
        sa.CheckConstraint(
            "selected_option IS NULL OR selected_option IN ('A', 'B', 'C', 'D')",
            name=op.f("ck_answers_valid_selected_option_or_null"),
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["test_attempts.attempt_id"],
            name=op.f("fk_answers_attempt_id_test_attempts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.question_id"],
            name=op.f("fk_answers_question_id_questions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("attempt_id", "question_id", name=op.f("pk_answers")),
    )

    # 9. topic_scores
    op.create_table(
        "topic_scores",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("score_percent", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "correct_count >= 0",
            name=op.f("ck_topic_scores_non_negative_correct_count"),
        ),
        sa.CheckConstraint(
            "question_count > 0 AND correct_count <= question_count",
            name=op.f("ck_topic_scores_valid_question_count_bounds"),
        ),
        sa.CheckConstraint(
            "score_percent >= 0.0 AND score_percent <= 100.0",
            name=op.f("ck_topic_scores_valid_topic_score_percent"),
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["test_attempts.attempt_id"],
            name=op.f("fk_topic_scores_attempt_id_test_attempts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.topic_id"],
            name=op.f("fk_topic_scores_topic_id_topics"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("attempt_id", "topic_id", name=op.f("pk_topic_scores")),
    )

    # 10. topic_progress (13th Revised RAD table)
    op.create_table(
        "topic_progress",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column(
            "is_manually_completed",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("manually_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_score_percent", sa.Float(), nullable=True),
        sa.Column(
            "mastery_status",
            sa.String(length=20),
            server_default="UNKNOWN",
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "mastery_status IN ('UNKNOWN', 'NEEDS_PRACTICE', 'MASTERED')",
            name=op.f("ck_topic_progress_valid_mastery_status"),
        ),
        sa.CheckConstraint(
            "latest_score_percent IS NULL OR (latest_score_percent >= 0.0 AND latest_score_percent <= 100.0)",
            name=op.f("ck_topic_progress_valid_latest_score_percent"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.user_id"],
            name=op.f("fk_topic_progress_student_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.topic_id"],
            name=op.f("fk_topic_progress_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("student_id", "topic_id", name=op.f("pk_topic_progress")),
    )

    # 11. resource_progress
    op.create_table(
        "resource_progress",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "first_opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('OPENED', 'COMPLETED')",
            name=op.f("ck_resource_progress_valid_resource_progress_status"),
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["resources.resource_id"],
            name=op.f("fk_resource_progress_resource_id_resources"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.user_id"],
            name=op.f("fk_resource_progress_student_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("student_id", "resource_id", name=op.f("pk_resource_progress")),
    )

    # 12. saved_resources
    op.create_table(
        "saved_resources",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["resources.resource_id"],
            name=op.f("fk_saved_resources_resource_id_resources"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.user_id"],
            name=op.f("fk_saved_resources_student_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("student_id", "resource_id", name=op.f("pk_saved_resources")),
    )

    # 13. feedback
    op.create_table(
        "feedback",
        sa.Column("feedback_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name=op.f("ck_feedback_valid_feedback_rating_range"),
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["resources.resource_id"],
            name=op.f("fk_feedback_resource_id_resources"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.user_id"],
            name=op.f("fk_feedback_student_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("feedback_id", name=op.f("pk_feedback")),
        sa.UniqueConstraint("student_id", "resource_id", name="uq_feedback_student_resource"),
    )
    op.create_index(op.f("ix_feedback_resource_id"), "feedback", ["resource_id"], unique=False)
    op.create_index(op.f("ix_feedback_student_id"), "feedback", ["student_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_feedback_student_id"), table_name="feedback")
    op.drop_index(op.f("ix_feedback_resource_id"), table_name="feedback")
    op.drop_table("feedback")
    op.drop_table("saved_resources")
    op.drop_table("resource_progress")
    op.drop_table("topic_progress")
    op.drop_table("topic_scores")
    op.drop_table("answers")
    op.drop_index(op.f("ix_test_attempts_student_id"), table_name="test_attempts")
    op.drop_table("test_attempts")
    op.drop_index(op.f("ix_questions_topic_id"), table_name="questions")
    op.drop_table("questions")
    op.drop_index(op.f("ix_resources_topic_id"), table_name="resources")
    op.drop_table("resources")
    op.drop_table("topic_prerequisites")
    op.drop_table("student_profiles")
    op.drop_index(op.f("ix_topics_slug"), table_name="topics")
    op.drop_table("topics")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
