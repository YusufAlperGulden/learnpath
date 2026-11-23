"""Atomic assessment delivery, submission, and post-submit review schemas (FR03–FR04)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import AnswerOption, MasteryStatus, TestType


class AssessmentQuestionPublic(BaseModel):
    """Question payload sent BEFORE submission — strictly omits correct_option & explanation."""

    question_id: UUID
    topic_id: UUID
    topic_name: str
    question_text: str
    code_snippet: str | None = None
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class AssessmentQuestionsResponse(BaseModel):
    attempt_id: UUID
    test_type: TestType
    target_topic_id: UUID | None = None
    test_session_token: str
    questions: list[AssessmentQuestionPublic]


class SubmittedAnswerItem(BaseModel):
    question_id: UUID
    selected_option: AnswerOption | None = None


class AssessmentSubmitRequest(BaseModel):
    attempt_id: UUID
    test_session_token: str = Field(min_length=16)
    answers: list[SubmittedAnswerItem] = Field(min_length=1)

    @model_validator(mode="after")
    def check_unique_question_ids(self) -> "AssessmentSubmitRequest":
        ids = [item.question_id for item in self.answers]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate question_id entries are not permitted in answers.")
        return self


class TopicScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: UUID
    topic_name: str
    correct_count: int
    question_count: int
    score_percent: float
    mastery_status: MasteryStatus


class AnswerReviewItem(BaseModel):
    """Post-submission answer review including solution & explanation (Figma Fig. 5)."""

    question_id: UUID
    topic_id: UUID
    topic_name: str
    question_text: str
    code_snippet: str | None = None
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    selected_option: AnswerOption | None
    correct_option: AnswerOption
    is_correct: bool
    is_skipped: bool
    explanation: str


class AssessmentAttemptSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID
    test_type: TestType
    target_topic_id: UUID | None
    overall_score_percent: float
    started_at: datetime
    submitted_at: datetime


class AssessmentAttemptDetailResponse(AssessmentAttemptSummary):
    topic_scores: list[TopicScoreRead]
    answers: list[AnswerReviewItem]
