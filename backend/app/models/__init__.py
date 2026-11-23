"""Central registry importing all 13 SQLAlchemy 2.0 models for metadata & Alembic."""

from app.core.database import Base
from app.models.assessment import Answer, TestAttempt, TopicScore
from app.models.catalog import Question, Resource, Topic, TopicPrerequisite
from app.models.progress import Feedback, ResourceProgress, SavedResource, TopicProgress
from app.models.user import StudentProfile, User

__all__ = [
    "Answer",
    "Base",
    "Feedback",
    "Question",
    "Resource",
    "ResourceProgress",
    "SavedResource",
    "StudentProfile",
    "TestAttempt",
    "Topic",
    "TopicPrerequisite",
    "TopicProgress",
    "TopicScore",
    "User",
]
