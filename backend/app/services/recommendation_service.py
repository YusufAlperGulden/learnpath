"""Prerequisite-aware learning path and explainable recommendation orchestration (FR05–FR07)."""

import time
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    ContentType,
    DifficultyLevel,
    ExperienceLevel,
    MasteryStatus,
    ResourceProgressStatus,
    SupportedLanguage,
)
from app.core.logging_config import get_logger
from app.models.catalog import Resource, Topic
from app.models.progress import ResourceProgress, TopicProgress
from app.models.user import User
from app.schemas.recommendation import (
    LearningPathEdge,
    LearningPathNode,
    LearningPathResponse,
    PriorityTopicSummary,
    RecommendationResponse,
    RecommendedResourceItem,
    RecommenderStrategy,
)
from app.services.recommenders import (
    CandidateResource,
    RuleBasedRecommender,
    StudentRecommendationContext,
)

logger = get_logger("recommendations")

MAX_PRIORITY_TOPICS = 3
_rule_recommender = RuleBasedRecommender()


def _select_recommended_next_topic_id(nodes: list[LearningPathNode]) -> UUID | None:
    unlocked_needs_practice = [
        n
        for n in nodes
        if not n.is_locked and n.mastery_status == MasteryStatus.NEEDS_PRACTICE
    ]
    if unlocked_needs_practice:
        unlocked_needs_practice.sort(
            key=lambda n: (
                n.latest_score_percent if n.latest_score_percent is not None else 0.0,
                n.display_order,
            )
        )
        return unlocked_needs_practice[0].topic_id

    unlocked_unknown = [
        n for n in nodes if not n.is_locked and n.mastery_status == MasteryStatus.UNKNOWN
    ]
    if unlocked_unknown:
        unlocked_unknown.sort(key=lambda n: n.display_order)
        return unlocked_unknown[0].topic_id

    return None


def compute_learning_path(db: Session, *, student_id: UUID) -> LearningPathResponse:
    """Computes student curriculum DAG nodes, lock states, and next priority topic (FR05)."""
    topics = db.scalars(
        select(Topic)
        .options(selectinload(Topic.prerequisite_links))
        .order_by(Topic.display_order.asc(), Topic.name.asc())
    ).all()
    progress_rows = db.scalars(
        select(TopicProgress).where(TopicProgress.student_id == student_id)
    ).all()
    progress_by_topic = {row.topic_id: row for row in progress_rows}

    nodes: list[LearningPathNode] = []
    edges: list[LearningPathEdge] = []

    for topic in topics:
        unmet_prereqs = [
            link.prerequisite_topic_id
            for link in topic.prerequisite_links
            if (
                progress_by_topic.get(link.prerequisite_topic_id) is None
                or progress_by_topic[link.prerequisite_topic_id].mastery_status
                != MasteryStatus.MASTERED.value
            )
        ]
        for link in topic.prerequisite_links:
            edges.append(
                LearningPathEdge(
                    prerequisite_topic_id=link.prerequisite_topic_id,
                    topic_id=topic.topic_id,
                )
            )

        prog = progress_by_topic.get(topic.topic_id)
        mastery = (
            MasteryStatus(prog.mastery_status) if prog is not None else MasteryStatus.UNKNOWN
        )
        nodes.append(
            LearningPathNode(
                topic_id=topic.topic_id,
                name=topic.name,
                slug=topic.slug,
                description=topic.description,
                display_order=topic.display_order,
                is_locked=len(unmet_prereqs) > 0,
                unmet_prerequisite_ids=unmet_prereqs,
                is_manually_completed=prog.is_manually_completed if prog is not None else False,
                latest_score_percent=prog.latest_score_percent if prog is not None else None,
                mastery_status=mastery,
            )
        )

    return LearningPathResponse(
        nodes=nodes,
        edges=edges,
        recommended_next_topic_id=_select_recommended_next_topic_id(nodes),
    )


