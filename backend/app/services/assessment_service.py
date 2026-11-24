"""Atomic assessment engine: stateless question delivery, single-transaction grading, and review."""

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.enums import AnswerOption, DifficultyLevel, MasteryStatus, TestType
from app.core.logging_config import get_logger
from app.core.security import (
    TokenValidationError,
    create_test_session_token,
    decode_test_session_token,
)
from app.models.assessment import Answer, TestAttempt, TopicScore
from app.models.catalog import Question, Topic, TopicPrerequisite
from app.models.progress import TopicProgress
from app.schemas.assessment import (
    AnswerReviewItem,
    AssessmentAttemptDetailResponse,
    AssessmentAttemptSummary,
    AssessmentQuestionPublic,
    AssessmentQuestionsResponse,
    AssessmentSubmitRequest,
    TopicScoreRead,
)
from app.services.mastery import calculate_mastery_status

logger = get_logger("assessment")

DIAGNOSTIC_QUESTIONS_PER_TOPIC = 2
TOPIC_QUIZ_MAX_QUESTIONS = 6

_DIFFICULTY_ORDER = {
    DifficultyLevel.BEGINNER.value: 0,
    DifficultyLevel.INTERMEDIATE.value: 1,
    DifficultyLevel.ADVANCED.value: 2,
}


def _select_stratified_questions(questions: list[Question], limit: int) -> list[Question]:
    """Selects up to `limit` questions spread evenly across difficulty tiers."""
    if len(questions) <= limit:
        return sorted(
            questions,
            key=lambda q: (_DIFFICULTY_ORDER.get(q.difficulty, 99), str(q.question_id)),
        )

    by_diff: dict[str, list[Question]] = defaultdict(list)
    for q in sorted(questions, key=lambda item: str(item.question_id)):
        by_diff[q.difficulty].append(q)

    ordered_tiers = [
        DifficultyLevel.BEGINNER.value,
        DifficultyLevel.INTERMEDIATE.value,
        DifficultyLevel.ADVANCED.value,
    ]
    picked: list[Question] = []
    idx_by_tier = {tier: 0 for tier in ordered_tiers}

    while len(picked) < limit:
        progressed = False
        for tier in ordered_tiers:
            bucket = by_diff.get(tier, [])
            pos = idx_by_tier[tier]
            if pos < len(bucket):
                picked.append(bucket[pos])
                idx_by_tier[tier] = pos + 1
                progressed = True
                if len(picked) >= limit:
                    break
        if not progressed:
            break

    return picked


def _verify_topic_unlocked_for_quiz(
    db: Session,
    student_id: UUID,
    target_topic_id: UUID,
) -> None:
    """Enforces FR05 prerequisite locking on TOPIC_QUIZ attempts."""
    prereq_links = db.scalars(
        select(TopicPrerequisite)
        .options(selectinload(TopicPrerequisite.prerequisite_topic))
        .where(TopicPrerequisite.topic_id == target_topic_id)
    ).all()
    if not prereq_links:
        return

    prereq_ids = [link.prerequisite_topic_id for link in prereq_links]
    progress_rows = db.scalars(
        select(TopicProgress).where(
            TopicProgress.student_id == student_id,
            TopicProgress.topic_id.in_(prereq_ids),
        )
    ).all()
    mastery_by_topic = {row.topic_id: row.mastery_status for row in progress_rows}

    unmet_names = [
        link.prerequisite_topic.name
        for link in prereq_links
        if mastery_by_topic.get(link.prerequisite_topic_id) != MasteryStatus.MASTERED.value
    ]
    if unmet_names:
        joined = ", ".join(unmet_names)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Topic is locked until prerequisite topic(s) reach MASTERED (>= 70%): {joined}."
            ),
        )


