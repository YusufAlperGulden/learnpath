"""Idempotent seed runner for LearnPath curriculum DAG, 54 resources, 36 questions, and demo users."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.enums import (
    ContentType,
    ExperienceLevel,
    SupportedLanguage,
    UserRole,
)
from app.core.logging_config import configure_logging, get_logger
from app.core.security import hash_password
from app.models.catalog import Question, Resource, Topic, TopicPrerequisite
from app.models.user import StudentProfile, User
from scripts.curriculum_seed_catalog import QUESTIONS_DATA, RESOURCES_DATA, TOPICS_DATA

logger = get_logger("seed")


@dataclass(frozen=True, slots=True)
class SeedSummary:
    topics_total: int
    resources_total: int
    questions_total: int
    admin_email: str
    demo_student_email: str


def seed_database(db: Session) -> SeedSummary:
    """Populates default accounts, 6 DAG topics, 54 resources, and 36 questions idempotently."""
    admin = db.scalar(select(User).where(User.email == "admin@learnpath.local"))
    if admin is None:
        admin = User(
            email="admin@learnpath.local",
            password_hash=hash_password("AdminPass123!"),
            role=UserRole.ADMIN.value,
        )
        db.add(admin)
        db.flush()
        logger.info("Created default admin account: admin@learnpath.local")

    demo_student = db.scalar(select(User).where(User.email == "student@learnpath.local"))
    if demo_student is None:
        demo_student = User(
            email="student@learnpath.local",
            password_hash=hash_password("StudentPass123!"),
            role=UserRole.STUDENT.value,
        )
        db.add(demo_student)
        db.flush()
        db.add(
            StudentProfile(
                student_id=demo_student.user_id,
                display_name="Demo Python Learner",
                learning_goal="PYTHON_FUNDAMENTALS",
                experience_level=ExperienceLevel.BEGINNER.value,
                preferred_formats=[ContentType.VIDEO.value, ContentType.EXERCISE.value],
                preferred_language=SupportedLanguage.EN.value,
            )
        )
        db.flush()
        logger.info("Created default student account: student@learnpath.local")

    topics_by_slug: dict[str, Topic] = {}
    for item in TOPICS_DATA:
        topic = db.scalar(select(Topic).where(Topic.slug == item["slug"]))
        if topic is None:
            topic = Topic(
                name=item["name"],
                slug=item["slug"],
                description=item["description"],
                display_order=item["display_order"],
            )
            db.add(topic)
            db.flush()
        else:
            topic.name = item["name"]
            topic.description = item["description"]
            topic.display_order = item["display_order"]
        topics_by_slug[item["slug"]] = topic

    for item in TOPICS_DATA:
        topic = topics_by_slug[item["slug"]]
        for prereq_slug in item["prereqs"]:
            prereq_topic = topics_by_slug[prereq_slug]
            exists = db.get(
                TopicPrerequisite,
                (topic.topic_id, prereq_topic.topic_id),
            )
            if exists is None:
                db.add(
                    TopicPrerequisite(
                        topic_id=topic.topic_id,
                        prerequisite_topic_id=prereq_topic.topic_id,
                    )
                )

    for res in RESOURCES_DATA:
        existing_res = db.scalar(
            select(Resource).where(Resource.external_url == res["external_url"])
        )
        if existing_res is None:
            db.add(
                Resource(
                    topic_id=topics_by_slug[res["topic_slug"]].topic_id,
                    created_by=admin.user_id,
                    title=res["title"],
                    description=res["description"],
                    external_url=res["external_url"],
                    content_type=res["content_type"].value,
                    difficulty=res["difficulty"].value,
                    language=res["language"].value,
                    estimated_minutes=res["estimated_minutes"],
                    is_active=True,
                )
            )

    existing_questions = {
        (q.topic_id, q.question_text)
        for q in db.scalars(select(Question)).all()
    }
    for q in QUESTIONS_DATA:
        target_topic_id = topics_by_slug[q["topic_slug"]].topic_id
        if (target_topic_id, q["question_text"]) not in existing_questions:
            db.add(
                Question(
                    topic_id=target_topic_id,
                    created_by=admin.user_id,
                    question_text=q["question_text"],
                    code_snippet=q["code_snippet"],
                    option_a=q["option_a"],
                    option_b=q["option_b"],
                    option_c=q["option_c"],
                    option_d=q["option_d"],
                    correct_option=q["correct_option"].value,
                    explanation=q["explanation"],
                    difficulty=q["difficulty"].value,
                    version=1,
                    is_active=True,
                )
            )
            existing_questions.add((target_topic_id, q["question_text"]))

    db.commit()

    total_topics = len(db.scalars(select(Topic.topic_id)).all())
    total_resources = len(db.scalars(select(Resource.resource_id)).all())
    total_questions = len(db.scalars(select(Question.question_id)).all())

    logger.info(
        "Seed complete: topics=%d resources=%d questions=%d",
        total_topics,
        total_resources,
        total_questions,
    )
    return SeedSummary(
        topics_total=total_topics,
        resources_total=total_resources,
        questions_total=total_questions,
        admin_email=admin.email,
        demo_student_email=demo_student.email,
    )


def run_seed() -> SeedSummary:
    configure_logging()
    with SessionLocal() as db:
        return seed_database(db)


if __name__ == "__main__":
    run_seed()
