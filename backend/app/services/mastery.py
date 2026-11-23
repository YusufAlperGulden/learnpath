"""Mastery status calculation rule synchronized with Revised RAD v2.0.

Mastery recalculates directly from the student's latest attempt score on a topic:
- None -> UNKNOWN
- >= MASTERY_THRESHOLD_PERCENT (70.0%) -> MASTERED
- < MASTERY_THRESHOLD_PERCENT -> NEEDS_PRACTICE
"""

from app.core.config import settings
from app.core.enums import MasteryStatus


def calculate_mastery_status(
    latest_score_percent: float | None,
    threshold_percent: float | None = None,
) -> MasteryStatus:
    if latest_score_percent is None:
        return MasteryStatus.UNKNOWN

    cutoff = (
        threshold_percent
        if threshold_percent is not None
        else settings.MASTERY_THRESHOLD_PERCENT
    )
    if latest_score_percent >= cutoff:
        return MasteryStatus.MASTERED
    return MasteryStatus.NEEDS_PRACTICE