def prepare_assessment_questions(
    db: Session,
    *,
    student_id: UUID,
    test_type: TestType,
    target_topic_id: UUID | None,
) -> AssessmentQuestionsResponse:
    """Builds an assessment question packet and signed token WITHOUT writing draft DB rows."""
    if test_type == TestType.DIAGNOSTIC:
        if target_topic_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="target_topic_id must be omitted when test_type is DIAGNOSTIC.",
            )
        topics = db.scalars(
            select(Topic).order_by(Topic.display_order.asc(), Topic.name.asc())
        ).all()
        active_questions = db.scalars(
            select(Question).where(Question.is_active.is_(True))
        ).all()
        by_topic: dict[UUID, list[Question]] = defaultdict(list)
        for q in active_questions:
            by_topic[q.topic_id].append(q)

        selected: list[tuple[Topic, Question]] = []
        for topic in topics:
            picked = _select_stratified_questions(
                by_topic.get(topic.topic_id, []),
                DIAGNOSTIC_QUESTIONS_PER_TOPIC,
            )
            for q in picked:
                selected.append((topic, q))
    else:
        if target_topic_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="target_topic_id is required when test_type is TOPIC_QUIZ.",
            )
        topic = db.get(Topic, target_topic_id)
        if topic is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target topic not found.",
            )
        _verify_topic_unlocked_for_quiz(db, student_id=student_id, target_topic_id=target_topic_id)

        topic_questions = db.scalars(
            select(Question).where(
                Question.topic_id == target_topic_id,
                Question.is_active.is_(True),
            )
        ).all()
        picked = _select_stratified_questions(topic_questions, TOPIC_QUIZ_MAX_QUESTIONS)
        selected = [(topic, q) for q in picked]

    if not selected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active assessment questions are available for this selection.",
        )

    attempt_id = uuid4()
    started_at = datetime.now(UTC)
    question_ids = [q.question_id for _, q in selected]

    session_token = create_test_session_token(
        student_id=student_id,
        attempt_id=attempt_id,
        test_type=test_type,
        target_topic_id=target_topic_id,
        question_ids=question_ids,
        started_at=started_at,
    )

    public_questions = [
        AssessmentQuestionPublic(
            question_id=q.question_id,
            topic_id=topic.topic_id,
            topic_name=topic.name,
            question_text=q.question_text,
            code_snippet=q.code_snippet,
            option_a=q.option_a,
            option_b=q.option_b,
            option_c=q.option_c,
            option_d=q.option_d,
        )
        for topic, q in selected
    ]

    logger.info(
        "Issued stateless test session student_id=%s attempt_id=%s type=%s count=%d",
        student_id,
        attempt_id,
        test_type.value,
        len(public_questions),
    )

    return AssessmentQuestionsResponse(
        attempt_id=attempt_id,
        test_type=test_type,
        target_topic_id=target_topic_id,
        test_session_token=session_token,
        questions=public_questions,
    )


def _build_attempt_detail_response(
    attempt: TestAttempt,
    ordered_question_ids: list[UUID] | None = None,
) -> AssessmentAttemptDetailResponse:
    order_index = (
        {qid: idx for idx, qid in enumerate(ordered_question_ids)}
        if ordered_question_ids is not None
        else {}
    )
    sorted_answers = sorted(
        attempt.answers,
        key=lambda a: (
            order_index.get(a.question_id, 10_000),
            a.question.topic.display_order if a.question and a.question.topic else 0,
            str(a.question_id),
        ),
    )

    answer_items = [
        AnswerReviewItem(
            question_id=ans.question_id,
            topic_id=ans.question.topic_id,
            topic_name=ans.question.topic.name,
            question_text=ans.question.question_text,
            code_snippet=ans.question.code_snippet,
            option_a=ans.question.option_a,
            option_b=ans.question.option_b,
            option_c=ans.question.option_c,
            option_d=ans.question.option_d,
            selected_option=(
                AnswerOption(ans.selected_option) if ans.selected_option is not None else None
            ),
            correct_option=AnswerOption(ans.question.correct_option),
            is_correct=ans.is_correct,
            is_skipped=ans.selected_option is None,
            explanation=ans.question.explanation,
        )
        for ans in sorted_answers
    ]

    sorted_topic_scores = sorted(
        attempt.topic_scores,
        key=lambda ts: (ts.topic.display_order if ts.topic else 0, ts.topic.name if ts.topic else ""),
    )
    topic_score_items = [
        TopicScoreRead(
            topic_id=ts.topic_id,
            topic_name=ts.topic.name,
            correct_count=ts.correct_count,
            question_count=ts.question_count,
            score_percent=ts.score_percent,
            mastery_status=calculate_mastery_status(ts.score_percent),
        )
        for ts in sorted_topic_scores
    ]

    return AssessmentAttemptDetailResponse(
        attempt_id=attempt.attempt_id,
        test_type=TestType(attempt.test_type),
        target_topic_id=attempt.target_topic_id,
        overall_score_percent=attempt.overall_score_percent,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        topic_scores=topic_score_items,
        answers=answer_items,
    )


