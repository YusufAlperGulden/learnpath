"""Increment 6 test suite: RAD Section 3.4.4 evaluation metrics, slices, bootstrap, and ablation."""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.enums import ContentType, DifficultyLevel, SupportedLanguage
from app.services.recommenders import CandidateResource
from experiments.evaluate_models import run_model_evaluation
from experiments.metrics import (
    bootstrap_mean_ci,
    compute_topic_format_diversity,
    compute_topic_tag_diversity,
    ndcg_at_k,
    paired_bootstrap_delta,
    precision_at_k,
    recall_at_k,
)
from experiments.run_ablation import (
    render_academic_evaluation_markdown,
    run_ablation_study,
)
from tests.test_foundation import db_session  # noqa: F401


def test_short_list_precision_diversity_and_paired_bootstrap_conventions() -> None:
    r1, r2, r3 = uuid4(), uuid4(), uuid4()
    relevant = {r1, r3}

    # Short recommendation list of length 2 (< K=5) must divide by 5 (missing slots non-relevant)
    assert precision_at_k([r1, r2], relevant, k=5) == 0.20
    assert recall_at_k([r1, r2], relevant, k=5) == 0.50
    assert 0.60 < ndcg_at_k([r1, r2], relevant, k=5) < 0.65

    t1, t2 = uuid4(), uuid4()
    cands = [
        CandidateResource(
            resource_id=r1,
            topic_id=t1,
            topic_name="Variables",
            topic_display_order=1,
            title="A",
            description="desc",
            external_url="https://example.org/1",
            content_type=ContentType.VIDEO,
            difficulty=DifficultyLevel.BEGINNER,
            language=SupportedLanguage.EN,
        ),
        CandidateResource(
            resource_id=r2,
            topic_id=t1,
            topic_name="Variables",
            topic_display_order=1,
            title="B",
            description="desc",
            external_url="https://example.org/2",
            content_type=ContentType.EXERCISE,
            difficulty=DifficultyLevel.BEGINNER,
            language=SupportedLanguage.EN,
        ),
        CandidateResource(
            resource_id=r3,
            topic_id=t2,
            topic_name="Loops",
            topic_display_order=2,
            title="C",
            description="desc",
            external_url="https://example.org/3",
            content_type=ContentType.VIDEO,
            difficulty=DifficultyLevel.BEGINNER,
            language=SupportedLanguage.EN,
        ),
    ]
    # Pairs: (t1,t1)->0, (t1,t2)->1, (t1,t2)->1 => 2/3
    assert abs(compute_topic_tag_diversity(cands) - (2.0 / 3.0)) < 1e-5
    assert 0.5 < compute_topic_format_diversity(cands) < 0.8

    vec_a = [0.8, 0.7, 0.9, 0.85, 0.75, 0.8, 0.9, 0.85]
    vec_b = [0.3, 0.25, 0.4, 0.35, 0.2, 0.3, 0.35, 0.3]
    ci_a = bootstrap_mean_ci(vec_a, n_boot=300, seed=42)
    assert ci_a.ci_95_low <= ci_a.mean <= ci_a.ci_95_high

    delta = paired_bootstrap_delta(
        vec_a,
        vec_b,
        comparison="A - B",
        metric="NDCG@5",
        n_boot=300,
        seed=42,
    )
    assert delta.mean_delta > 0.4
    assert delta.ci_95_low > 0.0
    assert delta.statistically_significant_95 is True


def test_full_evaluation_and_ablation_pipeline_rq1_to_rq4_and_nfr05(
    db_session: Session,  # noqa: F811
) -> None:
    eval_report = run_model_evaluation(
        db_session,
        db_backend="sqlite_in_memory",
        n_boot=200,
        latency_iterations=5,
        write_artifacts=False,
    )

    assert eval_report.provenance.data_origin == "documented_cohort_simulation"
    assert eval_report.provenance.evaluated_test_students == 48
    assert eval_report.provenance.warm_start_test_students == 40
    assert eval_report.provenance.cold_start_test_students == 8

    by_key = {m.model_key: m for m in eval_report.models}
    assert {"popularity", "cbf", "cf", "hybrid", "rule_based"} <= set(by_key)

    hybrid = by_key["hybrid"]
    pop = by_key["popularity"]
    cf = by_key["cf"]
    cbf = by_key["cbf"]

    # Zero-relevant query accounting rule (RAD Section 3.4.4)
    assert (
        hybrid.overall.evaluated_relevant_queries
        + hybrid.overall.excluded_zero_relevant_queries
        == hybrid.overall.total_queries
    )
    assert hybrid.overall.excluded_zero_relevant_queries >= 0

    # RQ1: Hybrid outperforms Popularity and CF baselines on Test NDCG@5
    assert hybrid.overall.ndcg_at_5.mean > pop.overall.ndcg_at_5.mean
    assert hybrid.overall.ndcg_at_5.mean > cf.overall.ndcg_at_5.mean
    assert hybrid.warm_start.ndcg_at_5.mean >= cbf.warm_start.ndcg_at_5.mean

    # RQ2: Cold-start learners trigger 100% fallback to CBF under Hybrid
    assert hybrid.cold_start.cold_start_fallback_rate == 1.0
    assert abs(hybrid.cold_start.ndcg_at_5.mean - cbf.cold_start.ndcg_at_5.mean) < 1e-6

    # RQ4 & NFR-05: Coverage, diversity, and < 2.0s end-to-end latency
    assert 0.0 < hybrid.catalog_coverage_eligible <= 1.0
    assert 0.0 < hybrid.tfidf_cosine_diversity_at_5.mean <= 1.0
    assert eval_report.end_to_end_latency.passes_nfr05 is True
    assert eval_report.end_to_end_latency.assessment_plus_recommendation_p95_ms < 2000.0

    # RQ3: Four controlled ablation conditions + Markdown report generation
    ablation_report = run_ablation_study(
        db_session,
        db_backend="sqlite_in_memory",
        n_boot=200,
        write_artifacts=False,
    )
    cond_by_key = {c.condition_key: c for c in ablation_report.conditions}
    assert set(cond_by_key) == {
        "full_hybrid",
        "no_profile_preferences",
        "no_assessment_features",
        "no_collaborative_evidence",
    }
    assert (
        cond_by_key["full_hybrid"].overall.ndcg_at_5.mean
        > cond_by_key["no_assessment_features"].overall.ndcg_at_5.mean
    )
    assert (
        cond_by_key["full_hybrid"].overall.ndcg_at_5.mean
        >= cond_by_key["no_profile_preferences"].overall.ndcg_at_5.mean
    )

    md = render_academic_evaluation_markdown(eval_report, ablation_report)
    for required_heading in ("RQ1", "RQ2", "RQ3", "RQ4", "NFR-05", "Research Limitations"):
        assert required_heading in md
