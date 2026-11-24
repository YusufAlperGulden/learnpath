"""Portable container & cloud startup entrypoint optimized for low-CPU cloud containers.

1. Prints immediate unbuffered liveness output so cloud log streams attach right away.
2. Fast-checks PostgreSQL connectivity (`connect_timeout=5`) and `alembic_version` head so
   already-migrated databases skip spawning a second Python interpreter (`saves ~200 MB RAM`
   and `~15s` CPU on `0.1 vCPU` free tiers).
3. Idempotently seeds curriculum + 48-learner cohort (O(1) count check when already seeded).
4. If a sleeping cloud database takes longer than the quick probe window to wake, hands off
   deferred bootstrap to FastAPI's background lifespan thread so Uvicorn binds `0.0.0.0:$PORT`
   immediately for platform health checks.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
CURRENT_ALEMBIC_HEAD = "0001_initial_13_tables"


def _log(msg: str) -> None:
    print(f"[startup] {msg}", flush=True)


def bootstrap_database(*, max_db_attempts: int = 20, delay_seconds: float = 2.0) -> bool:
    """Ensures PostgreSQL is reachable, migrated to head, and idempotently seeded."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

    from app.core.database import SessionLocal
    from scripts.seed_data import seed_database
    from scripts.seed_interactions import seed_interaction_cohort

    reachable = False
    for attempt in range(1, max_db_attempts + 1):
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            _log(f"Database connection verified on attempt {attempt}.")
            reachable = True
            break
        except (OperationalError, SQLAlchemyError) as exc:
            _log(f"Waiting for PostgreSQL ({attempt}/{max_db_attempts}): {exc.__class__.__name__}")
            time.sleep(delay_seconds)

    if not reachable:
        return False

    already_at_head = False
    try:
        with SessionLocal() as db:
            ver = db.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
            already_at_head = ver == CURRENT_ALEMBIC_HEAD
    except (ProgrammingError, OperationalError, SQLAlchemyError):
        already_at_head = False

    if already_at_head:
        _log(f"Schema already at Alembic head ({CURRENT_ALEMBIC_HEAD}); skipping subprocess.")
    else:
        _log("Applying Alembic migrations...")
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(BACKEND_ROOT),
            check=True,
        )

    t0 = time.perf_counter()
    with SessionLocal() as db:
        seed_database(db)
        if os.getenv("SEED_INTERACTION_COHORT", "true").strip().lower() in {"1", "true", "yes"}:
            seed_interaction_cohort(db)
    _log(f"Catalog & cohort seed verified in {(time.perf_counter() - t0) * 1000.0:.1f} ms.")
    return True


def main() -> None:
    port = os.getenv("PORT", "8000")
    _log(f"Booting LearnPath container (target port={port})...")

    # Try quick synchronous DB bootstrap (~6s window); if DB is still waking from sleep,
    # bind Uvicorn immediately so platform health checks pass while lifespan finishes bootstrap.
    ok = bootstrap_database(max_db_attempts=3, delay_seconds=1.5)
    if not ok:
        _log("PostgreSQL still waking up; deferring DB bootstrap to background lifespan worker.")
        os.environ["LEARNPATH_DEFER_BOOTSTRAP"] = "1"

    _log(f"Launching Uvicorn on 0.0.0.0:{port}...")
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