def get_student_attempt_detail(
    db: Session,
    *,
    student_id: UUID,
    attempt_id: UUID,
    ordered_question_ids: list[UUID] | None = None,
) -> AssessmentAttemptDetailResponse:
    stmt = (
        select(TestAttempt)
        .options(
            selectinload(TestAttempt.answers)
            .selectinload(Answer.question)
            .selectinload(Question.topic),
            selectinload(TestAttempt.topic_scores).selectinload(TopicScore.topic),
        )
        .where(
            TestAttempt.attempt_id == attempt_id,
            TestAttempt.student_id == student_id,
        )
    )
    attempt = db.scalar(stmt)
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment attempt not found.",
        )
    return _build_attempt_detail_response(attempt, ordered_question_ids=ordered_question_ids)


def list_student_attempts(
    db: Session,
    *,
    student_id: UUID,
) -> list[AssessmentAttemptSummary]:
    attempts = db.scalars(
        select(TestAttempt)
        .where(TestAttempt.student_id == student_id)
        .order_by(TestAttempt.submitted_at.desc())
    ).all()
    return [AssessmentAttemptSummary.model_validate(item) for item in attempts]


def submit_assessment_atomic(
    db: Session,
    *,
    student_id: UUID,
    payload: AssessmentSubmitRequest,
) -> AssessmentAttemptDetailResponse:
    """Validates session token, enforces idempotency, and persists the attempt in 1 transaction."""
    try:
        claims = decode_test_session_token(payload.test_session_token)
        token_student_id = UUID(claims["sub"])
        token_attempt_id = UUID(claims["attempt_id"])
        token_test_type = TestType(claims["test_type"])
        raw_target_topic = claims.get("target_topic_id")
        token_target_topic_id = UUID(raw_target_topic) if raw_target_topic else None
        expected_q_ids = [UUID(qid) for qid in claims["question_ids"]]
        started_at = datetime.fromisoformat(claims["started_at"])
    except (TokenValidationError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired test_session_token: {exc}",
        ) from exc

    if token_student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This test_session_token belongs to a different student account.",
        )

    if token_attempt_id != payload.attempt_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="attempt_id does not match the signed test_session_token.",
        )

    # Idempotent retry handling (NFR-04 double-click / network retry protection)
    existing_attempt = db.get(TestAttempt, payload.attempt_id)
    if existing_attempt is not None:
        if existing_attempt.student_id != student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Attempt ID belongs to another user.",
            )
        logger.info("Idempotent replay returning existing attempt_id=%s", payload.attempt_id)
        return get_student_attempt_detail(
            db,
            student_id=student_id,
            attempt_id=payload.attempt_id,
            ordered_question_ids=expected_q_ids,
        )

    submitted_by_qid: dict[UUID, AnswerOption | None] = {
        item.question_id: item.selected_option for item in payload.answers
    }
    expected_set = set(expected_q_ids)
    submitted_set = set(submitted_by_qid.keys())

    if submitted_set != expected_set:
        missing = [str(qid) for qid in expected_q_ids if qid not in submitted_set]
        extra = [str(qid) for qid in submitted_by_qid if qid not in expected_set]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Submitted answers must match the exact session question list "
                f"(missing={missing}, unexpected={extra})."
            ),
        )

    questions = db.scalars(
        select(Question)
        .options(selectinload(Question.topic))
        .where(Question.question_id.in_(expected_q_ids))
    ).all()
    question_by_id = {q.question_id: q for q in questions}

    if len(question_by_id) != len(expected_q_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="One or more session questions could not be resolved.",
        )

    now = datetime.now(UTC)
    total_questions = len(expected_q_ids)
    total_correct = 0
    skipped_count = 0

    topic_tallies: dict[UUID, list[int]] = defaultdict(lambda: [0, 0])  # [correct, count]
    scored_rows: list[tuple[UUID, str | None, bool]] = []

    for qid in expected_q_ids:
        question = question_by_id[qid]
        selected_opt = submitted_by_qid[qid]
        if selected_opt is None:
            is_correct = False
            skipped_count += 1
            selected_str = None
        else:
            selected_str = selected_opt.value
            is_correct = selected_str == question.correct_option

        if is_correct:
            total_correct += 1
            topic_tallies[question.topic_id][0] += 1
        topic_tallies[question.topic_id][1] += 1
        scored_rows.append((qid, selected_str, is_correct))

    overall_score_percent = round((total_correct / total_questions) * 100.0, 2)

    try:
        attempt = TestAttempt(
            attempt_id=payload.attempt_id,
            student_id=student_id,
            test_type=token_test_type.value,
            target_topic_id=token_target_topic_id,
            overall_score_percent=overall_score_percent,
            started_at=started_at,
            submitted_at=now,
        )
        db.add(attempt)
        db.flush()

        for qid, selected_str, is_correct in scored_rows:
            db.add(
                Answer(
                    attempt_id=attempt.attempt_id,
                    question_id=qid,
                    selected_option=selected_str,
                    is_correct=is_correct,
                )
            )

        existing_progress = {
            tp.topic_id: tp
            for tp in db.scalars(
                select(TopicProgress).where(
                    TopicProgress.student_id == student_id,
                    TopicProgress.topic_id.in_(list(topic_tallies.keys())),
                )
            ).all()
        }

        for topic_id, (correct_cnt, question_cnt) in topic_tallies.items():
            topic_pct = round((correct_cnt / question_cnt) * 100.0, 2)
            db.add(
                TopicScore(
                    attempt_id=attempt.attempt_id,
                    topic_id=topic_id,
                    correct_count=correct_cnt,
                    question_count=question_cnt,
                    score_percent=topic_pct,
                )
            )

            next_mastery = calculate_mastery_status(topic_pct).value
            prog = existing_progress.get(topic_id)
            if prog is None:
                db.add(
                    TopicProgress(
                        student_id=student_id,
                        topic_id=topic_id,
                        is_manually_completed=False,
                        manually_completed_at=None,
                        latest_score_percent=topic_pct,
                        mastery_status=next_mastery,
                        updated_at=now,
                    )
                )
            else:
                prog.latest_score_percent = topic_pct
                prog.mastery_status = next_mastery
                prog.updated_at = now

        db.commit()
    except IntegrityError:
        db.rollback()
        raced = db.get(TestAttempt, payload.attempt_id)
        if raced is not None and raced.student_id == student_id:
            return get_student_attempt_detail(
                db,
                student_id=student_id,
                attempt_id=payload.attempt_id,
                ordered_question_ids=expected_q_ids,
            )
        raise
    except Exception:
        db.rollback()
        raise

    logger.info(
        "Recorded atomic TestAttempt attempt_id=%s student_id=%s type=%s score=%.2f skipped=%d",
        payload.attempt_id,
        student_id,
        token_test_type.value,
        overall_score_percent,
        skipped_count,
    )

    return get_student_attempt_detail(
        db,
        student_id=student_id,
        attempt_id=payload.attempt_id,
        ordered_question_ids=expected_q_ids,
    )