def _find_unlocked_unmet_ancestors(
    target_node: LearningPathNode,
    nodes_by_id: dict[UUID, LearningPathNode],
) -> list[LearningPathNode]:
    """Walks prerequisite links upwards to find unlocked unmet prerequisite topics (FR05)."""
    found: dict[UUID, LearningPathNode] = {}
    visited: set[UUID] = set()
    stack: list[UUID] = list(target_node.unmet_prerequisite_ids)

    while stack:
        curr_id = stack.pop()
        if curr_id in visited:
            continue
        visited.add(curr_id)
        node = nodes_by_id.get(curr_id)
        if node is None or node.mastery_status == MasteryStatus.MASTERED:
            continue
        if not node.is_locked:
            found[node.topic_id] = node
        else:
            stack.extend(node.unmet_prerequisite_ids)

    return sorted(found.values(), key=lambda n: n.display_order)


def _resolve_priority_topics(
    path: LearningPathResponse,
    target_topic_id: UUID | None,
) -> tuple[list[LearningPathNode], bool, str | None]:
    nodes_by_id = {n.topic_id: n for n in path.nodes}

    if target_topic_id is not None:
        target = nodes_by_id.get(target_topic_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested topic_id does not exist.",
            )
        if target.is_locked:
            prereq_nodes = _find_unlocked_unmet_ancestors(target, nodes_by_id)
            return prereq_nodes, True, "prerequisite_not_mastered"
        return [target], False, None

    unlocked_needs_practice = sorted(
        [
            n
            for n in path.nodes
            if not n.is_locked and n.mastery_status == MasteryStatus.NEEDS_PRACTICE
        ],
        key=lambda n: (
            n.latest_score_percent if n.latest_score_percent is not None else 0.0,
            n.display_order,
        ),
    )
    unlocked_unknown = sorted(
        [
            n
            for n in path.nodes
            if not n.is_locked and n.mastery_status == MasteryStatus.UNKNOWN
        ],
        key=lambda n: n.display_order,
    )

    combined = (unlocked_needs_practice + unlocked_unknown)[:MAX_PRIORITY_TOPICS]
    if combined:
        return combined, False, None

    # All unlocked topics are MASTERED -> allow advanced enrichment on unlocked topics
    unlocked_all = sorted(
        [n for n in path.nodes if not n.is_locked],
        key=lambda n: (
            n.latest_score_percent if n.latest_score_percent is not None else 100.0,
            n.display_order,
        ),
    )
    return unlocked_all[:MAX_PRIORITY_TOPICS], False, None


