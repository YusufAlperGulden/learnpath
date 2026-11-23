"""Pure-Python DFS prerequisite DAG validator, question versioning, and catalog cache hooks."""

from collections import defaultdict
from collections.abc import Callable, Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assessment import Answer
from app.models.catalog import Question
from app.schemas.catalog import QuestionUpdate


class DAGCycleError(ValueError):
    """Raised when adding prerequisite edges would create a self-loop or cycle."""


_catalog_generation: int = 0
_catalog_invalidation_hooks: list[Callable[[], None]] = []


def get_catalog_generation() -> int:
    """Monotonic counter incremented whenever active resource metadata mutates."""
    return _catalog_generation


def register_catalog_invalidation_hook(hook: Callable[[], None]) -> None:
    """Registers a callback (e.g. TF-IDF matrix cache reset) invoked on catalog writes."""
    if hook not in _catalog_invalidation_hooks:
        _catalog_invalidation_hooks.append(hook)


def notify_catalog_changed() -> None:
    """Increments catalog generation and notifies registered recommender caches."""
    global _catalog_generation
    _catalog_generation += 1
    for hook in _catalog_invalidation_hooks:
        hook()


def validate_prerequisite_dag(
    existing_edges: Iterable[tuple[UUID, UUID]],
    target_topic_id: UUID,
    new_prerequisite_ids: Iterable[UUID],
) -> None:
    """Validates that assigning `new_prerequisite_ids` to `target_topic_id` keeps the graph acyclic.

    Each edge in `existing_edges` is `(topic_id, prerequisite_topic_id)`, meaning
    `prerequisite_topic_id` must be mastered BEFORE `topic_id`.
    """
    prereq_set = set(new_prerequisite_ids)
    if target_topic_id in prereq_set:
        raise DAGCycleError("A topic cannot list itself as a prerequisite.")

    prereqs_by_topic: dict[UUID, set[UUID]] = defaultdict(set)
    nodes: set[UUID] = {target_topic_id} | prereq_set

    for topic_id, prereq_id in existing_edges:
        nodes.add(topic_id)
        nodes.add(prereq_id)
        if topic_id != target_topic_id:
            prereqs_by_topic[topic_id].add(prereq_id)

    prereqs_by_topic[target_topic_id] = set(prereq_set)

    # Standard 3-color DFS cycle check (0 = unvisited, 1 = visiting, 2 = visited)
    state: dict[UUID, int] = {node: 0 for node in nodes}

    def dfs(node: UUID) -> None:
        state[node] = 1
        for neighbor in prereqs_by_topic.get(node, ()):
            neighbor_state = state.get(neighbor, 0)
            if neighbor_state == 1:
                raise DAGCycleError(
                    f"Circular prerequisite dependency detected involving topic {neighbor}."
                )
            if neighbor_state == 0:
                dfs(neighbor)
        state[node] = 2

    for node in list(nodes):
        if state.get(node, 0) == 0:
            dfs(node)


def is_question_answered(db: Session, question_id: UUID) -> bool:
    """Returns True if at least one historical Answer references `question_id`."""
    count = db.scalar(
        select(func.count()).select_from(Answer).where(Answer.question_id == question_id)
    )
    return bool(count and count > 0)


def apply_question_update(
    db: Session,
    question: Question,
    payload: QuestionUpdate,
    admin_user_id: UUID,
) -> tuple[Question, bool]:
    """Updates a question while preserving historical TestAttempt/Answer integrity (FR12).

    - If the question has already been answered in any exam AND any substantive field
      (topic, stem, code snippet, options, answer key, explanation, or difficulty) changes:
      1. The existing row's content is left untouched and marked `is_active = False`.
      2. A new row is inserted with `version = old.version + 1` and
         `previous_question_id = old.question_id`.
    - Otherwise (unanswered question or status-only toggle), updates the row in place.

    Returns `(resulting_question, created_new_version)`.
    """
    fields_set = payload.model_fields_set

    next_topic_id = (
        payload.topic_id
        if "topic_id" in fields_set and payload.topic_id is not None
        else question.topic_id
    )
    next_text = (
        payload.question_text.strip()
        if "question_text" in fields_set and payload.question_text is not None
        else question.question_text
    )
    if "code_snippet" in fields_set:
        raw_snippet = payload.code_snippet
        next_snippet = raw_snippet if raw_snippet and raw_snippet.strip() else None
    else:
        next_snippet = question.code_snippet

    next_opt_a = (
        payload.option_a.strip()
        if "option_a" in fields_set and payload.option_a is not None
        else question.option_a
    )
    next_opt_b = (
        payload.option_b.strip()
        if "option_b" in fields_set and payload.option_b is not None
        else question.option_b
    )
    next_opt_c = (
        payload.option_c.strip()
        if "option_c" in fields_set and payload.option_c is not None
        else question.option_c
    )
    next_opt_d = (
        payload.option_d.strip()
        if "option_d" in fields_set and payload.option_d is not None
        else question.option_d
    )
    next_correct = (
        payload.correct_option.value
        if "correct_option" in fields_set and payload.correct_option is not None
        else question.correct_option
    )
    next_explanation = (
        payload.explanation.strip()
        if "explanation" in fields_set and payload.explanation is not None
        else question.explanation
    )
    next_difficulty = (
        payload.difficulty.value
        if "difficulty" in fields_set and payload.difficulty is not None
        else question.difficulty
    )
    next_is_active = (
        payload.is_active
        if "is_active" in fields_set and payload.is_active is not None
        else question.is_active
    )

    substantive_changed = (
        next_topic_id != question.topic_id
        or next_text != question.question_text
        or next_snippet != question.code_snippet
        or next_opt_a != question.option_a
        or next_opt_b != question.option_b
        or next_opt_c != question.option_c
        or next_opt_d != question.option_d
        or next_correct != question.correct_option
        or next_explanation != question.explanation
        or next_difficulty != question.difficulty
    )

    answered = is_question_answered(db, question.question_id)

    if answered and substantive_changed:
        question.is_active = False
        new_version = Question(
            topic_id=next_topic_id,
            created_by=admin_user_id,
            question_text=next_text,
            code_snippet=next_snippet,
            option_a=next_opt_a,
            option_b=next_opt_b,
            option_c=next_opt_c,
            option_d=next_opt_d,
            correct_option=next_correct,
            explanation=next_explanation,
            difficulty=next_difficulty,
            version=question.version + 1,
            previous_question_id=question.question_id,
            is_active=True if "is_active" not in fields_set else bool(next_is_active),
        )
        db.add(new_version)
        db.flush()
        return new_version, True

    question.topic_id = next_topic_id
    question.question_text = next_text
    question.code_snippet = next_snippet
    question.option_a = next_opt_a
    question.option_b = next_opt_b
    question.option_c = next_opt_c
    question.option_d = next_opt_d
    question.correct_option = next_correct
    question.explanation = next_explanation
    question.difficulty = next_difficulty
    question.is_active = bool(next_is_active)
    db.flush()
    return question, False
