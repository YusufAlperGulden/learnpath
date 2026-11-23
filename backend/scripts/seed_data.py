"""Idempotent seed script for initial Python curriculum DAG, resources, and questions."""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.enums import (
    AnswerOption,
    ContentType,
    DifficultyLevel,
    SupportedLanguage,
    UserRole,
)
from app.core.logging_config import configure_logging, get_logger
from app.core.security import hash_password
from app.models.catalog import Question, Resource, Topic, TopicPrerequisite
from app.models.user import User

logger = get_logger("seed")

TOPICS_DATA = [
    {
        "slug": "variables",
        "name": "Variables & Data Types",
        "description": "Variable assignment, dynamic typing, strings, integers, floats, and booleans in Python.",
        "display_order": 1,
        "prereqs": [],
    },
    {
        "slug": "operators",
        "name": "Operators & Expressions",
        "description": "Arithmetic, comparison, logical, and assignment operators with precedence rules.",
        "display_order": 2,
        "prereqs": ["variables"],
    },
    {
        "slug": "conditionals",
        "name": "Conditionals & Branching",
        "description": "Decision making with if, elif, else, truthiness, and nested conditional expressions.",
        "display_order": 3,
        "prereqs": ["operators"],
    },
    {
        "slug": "loops",
        "name": "Loops & Control Flow",
        "description": "Iteration with for/while loops, range(), break, continue, and loop invariants.",
        "display_order": 4,
        "prereqs": ["conditionals"],
    },
    {
        "slug": "functions",
        "name": "Functions & Scope",
        "description": "Defining reusable functions, parameters, default arguments, return values, and variable scope.",
        "display_order": 5,
        "prereqs": ["loops"],
    },
    {
        "slug": "data-structures",
        "name": "Core Data Structures",
        "description": "Lists, tuples, dictionaries, sets, slicing, comprehensions, and mutability trade-offs.",
        "display_order": 6,
        "prereqs": ["loops", "functions"],
    },
]

RESOURCES_DATA = [
    {
        "topic_slug": "variables",
        "title": "Python Variables and Core Data Types Explained",
        "description": "Visual walkthrough of dynamic typing, int, float, str, bool, and type conversion with practical examples.",
        "external_url": "https://docs.python.org/3/tutorial/introduction.html",
        "content_type": ContentType.ARTICLE,
        "difficulty": DifficultyLevel.BEGINNER,
        "language": SupportedLanguage.EN,
        "estimated_minutes": 20,
    },
    {
        "topic_slug": "loops",
        "title": "Master Python While & For Loops",
        "description": "Step-by-step video guide covering loop counters, range(), sentinel conditions, and preventing infinite loops.",
        "external_url": "https://docs.python.org/3/tutorial/controlflow.html#for-statements",
        "content_type": ContentType.VIDEO,
        "difficulty": DifficultyLevel.BEGINNER,
        "language": SupportedLanguage.EN,
        "estimated_minutes": 18,
    },
    {
        "topic_slug": "data-structures",
        "title": "Hands-On Python Lists, Dictionaries & Sets Practice",
        "description": "Interactive coding exercises on list comprehensions, dictionary lookups, and choosing mutable vs immutable structures.",
        "external_url": "https://docs.python.org/3/tutorial/datastructures.html",
        "content_type": ContentType.EXERCISE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": SupportedLanguage.EN,
        "estimated_minutes": 30,
    },
]

QUESTIONS_DATA = [
    {
        "topic_slug": "variables",
        "question_text": "What is the type of the variable `result` after executing the snippet below?",
        "code_snippet": "x = 7\ny = 2\nresult = x / y",
        "option_a": "int",
        "option_b": "float",
        "option_c": "str",
        "option_d": "Decimal",
        "correct_option": AnswerOption.B,
        "explanation": "In Python 3, the `/` true division operator always returns a `float` (`3.5`), even when both operands divide evenly.",
        "difficulty": DifficultyLevel.BEGINNER,
    },
    {
        "topic_slug": "loops",
        "question_text": "What will be printed when the following Python loop executes?",
        "code_snippet": "count = 0\nwhile count < 3:\n    print(count, end=' ')\n    count += 1",
        "option_a": "0 1 2 3",
        "option_b": "0 1 2",
        "option_c": "1 2 3",
        "option_d": "The loop runs forever",
        "correct_option": AnswerOption.B,
        "explanation": "The loop starts at 0 and increments by 1 after printing. Once `count` reaches 3, `count < 3` is False and the loop terminates.",
        "difficulty": DifficultyLevel.BEGINNER,
    },
]


def run_seed() -> None:
    configure_logging()
    with SessionLocal() as db:
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

        existing_q_count = len(db.scalars(select(Question.question_id)).all())
        if existing_q_count == 0:
            for q in QUESTIONS_DATA:
                db.add(
                    Question(
                        topic_id=topics_by_slug[q["topic_slug"]].topic_id,
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

        db.commit()
        logger.info("Seed completed: %d topics ensured.", len(topics_by_slug))


if __name__ == "__main__":
    run_seed()
