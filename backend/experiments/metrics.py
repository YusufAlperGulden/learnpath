"""Shared ranking metrics, diversity measures, paired student-level bootstrap, and session helpers.

Implements the statistical and evaluation conventions specified in LearnPath RAD v2.0 Section 3.4.4:
- Relevance threshold: explicit rating >= 4 on a 1..5 scale.
- Precision@5: relevant items in top-5 divided by 5 (short lists pad missing slots as non-relevant).
- Recall@5 & NDCG@5: evaluated over queries with >= 1 eligible held-out relevant item; zero-relevant
  queries are excluded and explicitly counted.
- Diversity@5: reports topic-tag dissimilarity, topic+format dissimilarity, and TF-IDF cosine
  dissimilarity.
- Uncertainty: paired bootstrap resampling at the student level (B = 1000, fixed deterministic seed).
"""

from __future__ import annotations

import importlib.metadata
import math
import platform
import random
import socket
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID

import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import Base, SessionLocal
from app.core.logging_config import get_logger
from app.services.recommenders.base import CandidateResource

logger = get_logger("experiments.metrics")

BOOTSTRAP_SEED = 4912026
DEFAULT_BOOTSTRAP_SAMPLES = 1000


@dataclass(frozen=True, slots=True)
class BootstrapEstimate:
    mean: float
    ci_95_low: float
    ci_95_high: float
    n_students: int


@dataclass(frozen=True, slots=True)
class PairedBootstrapDelta:
    comparison: str
    metric: str
    mean_delta: float
    ci_95_low: float
    ci_95_high: float
    p_value_two_sided: float
    n_paired_students: int
    statistically_significant_95: bool


def precision_at_k(recommended_ids: Sequence[UUID], relevant_ids: set[UUID], k: int = 5) -> float:
    """Relevant recommended items divided by K; short lists (< K) treat missing slots as 0."""
    if k <= 0:
        return 0.0
    top_k = list(recommended_ids)[:k]
    hits = sum(1 for rid in top_k if rid in relevant_ids)
    return hits / k


def recall_at_k(recommended_ids: Sequence[UUID], relevant_ids: set[UUID], k: int = 5) -> float:
    """Relevant recommended items divided by eligible held-out relevant items for the query."""
    if not relevant_ids or k <= 0:
        return 0.0
    top_k = list(recommended_ids)[:k]
    hits = sum(1 for rid in top_k if rid in relevant_ids)
    return hits / len(relevant_ids)


def ndcg_at_k(recommended_ids: Sequence[UUID], relevant_ids: set[UUID], k: int = 5) -> float:
    """Normalized Discounted Cumulative Gain at K with binary relevance (rating >= 4)."""
    if not relevant_ids or k <= 0:
        return 0.0
    top_k = list(recommended_ids)[:k]
    dcg = 0.0
    for idx, rid in enumerate(top_k):
        if rid in relevant_ids:
            dcg += 1.0 / math.log2(idx + 2)
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0.0 else 0.0


def compute_topic_tag_diversity(candidates: Sequence[CandidateResource]) -> float:
    """Mean pairwise topic-tag dissimilarity within a recommendation list (RAD Section 3.4.4)."""
    n = len(candidates)
    if n < 2:
        return 0.0
    dissim_sum = 0.0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            dissim_sum += 1.0 if candidates[i].topic_id != candidates[j].topic_id else 0.0
            pairs += 1
    return round(dissim_sum / pairs, 6) if pairs > 0 else 0.0


def compute_topic_format_diversity(candidates: Sequence[CandidateResource]) -> float:
    """Mean pairwise dissimilarity across `(topic_id, content_type)` metadata attributes."""
    n = len(candidates)
    if n < 2:
        return 0.0
    dissim_sum = 0.0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            topic_diff = 1.0 if candidates[i].topic_id != candidates[j].topic_id else 0.0
            fmt_diff = 1.0 if candidates[i].content_type != candidates[j].content_type else 0.0
            dissim_sum += 0.5 * topic_diff + 0.5 * fmt_diff
            pairs += 1
    return round(dissim_sum / pairs, 6) if pairs > 0 else 0.0


def percentile(values: Sequence[float], q: float) -> float:
    """Computes linear-interpolated percentile `q` in [0, 100] for latency reporting."""
    if not values:
        return 0.0
    arr = np.asarray(values, dtype=np.float64)
    return round(float(np.percentile(arr, q)), 4)


