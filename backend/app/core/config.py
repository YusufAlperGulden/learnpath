"""Application settings loaded from the repository root .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "LearnPath API"
    APP_VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    DATABASE_URL: str = (
        "postgresql+psycopg://learnpath:learnpath_dev_pass@localhost:5432/learnpath_db"
    )
    TEST_DATABASE_URL: str = (
        "postgresql+psycopg://learnpath:learnpath_dev_pass@localhost:5432/learnpath_test"
    )

    JWT_SECRET_KEY: str = "change-this-in-local-env-minimum-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    TEST_SESSION_EXPIRE_MINUTES: int = 120

    MASTERY_THRESHOLD_PERCENT: float = 70.0
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            raise ValueError(
                "DATABASE_URL must use 'postgresql+psycopg://' for SQLAlchemy 2.0 + Psycopg 3."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
