"""Portable container & cloud startup entrypoint (immune to Windows CRLF line-ending issues).

1. Waits for PostgreSQL connectivity.
2. Applies Alembic 13-table schema migrations (`alembic upgrade head`).
3. Idempotently seeds the Python curriculum (`seed_data`) and 48-learner cohort (`seed_interactions`).
4. Starts Uvicorn bound to `0.0.0.0:$PORT` (compatible with Docker Compose, Codespaces, and Render).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.database import SessionLocal
from app.core.logging_config import configure_logging, get_logger
from scripts.seed_data import seed_database
from scripts.seed_interactions import seed_interaction_cohort

logger = get_logger("startup")
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def wait_for_database(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            logger.info("Database connection verified on attempt %d.", attempt)
            return
        except (OperationalError, SQLAlchemyError) as exc:
            logger.info(
                "Waiting for PostgreSQL (%d/%d): %s",
                attempt,
                max_attempts,
                exc.__class__.__name__,
            )
            time.sleep(delay_seconds)
    raise RuntimeError("Database did not become reachable within timeout.")


def run_migrations_and_seed() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_ROOT),
        check=True,
    )
    with SessionLocal() as db:
        seed_database(db)
        if os.getenv("SEED_INTERACTION_COHORT", "true").strip().lower() in {"1", "true", "yes"}:
            seed_interaction_cohort(db)


def main() -> None:
    configure_logging()
    wait_for_database()
    run_migrations_and_seed()

    port = os.getenv("PORT", "8000")
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
        ],
    )


if __name__ == "__main__":
    main()