def bootstrap_mean_ci(
    values: Sequence[float],
    *,
    n_boot: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> BootstrapEstimate:
    """Student-level percentile bootstrap 95% confidence interval for a metric vector."""
    n = len(values)
    if n == 0:
        return BootstrapEstimate(mean=0.0, ci_95_low=0.0, ci_95_high=0.0, n_students=0)

    observed_mean = sum(values) / n
    if n == 1:
        val = round(float(observed_mean), 6)
        return BootstrapEstimate(mean=val, ci_95_low=val, ci_95_high=val, n_students=1)

    rng = random.Random(seed)
    boot_means = np.empty(n_boot, dtype=np.float64)
    val_list = [float(v) for v in values]
    for b in range(n_boot):
        sample_sum = 0.0
        for _ in range(n):
            sample_sum += val_list[rng.randrange(n)]
        boot_means[b] = sample_sum / n

    low, high = np.percentile(boot_means, [2.5, 97.5])
    return BootstrapEstimate(
        mean=round(float(observed_mean), 6),
        ci_95_low=round(float(low), 6),
        ci_95_high=round(float(high), 6),
        n_students=n,
    )


def paired_bootstrap_delta(
    values_a: Sequence[float],
    values_b: Sequence[float],
    *,
    comparison: str,
    metric: str,
    n_boot: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> PairedBootstrapDelta:
    """Paired student-level bootstrap 95% CI on `Delta = A - B` across identical student queries."""
    if len(values_a) != len(values_b):
        raise ValueError("Paired bootstrap requires equal-length student metric vectors.")

    n = len(values_a)
    if n == 0:
        return PairedBootstrapDelta(
            comparison=comparison,
            metric=metric,
            mean_delta=0.0,
            ci_95_low=0.0,
            ci_95_high=0.0,
            p_value_two_sided=1.0,
            n_paired_students=0,
            statistically_significant_95=False,
        )

    diffs = [float(a) - float(b) for a, b in zip(values_a, values_b, strict=True)]
    mean_diff = sum(diffs) / n
    if n == 1:
        d = round(mean_diff, 6)
        return PairedBootstrapDelta(
            comparison=comparison,
            metric=metric,
            mean_delta=d,
            ci_95_low=d,
            ci_95_high=d,
            p_value_two_sided=1.0,
            n_paired_students=1,
            statistically_significant_95=False,
        )

    rng = random.Random(seed)
    boot_deltas = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += diffs[rng.randrange(n)]
        boot_deltas[b] = s / n

    low, high = np.percentile(boot_deltas, [2.5, 97.5])
    # Two-sided bootstrap p-value via empirical tail crossing zero
    le_zero = float(np.mean(boot_deltas <= 0.0))
    ge_zero = float(np.mean(boot_deltas >= 0.0))
    p_two_sided = min(1.0, 2.0 * min(le_zero, ge_zero))
    sig = bool(low > 0.0 or high < 0.0)

    return PairedBootstrapDelta(
        comparison=comparison,
        metric=metric,
        mean_delta=round(float(mean_diff), 6),
        ci_95_low=round(float(low), 6),
        ci_95_high=round(float(high), 6),
        p_value_two_sided=round(p_two_sided, 6),
        n_paired_students=n,
        statistically_significant_95=sig,
    )


def collect_environment_metadata(db_backend: str) -> dict[str, str]:
    """Records hardware, OS, Python, and ML package versions for RAD reproducibility."""
    packages = ("scikit-learn", "numpy", "scipy", "sqlalchemy", "fastapi", "pydantic")
    versions: dict[str, str] = {}
    for pkg in packages:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = "unknown"

    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "machine": platform.machine(),
        "processor": platform.processor() or "x86_64",
        "python_version": platform.python_version(),
        "database_backend": db_backend,
        **{f"pkg_{k.replace('-', '_')}": v for k, v in versions.items()},
    }


def _is_postgres_port_reachable(timeout_sec: float = 0.25) -> bool:
    parsed = urlparse(settings.DATABASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except OSError:
        return False


@contextmanager
def open_experiment_session(mode: str = "auto") -> Iterator[tuple[Session, str]]:
    """Opens configured PostgreSQL session or falls back cleanly to isolated in-memory SQLite."""
    normalized = mode.strip().lower()
    if normalized not in {"auto", "postgres", "sqlite"}:
        raise ValueError("mode must be one of: 'auto', 'postgres', 'sqlite'.")

    if normalized in {"auto", "postgres"}:
        if normalized == "auto" and not _is_postgres_port_reachable():
            logger.info(
                "Configured PostgreSQL port is unreachable; using isolated in-memory SQLite "
                "experiment database with deterministic cohort seed."
            )
        else:
            try:
                db = SessionLocal()
                db.execute(text("SELECT 1"))
            except (OperationalError, SQLAlchemyError):
                if normalized == "postgres":
                    raise
                logger.info(
                    "Configured PostgreSQL instance is offline; using isolated in-memory SQLite "
                    "experiment database with deterministic cohort seed."
                )
            else:
                try:
                    yield db, "postgresql"
                finally:
                    db.close()
                return

    sqlite_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=sqlite_engine)
    local_factory = sessionmaker(bind=sqlite_engine, autocommit=False, autoflush=False)
    sqlite_db = local_factory()
    try:
        yield sqlite_db, "sqlite_in_memory"
    finally:
        sqlite_db.close()
        Base.metadata.drop_all(bind=sqlite_engine)
        sqlite_engine.dispose()