def generate_student_recommendations(
    db: Session,
    *,
    student: User,
    strategy: RecommenderStrategy = "rule_based",
    limit: int = 5,
    target_topic_id: UUID | None = None,
) -> RecommendationResponse:
    """Filters eligible unseen resources and produces explainable recommendations (< 2.0s NFR-05)."""
    started = time.perf_counter()

    profile = student.profile
    if profile is not None:
        experience = ExperienceLevel(profile.experience_level)
        preferred_formats = tuple(ContentType(fmt) for fmt in profile.preferred_formats)
        preferred_language = SupportedLanguage(profile.preferred_language)
        learning_goal = profile.learning_goal
    else:
        experience = ExperienceLevel.BEGINNER
        preferred_formats = (
            ContentType.VIDEO,
            ContentType.ARTICLE,
            ContentType.EXERCISE,
        )
        preferred_language = SupportedLanguage.EN
        learning_goal = "PYTHON_FUNDAMENTALS"

    path = compute_learning_path(db, student_id=student.user_id)
    priority_nodes, fallback_applied, fallback_reason = _resolve_priority_topics(
        path,
        target_topic_id=target_topic_id,
    )

    priority_summaries = [
        PriorityTopicSummary(
            topic_id=node.topic_id,
            name=node.name,
            score_percent=node.latest_score_percent,
            mastery_status=node.mastery_status,
        )
        for node in priority_nodes
    ]

    if not priority_nodes:
        return RecommendationResponse(
            strategy_used="rule_based",
            fallback_applied=fallback_applied,
            fallback_reason=fallback_reason,
            priority_topics=[],
            items=[],
        )

    priority_ids = [n.topic_id for n in priority_nodes]
    node_by_id = {n.topic_id: n for n in priority_nodes}

    completed_resource_ids = set(
        db.scalars(
            select(ResourceProgress.resource_id).where(
                ResourceProgress.student_id == student.user_id,
                ResourceProgress.status == ResourceProgressStatus.COMPLETED.value,
            )
        ).all()
    )

    stmt = select(Resource).where(
        Resource.is_active.is_(True),
        Resource.topic_id.in_(priority_ids),
        Resource.language == preferred_language.value,
    )
    if completed_resource_ids:
        stmt = stmt.where(Resource.resource_id.notin_(completed_resource_ids))

    raw_resources = db.scalars(stmt).all()

    all_candidates = [
        CandidateResource(
            resource_id=res.resource_id,
            topic_id=res.topic_id,
            topic_name=node_by_id[res.topic_id].name,
            topic_display_order=node_by_id[res.topic_id].display_order,
            title=res.title,
            description=res.description,
            external_url=res.external_url,
            content_type=ContentType(res.content_type),
            difficulty=DifficultyLevel(res.difficulty),
            language=SupportedLanguage(res.language),
            estimated_minutes=res.estimated_minutes,
        )
        for res in raw_resources
    ]

    preferred_set = set(preferred_formats)
    preferred_candidates = [c for c in all_candidates if c.content_type in preferred_set]
    relaxed_candidates = [c for c in all_candidates if c.content_type not in preferred_set]

    if len(preferred_candidates) >= limit or not relaxed_candidates:
        candidate_pool = preferred_candidates
    else:
        candidate_pool = preferred_candidates + relaxed_candidates

    context = StudentRecommendationContext(
        student_id=student.user_id,
        experience_level=experience,
        preferred_formats=preferred_formats,
        preferred_language=preferred_language,
        learning_goal=learning_goal,
        topic_scores={
            n.topic_id: n.latest_score_percent
            for n in path.nodes
            if n.latest_score_percent is not None
        },
        topic_mastery={n.topic_id: n.mastery_status for n in path.nodes},
    )

    strategy_used: RecommenderStrategy = strategy
    if strategy != "rule_based":
        # Increment 5 registers popularity, cbf, cf, and hybrid into this dispatcher
        strategy_used = "rule_based"
        fallback_applied = True
        fallback_reason = fallback_reason or f"strategy_{strategy}_fallback_to_rule_based"

    ranked = _rule_recommender.rank(candidate_pool, context, limit=limit)

    if any(item.format_fallback_used for item in ranked):
        fallback_applied = True
        if fallback_reason is None:
            fallback_reason = "preferred_format_relaxed"

    items = [
        RecommendedResourceItem(
            resource_id=entry.candidate.resource_id,
            title=entry.candidate.title,
            description=entry.candidate.description,
            external_url=entry.candidate.external_url,
            content_type=entry.candidate.content_type,
            difficulty=entry.candidate.difficulty,
            language=entry.candidate.language,
            estimated_minutes=entry.candidate.estimated_minutes,
            topic_id=entry.candidate.topic_id,
            topic_name=entry.candidate.topic_name,
            rank=idx,
            score=entry.score,
            format_fallback_used=entry.format_fallback_used,
            rationale=entry.rationale,
        )
        for idx, entry in enumerate(ranked, start=1)
    ]

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    logger.info(
        "Generated recommendations student_id=%s strategy=%s items=%d fallback=%s duration_ms=%.2f",
        student.user_id,
        strategy_used,
        len(items),
        fallback_reason,
        elapsed_ms,
    )

    return RecommendationResponse(
        strategy_used=strategy_used,
        fallback_applied=fallback_applied,
        fallback_reason=fallback_reason,
        priority_topics=priority_summaries,
        items=items,
    )
