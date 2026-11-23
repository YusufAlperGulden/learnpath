"""Canonical enum constants shared across SQLAlchemy models, Pydantic schemas, and services.

Per RAD v2.0 Section 4.4, all domain enums use fixed uppercase string values
(except ISO 639-1 language codes 'en' and 'tr').
"""

from enum import StrEnum


class UserRole(StrEnum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


class ExperienceLevel(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class DifficultyLevel(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class ContentType(StrEnum):
    VIDEO = "VIDEO"
    ARTICLE = "ARTICLE"
    EXERCISE = "EXERCISE"


class TestType(StrEnum):
    __test__ = False

    DIAGNOSTIC = "DIAGNOSTIC"
    TOPIC_QUIZ = "TOPIC_QUIZ"


class MasteryStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    NEEDS_PRACTICE = "NEEDS_PRACTICE"
    MASTERED = "MASTERED"


class ResourceProgressStatus(StrEnum):
    OPENED = "OPENED"
    COMPLETED = "COMPLETED"


class AnswerOption(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class SupportedLanguage(StrEnum):
    EN = "en"
    TR = "tr"


class LearningGoalPreset(StrEnum):
    PYTHON_FUNDAMENTALS = "PYTHON_FUNDAMENTALS"
    DATA_SCIENCE = "DATA_SCIENCE"
    WEB_DEVELOPMENT = "WEB_DEVELOPMENT"
    AUTOMATION = "AUTOMATION"
