"""Deterministic, documented cohort interaction generator for offline recommender experiments.

Creates 48 Python learner accounts across 4 documented archetypes (including explicit cold-start
learners) with realistic TopicProgress states and ~750 chronological 1–5 resource ratings.
"""

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.enums import (
    ContentType,
    DifficultyLevel,
    ExperienceLevel,
    MasteryStatus,
    SupportedLanguage,
    UserRole,
)
from app.core.logging_config import configure_logging, get_logger
from app.core.security import hash_password
from app.models.catalog import Resource, Topic
from app.models.progress import Feedback, TopicProgress
from app.models.user import StudentProfile, User
from scripts.seed_data import seed_database

logger = get_logger("seed_interactions")

COHORT_RANDOM_SEED = 4912026
COHORT_STUDENT_COUNT = 48


@dataclass(frozen=True, slots=True)
class ArchetypeSpec:
    code: str
    goal: str
    experience: ExperienceLevel
    formats: tuple[ContentType, ...]
    language: SupportedLanguage
    mastered_slugs: tuple[str, ...]
    weak_slug: str
    weak_score: float
    preferred_keywords: tuple[str, ...]


ARCHETYPES: tuple[ArchetypeSpec, ...] = (
    ArchetypeSpec(
        code="fundamentals_visual",
        goal="PYTHON_FUNDAMENTALS",
        experience=ExperienceLevel.BEGINNER,
        formats=(ContentType.VIDEO, ContentType.EXERCISE),
        language=SupportedLanguage.EN,
        mastered_slugs=("variables",),
        weak_slug="operators",
        weak_score=45.0,
        preferred_keywords=("beginner", "visual", "step", "drills", "interactive", "practice"),
    ),
    ArchetypeSpec(
        code="data_science_prep",
        goal="DATA_SCIENCE",
        experience=ExperienceLevel.INTERMEDIATE,
        formats=(ContentType.ARTICLE, ContentType.EXERCISE),
        language=SupportedLanguage.EN,
        mastered_slugs=("variables", "operators", "conditionals"),
        weak_slug="loops",
        weak_score=52.0,
        preferred_keywords=("data", "precision", "enumerate", "zip", "comprehensions", "pipeline"),
    ),
    ArchetypeSpec(
        code="web_backend_builder",
        goal="WEB_DEVELOPMENT",
        experience=ExperienceLevel.INTERMEDIATE,
        formats=(ContentType.VIDEO, ContentType.ARTICLE),
        language=SupportedLanguage.EN,
        mastered_slugs=("variables", "operators", "conditionals", "loops"),
        weak_slug="functions",
        weak_score=55.0,
        preferred_keywords=("api", "guard", "pattern", "kwargs", "scope", "typing", "clean"),
    ),
    ArchetypeSpec(
        code="automation_advanced",
        goal="AUTOMATION",
        experience=ExperienceLevel.ADVANCED,
        formats=(ContentType.EXERCISE, ContentType.ARTICLE),
        language=SupportedLanguage.EN,
        mastered_slugs=("variables", "operators", "conditionals", "loops", "functions"),
        weak_slug="data-structures",
        weak_score=58.0,
        preferred_keywords=("itertools", "complexity", "collections", "decorators", "bitwise", "lab"),
    ),
)


@dataclass(frozen=True, slots=True)
class CohortSeedSummary:
    cohort_students: int
    cold_start_students: int
    total_feedback_rows: int


def _score_latent_utility(
    res: Resource,
    spec: ArchetypeSpec,
    latent_peer_bonus: dict[tuple[str, UUID], float],
    rng: random.Random,
) -> int:
    """Computes a realistic 1..5 integer rating driven by content fit + peer latent affinity."""
    base = 2.2

    if ContentType(res.content_type) in spec.formats:
        base += 1.05
    else:
        base -= 0.55

    tier_pos = {
        DifficultyLevel.BEGINNER.value: 0,
        DifficultyLevel.INTERMEDIATE.value: 1,
        DifficultyLevel.ADVANCED.value: 2,
    }
    diff_gap = abs(tier_pos[res.difficulty] - tier_pos[spec.experience.value])
    if diff_gap == 0:
        base += 0.75
    elif diff_gap == 1:
        base += 0.15
    else:
        base -= 0.65

    text_blob = f"{res.title} {res.description}".lower()
    kw_hits = sum(1 for kw in spec.preferred_keywords if kw in text_blob)
    base += min(0.55, kw_hits * 0.22)

    # Collaborative peer-gem signal shared across learners of the same archetype
    base += latent_peer_bonus.get((spec.code, res.resource_id), 0.0)

    noisy = base + rng.gauss(0.0, 0.32)
    return max(1, min(5, round(noisy)))


