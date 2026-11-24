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
    weak_topic_id: UUID,
    latent_peer_bonus: dict[tuple[str, UUID], float],
    rng: random.Random,
) -> int:
    """Computes a realistic 1..5 integer rating driven by topic gap, content fit, and peer affinity."""
    base = 2.05

    # Active topic-gap relevance vs. already-mastered review material
    if res.topic_id == weak_topic_id:
        base += 0.65
    else:
        base -= 0.20

    if ContentType(res.content_type) in spec.formats:
        base += 0.95
    else:
        base -= 0.55

    tier_pos = {
        DifficultyLevel.BEGINNER.value: 0,
        DifficultyLevel.INTERMEDIATE.value: 1,
        DifficultyLevel.ADVANCED.value: 2,
    }
    target_tier = (
        DifficultyLevel.BEGINNER.value
        if res.topic_id == weak_topic_id and spec.weak_score < 45.0
        else (
            DifficultyLevel.INTERMEDIATE.value
            if res.topic_id == weak_topic_id and spec.weak_score < 70.0
            else spec.experience.value
        )
    )
    diff_gap = abs(tier_pos[res.difficulty] - tier_pos[target_tier])
    if diff_gap == 0:
        base += 0.65
    elif diff_gap == 1:
        base += 0.10
    else:
        base -= 0.60

    text_blob = f"{res.title} {res.description}".lower()
    kw_hits = sum(1 for kw in spec.preferred_keywords if kw in text_blob)
    base += min(0.45, kw_hits * 0.20)

    # Collaborative peer-gem signal shared across learners of the same archetype
    base += latent_peer_bonus.get((spec.code, res.resource_id), 0.0)

    noisy = base + rng.gauss(0.0, 0.28)
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
            if draw > 0.76:
                latent_peer_bonus[(spec.code, res.resource_id)] = 1.05
            elif draw < 0.22:
                latent_peer_bonus[(spec.code, res.resource_id)] = -0.85

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

        unlocked_topic_ids = {
            topics_by_slug[s].topic_id for s in (*spec.mastered_slugs, spec.weak_slug)
        }
        weak_tid = topics_by_slug[spec.weak_slug].topic_id
        unlocked_pool = [r for r in en_resources if r.topic_id in unlocked_topic_ids]
        mastered_pool = [r for r in unlocked_pool if r.topic_id != weak_tid]
        weak_pool = [r for r in unlocked_pool if r.topic_id == weak_tid]

        if is_cold_start:
            # Cold-start learners have 0 train/val history and 4 late test-window ratings in unlocked topics
            chosen_early: list[Resource] = []
            weak_sample = rng.sample(weak_pool, k=min(3, len(weak_pool)))
            mastered_sample = rng.sample(mastered_pool, k=min(1, len(mastered_pool)))
            chosen_late = weak_sample + mastered_sample
        else:
            # Keep >= 8 unlocked resources unseen after early history so top-5 ranking is non-trivial
            early_mastered_k = min(9, max(4, len(mastered_pool) - 3))
            early_weak_k = min(2, len(weak_pool))
            chosen_early = (
                rng.sample(mastered_pool, k=early_mastered_k)
                + rng.sample(weak_pool, k=early_weak_k)
            )
            rng.shuffle(chosen_early)

            remaining_weak = [r for r in weak_pool if r not in chosen_early]
            remaining_mastered = [r for r in mastered_pool if r not in chosen_early]
            late_weak = rng.sample(remaining_weak, k=min(3, len(remaining_weak)))
            late_mastered = rng.sample(remaining_mastered, k=min(2, len(remaining_mastered)))
            chosen_late = late_weak + late_mastered
            rng.shuffle(chosen_late)

        # Early interactions fall in days 1..38 (Train window)
        for step_idx, res in enumerate(chosen_early):
            ts = base_time + timedelta(
                days=1 + (step_idx * 3) + rng.uniform(0.0, 1.8),
                minutes=idx * 7,
            )
            rating = _score_latent_utility(res, spec, weak_tid, latent_peer_bonus, rng)
            db.add(
                Feedback(
                    student_id=user.user_id,
                    resource_id=res.resource_id,
                    rating=rating,
                    comment=None,
                    created_at=ts,
                )
            )

        # Late interactions: warm learners span Validation (days 44..51) & Test (days 53..64);
        # cold-start learners fall strictly in the Test window (days 57..65) with 0 train/val leakage.
        for late_idx, res in enumerate(chosen_late):
            if is_cold_start:
                day_offset = 57.0 + late_idx * 2.0 + rng.uniform(0.0, 0.9)
            else:
                # First 2 late items land in Validation window (days 44..50); remaining land in Test (days 54..63)
                if late_idx < 2:
                    day_offset = 44.0 + late_idx * 2.5 + rng.uniform(0.0, 2.2)
                else:
                    day_offset = 54.0 + (late_idx - 2) * 2.8 + rng.uniform(0.0, 2.4)

            ts = base_time + timedelta(days=day_offset, minutes=idx * 11)
            rating = _score_latent_utility(res, spec, weak_tid, latent_peer_bonus, rng)
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