def seed_interaction_cohort(db: Session, *, seed: int = COHORT_RANDOM_SEED) -> CohortSeedSummary:
    """Populates 48 cohort learners and chronological ratings idempotently."""
    seed_database(db)
    rng = random.Random(seed)

    topics = db.scalars(select(Topic).order_by(Topic.display_order.asc())).all()
    topics_by_slug = {t.slug: t for t in topics}
    en_resources = db.scalars(
        select(Resource)
        .where(Resource.is_active.is_(True), Resource.language == SupportedLanguage.EN.value)
        .order_by(Resource.external_url.asc())
    ).all()

    # Pre-assign deterministic archetype-level collaborative affinity bonuses on specific resources
    latent_peer_bonus: dict[tuple[str, UUID], float] = {}
    for spec in ARCHETYPES:
        for res in en_resources:
            draw = rng.random()
            if draw > 0.80:
                latent_peer_bonus[(spec.code, res.resource_id)] = 0.85
            elif draw < 0.18:
                latent_peer_bonus[(spec.code, res.resource_id)] = -0.70

    # Compute password hash once so seeding 48 test learners stays sub-second
    shared_cohort_hash = hash_password("CohortLearner123!")
    base_time = datetime(2026, 9, 15, 9, 0, 0, tzinfo=UTC)

    cold_start_count = 0
    for idx in range(COHORT_STUDENT_COUNT):
        email = f"cohort-{idx + 1:02d}@learnpath.local"
        spec = ARCHETYPES[idx % len(ARCHETYPES)]
        # Designate the last 2 learners of each archetype (8 total) as cold-start learners
        is_cold_start = idx >= (COHORT_STUDENT_COUNT - 8)
        if is_cold_start:
            cold_start_count += 1

        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=shared_cohort_hash,
                role=UserRole.STUDENT.value,
                created_at=base_time + timedelta(hours=idx * 3),
            )
            db.add(user)
            db.flush()

            db.add(
                StudentProfile(
                    student_id=user.user_id,
                    display_name=f"Cohort Learner {idx + 1:02d}",
                    learning_goal=spec.goal,
                    experience_level=spec.experience.value,
                    preferred_formats=[f.value for f in spec.formats],
                    preferred_language=spec.language.value,
                )
            )

            for mastered_slug in spec.mastered_slugs:
                t_obj = topics_by_slug[mastered_slug]
                db.add(
                    TopicProgress(
                        student_id=user.user_id,
                        topic_id=t_obj.topic_id,
                        is_manually_completed=True,
                        manually_completed_at=base_time + timedelta(days=1),
                        latest_score_percent=85.0,
                        mastery_status=MasteryStatus.MASTERED.value,
                    )
                )

            weak_topic = topics_by_slug[spec.weak_slug]
            db.add(
                TopicProgress(
                    student_id=user.user_id,
                    topic_id=weak_topic.topic_id,
                    is_manually_completed=False,
                    manually_completed_at=None,
                    latest_score_percent=spec.weak_score,
                    mastery_status=MasteryStatus.NEEDS_PRACTICE.value,
                )
            )
            db.flush()

        existing_fb_ids = set(
            db.scalars(
                select(Feedback.resource_id).where(Feedback.student_id == user.user_id)
            ).all()
        )
        if existing_fb_ids:
            continue

        relevant_topic_ids = {
            topics_by_slug[s].topic_id for s in (*spec.mastered_slugs, spec.weak_slug)
        }
        pool = [r for r in en_resources if r.topic_id in relevant_topic_ids]
        other_pool = [r for r in en_resources if r.topic_id not in relevant_topic_ids]

        if is_cold_start:
            # Cold-start learners have 0 historical train ratings and 3 late test-window ratings
            chosen_early: list[Resource] = []
            weak_tid = topics_by_slug[spec.weak_slug].topic_id
            weak_candidates = [r for r in en_resources if r.topic_id == weak_tid]
            chosen_late = rng.sample(weak_candidates, k=min(4, len(weak_candidates)))
        else:
            early_k = min(13, len(pool))
            chosen_early = rng.sample(pool, k=early_k)
            remaining = [r for r in (pool + other_pool[:4]) if r not in chosen_early]
            # Ensure late interactions focus on the learner's active priority topic(s)
            weak_tid = topics_by_slug[spec.weak_slug].topic_id
            weak_remaining = [r for r in remaining if r.topic_id == weak_tid]
            other_remaining = [r for r in remaining if r.topic_id != weak_tid]
            late_pool = weak_remaining + other_remaining
            chosen_late = late_pool[: min(5, len(late_pool))]

        # Early interactions fall in days 1..40 (Train / Validation window)
        for step_idx, res in enumerate(chosen_early):
            ts = base_time + timedelta(
                days=1 + (step_idx * 3) + rng.uniform(0.0, 1.8),
                minutes=idx * 7,
            )
            rating = _score_latent_utility(res, spec, latent_peer_bonus, rng)
            db.add(
                Feedback(
                    student_id=user.user_id,
                    resource_id=res.resource_id,
                    rating=rating,
                    comment=None,
                    created_at=ts,
                )
            )

        # Late interactions fall in days 45..58 (Validation / Test evaluation window)
        for late_idx, res in enumerate(chosen_late):
            ts = base_time + timedelta(
                days=45 + late_idx * 3 + (10 if is_cold_start else rng.uniform(0.0, 8.0)),
                minutes=idx * 11,
            )
            # Ensure each learner evaluates both high-utility and lower-utility items in test window
            rating = _score_latent_utility(res, spec, latent_peer_bonus, rng)
            db.add(
                Feedback(
                    student_id=user.user_id,
                    resource_id=res.resource_id,
                    rating=rating,
                    comment=None,
                    created_at=ts,
                )
            )

    db.commit()
    total_fb = len(db.scalars(select(Feedback.feedback_id)).all())
    logger.info(
        "Seeded interaction cohort: students=%d cold_start=%d total_feedback=%d",
        COHORT_STUDENT_COUNT,
        cold_start_count,
        total_fb,
    )
    return CohortSeedSummary(
        cohort_students=COHORT_STUDENT_COUNT,
        cold_start_students=cold_start_count,
        total_feedback_rows=total_fb,
    )


def run_seed_interactions() -> CohortSeedSummary:
    configure_logging()
    with SessionLocal() as db:
        return seed_interaction_cohort(db)


if __name__ == "__main__":
    run_seed_interactions()
