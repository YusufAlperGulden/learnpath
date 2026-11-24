"""Comprehensive offline & end-to-end recommender evaluation script (RAD v2.0 Section 3.4.4).

Answers Research Questions RQ1, RQ2, and RQ4 plus NFR-05 (< 2.0s end-to-end latency):
- RQ1: Compares Popularity, Content-Based (TF-IDF), Collaborative Filtering, and Hybrid
  (plus Rule-Based prototype reference) on identical prerequisite-gated unseen candidates (K = 5)
  with paired student-level bootstrap 95% confidence intervals.
- RQ2: Reports Warm-Start (>= 2 prior ratings) vs. Cold-Start (< 2 prior ratings) slices and
  explicit cold-start / format-relaxation fallback rates.
- RQ4: Reports Catalog Coverage, Intra-List Diversity@5 (topic-tag, topic+format, and TF-IDF
  cosine dissimilarity), and server p50 / p95 response latency.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.enums import AnswerOption, TestType, UserRole
from app.core.logging_config import configure_logging, get_logger
from app.core.security import create_access_token
from app.main import app
from app.models.catalog import Topic
from app.models.user import User
from app.services.recommenders import (
    CandidateResource,
    CollaborativeFilteringRecommender,
    ContentBasedRecommender,
    HybridRecommender,
    InteractionRecord,
    PopularityRecommender,
    RankedCandidate,
    RuleBasedRecommender,
    StudentRecommendationContext,
)
from experiments.metrics import (
    BOOTSTRAP_SEED,
    DEFAULT_BOOTSTRAP_SAMPLES,
    BootstrapEstimate,
    PairedBootstrapDelta,
    bootstrap_mean_ci,
    collect_environment_metadata,
    compute_topic_format_diversity,
    compute_topic_tag_diversity,
    ndcg_at_k,
    open_experiment_session,
    paired_bootstrap_delta,
    percentile,
    precision_at_k,
    recall_at_k,
)
from experiments.split_dataset import (
    ARTIFACTS_DIR,
    RELEVANCE_RATING_THRESHOLD,
    build_offline_student_context,
    get_eligible_unseen_candidates,
    load_active_catalog_candidates,
    load_or_seed_interactions,
    select_hybrid_weight_on_validation,
    split_interactions_chronologically,
)
from scripts.seed_interactions import COHORT_RANDOM_SEED

logger = get_logger("experiments.evaluate")

EVALUATION_K = 5
COLD_START_MAX_PRIOR_RATINGS = 1


@dataclass(frozen=True, slots=True)
class PreparedStudentQuery:
    student_id: UUID
    email: str
    is_cold_start: bool
    prior_rating_count: int
    context: StudentRecommendationContext
    eligible_candidates: list[CandidateResource]
    relevant_test_ids: set[UUID]


@dataclass(frozen=True, slots=True)
class SliceMetrics:
    slice_name: str
    total_queries: int
    evaluated_relevant_queries: int
    excluded_zero_relevant_queries: int
    precision_at_5: BootstrapEstimate
    precision_at_5_all_queries: float
    recall_at_5: BootstrapEstimate
    ndcg_at_5: BootstrapEstimate
    cold_start_fallback_rate: float
    format_relaxation_rate: float


@dataclass(frozen=True, slots=True)
class ModelEvaluationSummary:
    model_key: str
    display_name: str
    is_primary_rad_benchmark: bool
    overall: SliceMetrics
    warm_start: SliceMetrics
    cold_start: SliceMetrics
    catalog_coverage_eligible: float
    catalog_coverage_all_active: float
    unique_recommended_resources: int
    topic_tag_diversity_at_5: BootstrapEstimate
    topic_format_diversity_at_5: BootstrapEstimate
    tfidf_cosine_diversity_at_5: BootstrapEstimate
    ranking_latency_p50_ms: float
    ranking_latency_p95_ms: float
    ranking_latency_mean_ms: float


@dataclass(frozen=True, slots=True)
class EndToEndLatencyReport:
    n_iterations: int
    warm_cache: bool
    assessment_plus_recommendation_p50_ms: float
    assessment_plus_recommendation_p95_ms: float
    assessment_plus_recommendation_max_ms: float
    recommendation_get_only_p50_ms: float
    recommendation_get_only_p95_ms: float
    nfr05_threshold_ms: float
    passes_nfr05: bool


@dataclass(frozen=True, slots=True)
class DatasetProvenance:
    data_origin: str
    simulation_seed: int
    active_topics: int
    active_catalog_resources: int
    eligible_catalog_union_size: int
    total_students_with_feedback: int
    evaluated_test_students: int
    warm_start_test_students: int
    cold_start_test_students: int
    raw_feedback_rows: int
    deduplicated_feedback_rows: int
    duplicates_removed: int
    user_item_matrix_density: float
    train_interactions: int
    validation_interactions: int
    test_interactions: int
    train_end_at: str | None
    validation_end_at: str | None
    selected_hybrid_cbf_weight: float
    selected_hybrid_cf_weight: float
    cf_min_common_items: int
    cf_min_neighbors: int


@dataclass(frozen=True, slots=True)
class FullEvaluationReport:
    generated_at: str
    k: int
    relevance_definition: str
    bootstrap_samples: int
    bootstrap_seed: int
    environment: dict[str, str]
    provenance: DatasetProvenance
    models: list[ModelEvaluationSummary]
    rq1_paired_bootstrap_vs_hybrid: list[PairedBootstrapDelta]
    end_to_end_latency: EndToEndLatencyReport
    study_limitations: list[str]


@dataclass(slots=True)
class _PerStudentModelRun:
    student_id: UUID
    is_cold_start: bool
    has_eligible_relevant: bool
    precision: float
    recall: float
    ndcg: float
    topic_div: float
    topic_fmt_div: float
    tfidf_div: float
    cold_start_fallback: bool
    format_relaxed: bool
    recommended_ids: list[UUID]
    latency_ms: float


def _build_slice_metrics(
    slice_name: str,
    runs: Sequence[_PerStudentModelRun],
    *,
    n_boot: int,
    seed: int,
) -> SliceMetrics:
    total_q = len(runs)
    rel_runs = [r for r in runs if r.has_eligible_relevant]
    excluded_q = total_q - len(rel_runs)

    prec_rel = [r.precision for r in rel_runs]
    rec_rel = [r.recall for r in rel_runs]
    ndcg_rel = [r.ndcg for r in rel_runs]
    prec_all = round(sum(r.precision for r in runs) / total_q, 6) if total_q > 0 else 0.0
    cs_fb_rate = (
        round(sum(1 for r in runs if r.cold_start_fallback) / total_q, 6) if total_q > 0 else 0.0
    )
    fmt_fb_rate = (
        round(sum(1 for r in runs if r.format_relaxed) / total_q, 6) if total_q > 0 else 0.0
    )

    return SliceMetrics(
        slice_name=slice_name,
        total_queries=total_q,
        evaluated_relevant_queries=len(rel_runs),
        excluded_zero_relevant_queries=excluded_q,
        precision_at_5=bootstrap_mean_ci(prec_rel, n_boot=n_boot, seed=seed),
        precision_at_5_all_queries=prec_all,
        recall_at_5=bootstrap_mean_ci(rec_rel, n_boot=n_boot, seed=seed + 11),
        ndcg_at_5=bootstrap_mean_ci(ndcg_rel, n_boot=n_boot, seed=seed + 23),
        cold_start_fallback_rate=cs_fb_rate,
        format_relaxation_rate=fmt_fb_rate,
    )


def prepare_test_queries(
    db: Session,
    *,
    prior_interactions: Sequence[InteractionRecord],
    test_interactions: Sequence[InteractionRecord],
    catalog: Sequence[CandidateResource],
) -> list[PreparedStudentQuery]:
    """Builds leak-free student queries at the Test split boundary."""
    prior_by_user: dict[UUID, list[InteractionRecord]] = defaultdict(list)
    for rec in prior_interactions:
        prior_by_user[rec.student_id].append(rec)

    test_by_user: dict[UUID, list[InteractionRecord]] = defaultdict(list)
    for rec in test_interactions:
        test_by_user[rec.student_id].append(rec)

    test_user_ids = sorted(test_by_user.keys(), key=str)
    users_by_id = {
        u.user_id: u
        for u in db.scalars(
            select(User)
            .options(selectinload(User.profile))
            .where(User.user_id.in_(test_user_ids))
        ).all()
    }

    queries: list[PreparedStudentQuery] = []
    for uid in test_user_ids:
        user = users_by_id.get(uid)
        if user is None:
            continue
        hist = prior_by_user.get(uid, [])
        seen_ids = {r.resource_id for r in hist}
        ctx = build_offline_student_context(db, user, hist)
        eligible = get_eligible_unseen_candidates(
            db,
            student_id=uid,
            preferred_language=ctx.preferred_language,
            seen_resource_ids=seen_ids,
            catalog=catalog,
        )
        eligible_ids = {c.resource_id for c in eligible}
        rel_ids = {
            r.resource_id
            for r in test_by_user[uid]
            if r.rating >= RELEVANCE_RATING_THRESHOLD and r.resource_id in eligible_ids
        }
        queries.append(
            PreparedStudentQuery(
                student_id=uid,
                email=user.email,
                is_cold_start=len(hist) <= COLD_START_MAX_PRIOR_RATINGS,
                prior_rating_count=len(hist),
                context=ctx,
                eligible_candidates=eligible,
                relevant_test_ids=rel_ids,
            )
        )
    return queries


def benchmark_end_to_end_http_latency(
    db: Session,
    *,
    n_iterations: int = 20,
) -> EndToEndLatencyReport:
    """Measures full HTTP assessment submission + hybrid recommendation turnaround (NFR-05 < 2.0s)."""
    student = db.scalar(select(User).where(User.email == "student@learnpath.local"))
    if student is None:
        student = db.scalar(select(User).where(User.role == UserRole.STUDENT.value))
    assert student is not None, "Expected at least one seeded student account."

    headers = {
        "Authorization": f"Bearer {create_access_token(user_id=student.user_id, role=UserRole.STUDENT)}"
    }

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    e2e_samples_ms: list[float] = []
    rec_only_samples_ms: list[float] = []

    try:
        with TestClient(app) as client:
            # Warm up in-memory TF-IDF cache once so reported timings reflect warm-cache state
            warmup = client.get(
                "/api/v1/recommendations?strategy=hybrid&limit=5",
                headers=headers,
            )
            assert warmup.status_code == 200

            option_cycle = (
                AnswerOption.A.value,
                AnswerOption.B.value,
                AnswerOption.C.value,
                AnswerOption.D.value,
            )

            for i in range(n_iterations):
                q_res = client.get(
                    f"/api/v1/assessments/questions?test_type={TestType.DIAGNOSTIC.value}",
                    headers=headers,
                )
                assert q_res.status_code == 200
                q_payload = q_res.json()
                answers = [
                    {
                        "question_id": q["question_id"],
                        "selected_option": option_cycle[(idx + i) % 4],
                    }
                    for idx, q in enumerate(q_payload["questions"])
                ]

                t_start = time.perf_counter()
                sub_res = client.post(
                    "/api/v1/assessments/submit",
                    headers=headers,
                    json={
                        "attempt_id": q_payload["attempt_id"],
                        "test_session_token": q_payload["test_session_token"],
                        "answers": answers,
                    },
                )
                assert sub_res.status_code == 200

                t_rec_start = time.perf_counter()
                rec_res = client.get(
                    "/api/v1/recommendations?strategy=hybrid&limit=5",
                    headers=headers,
                )
                t_end = time.perf_counter()
                assert rec_res.status_code == 200

                e2e_samples_ms.append((t_end - t_start) * 1000.0)
                rec_only_samples_ms.append((t_end - t_rec_start) * 1000.0)
    finally:
        app.dependency_overrides.pop(get_db, None)

    e2e_p50 = percentile(e2e_samples_ms, 50.0)
    e2e_p95 = percentile(e2e_samples_ms, 95.0)
    e2e_max = round(max(e2e_samples_ms), 4) if e2e_samples_ms else 0.0
    rec_p50 = percentile(rec_only_samples_ms, 50.0)
    rec_p95 = percentile(rec_only_samples_ms, 95.0)

    return EndToEndLatencyReport(
        n_iterations=n_iterations,
        warm_cache=True,
        assessment_plus_recommendation_p50_ms=e2e_p50,
        assessment_plus_recommendation_p95_ms=e2e_p95,
        assessment_plus_recommendation_max_ms=e2e_max,
        recommendation_get_only_p50_ms=rec_p50,
        recommendation_get_only_p95_ms=rec_p95,
        nfr05_threshold_ms=2000.0,
        passes_nfr05=e2e_p95 < 2000.0 and e2e_max < 2000.0,
    )


def run_model_evaluation(
    db: Session,
    *,
    db_backend: str = "postgresql",
    k: int = EVALUATION_K,
    n_boot: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
    latency_iterations: int = 20,
    write_artifacts: bool = True,
) -> FullEvaluationReport:
    """Executes leak-free benchmark comparison across Popularity, CBF, CF, Hybrid, and Rule-Based."""
    interactions = load_or_seed_interactions(db)
    split = split_interactions_chronologically(interactions)
    catalog = load_active_catalog_candidates(db)

    # Step 1: Select Hybrid CBF weight strictly on Validation (fitted on Train only)
    cbf_for_val = ContentBasedRecommender().fit(catalog)
    selected_cbf_weight, _grid = select_hybrid_weight_on_validation(
        db,
        split,
        k=k,
        cbf_recommender=cbf_for_val,
    )

    # Step 2: Fit models for Test evaluation using ONLY pre-test historical interactions (Train + Val)
    pre_test_history = [*split.train, *split.validation]
    pop_model = PopularityRecommender().fit(pre_test_history)
    cbf_model = ContentBasedRecommender().fit(catalog)
    cf_model = CollaborativeFilteringRecommender().fit(pre_test_history)
    hybrid_model = HybridRecommender(
        cbf=cbf_model,
        cf=cf_model,
        cbf_weight=selected_cbf_weight,
    )
    rule_model = RuleBasedRecommender()

    queries = prepare_test_queries(
        db,
        prior_interactions=pre_test_history,
        test_interactions=split.test,
        catalog=catalog,
    )

    eligible_union_ids: set[UUID] = set()
    for q in queries:
        eligible_union_ids.update(c.resource_id for c in q.eligible_candidates)

    model_specs: tuple[tuple[str, str, bool], ...] = (
        ("popularity", "Popularity Baseline", True),
        ("cbf", "Content-Based Filtering (TF-IDF)", True),
        ("cf", "Collaborative Filtering (User-KNN)", True),
        ("hybrid", f"Weighted Hybrid (w_cbf={selected_cbf_weight:.2f})", True),
        ("rule_based", "Rule-Based Prototype (Phase 3 Reference)", False),
    )

    runs_by_model: dict[str, list[_PerStudentModelRun]] = {}
    summaries: list[ModelEvaluationSummary] = []

    for model_key, display_name, is_primary in model_specs:
        per_user_runs: list[_PerStudentModelRun] = []
        recommended_union: set[UUID] = set()

        for q in queries:
            t0 = time.perf_counter()
            cold_fallback = False
            ranked: list[RankedCandidate]

            if model_key == "popularity":
                ranked = pop_model.rank(q.eligible_candidates, q.context, limit=k)
            elif model_key == "cbf":
                ranked = cbf_model.rank(q.eligible_candidates, q.context, limit=k)
            elif model_key == "cf":
                cold_fallback = not cf_model.has_collaborative_support(
                    q.eligible_candidates, q.context
                )
                ranked = cf_model.rank(q.eligible_candidates, q.context, limit=k)
            elif model_key == "hybrid":
                outcome = hybrid_model.rank_with_diagnostics(
                    q.eligible_candidates, q.context, limit=k
                )
                ranked = outcome.items
                cold_fallback = outcome.cold_start_fallback
            else:
                ranked = rule_model.rank(q.eligible_candidates, q.context, limit=k)

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            rec_ids = [item.candidate.resource_id for item in ranked]
            rec_cands = [item.candidate for item in ranked]
            recommended_union.update(rec_ids)

            has_rel = len(q.relevant_test_ids) > 0
            prec = precision_at_k(rec_ids, q.relevant_test_ids, k=k)
            rec = recall_at_k(rec_ids, q.relevant_test_ids, k=k) if has_rel else 0.0
            ndcg = ndcg_at_k(rec_ids, q.relevant_test_ids, k=k) if has_rel else 0.0

            topic_div = compute_topic_tag_diversity(rec_cands)
            topic_fmt_div = compute_topic_format_diversity(rec_cands)
            tfidf_div = cbf_model.compute_intra_list_diversity(rec_ids)
            fmt_relaxed = any(item.format_fallback_used for item in ranked)

            per_user_runs.append(
                _PerStudentModelRun(
                    student_id=q.student_id,
                    is_cold_start=q.is_cold_start,
                    has_eligible_relevant=has_rel,
                    precision=prec,
                    recall=rec,
                    ndcg=ndcg,
                    topic_div=topic_div,
                    topic_fmt_div=topic_fmt_div,
                    tfidf_div=tfidf_div,
                    cold_start_fallback=cold_fallback,
                    format_relaxed=fmt_relaxed,
                    recommended_ids=rec_ids,
                    latency_ms=elapsed_ms,
                )
            )

        runs_by_model[model_key] = per_user_runs
        warm_runs = [r for r in per_user_runs if not r.is_cold_start]
        cold_runs = [r for r in per_user_runs if r.is_cold_start]
        latencies = [r.latency_ms for r in per_user_runs]

        cov_eligible = (
            round(len(recommended_union) / len(eligible_union_ids), 6)
            if eligible_union_ids
            else 0.0
        )
        cov_all = round(len(recommended_union) / len(catalog), 6) if catalog else 0.0

        summaries.append(
            ModelEvaluationSummary(
                model_key=model_key,
                display_name=display_name,
                is_primary_rad_benchmark=is_primary,
                overall=_build_slice_metrics("overall", per_user_runs, n_boot=n_boot, seed=seed),
                warm_start=_build_slice_metrics("warm_start", warm_runs, n_boot=n_boot, seed=seed),
                cold_start=_build_slice_metrics("cold_start", cold_runs, n_boot=n_boot, seed=seed),
                catalog_coverage_eligible=cov_eligible,
                catalog_coverage_all_active=cov_all,
                unique_recommended_resources=len(recommended_union),
                topic_tag_diversity_at_5=bootstrap_mean_ci(
                    [r.topic_div for r in per_user_runs], n_boot=n_boot, seed=seed + 31
                ),
                topic_format_diversity_at_5=bootstrap_mean_ci(
                    [r.topic_fmt_div for r in per_user_runs], n_boot=n_boot, seed=seed + 41
                ),
                tfidf_cosine_diversity_at_5=bootstrap_mean_ci(
                    [r.tfidf_div for r in per_user_runs], n_boot=n_boot, seed=seed + 53
                ),
                ranking_latency_p50_ms=percentile(latencies, 50.0),
                ranking_latency_p95_ms=percentile(latencies, 95.0),
                ranking_latency_mean_ms=(
                    round(sum(latencies) / len(latencies), 4) if latencies else 0.0
                ),
            )
        )

    # Step 3: Paired student-level bootstrap comparisons for RQ1 (Hybrid vs. each baseline)
    hybrid_rel = [r for r in runs_by_model["hybrid"] if r.has_eligible_relevant]
    rq1_deltas: list[PairedBootstrapDelta] = []
    for base_key, base_label in (
        ("popularity", "Popularity"),
        ("cbf", "CBF"),
        ("cf", "CF"),
    ):
        base_rel = [r for r in runs_by_model[base_key] if r.has_eligible_relevant]
        label = f"Hybrid - {base_label}"
        rq1_deltas.extend(
            [
                paired_bootstrap_delta(
                    [r.precision for r in hybrid_rel],
                    [r.precision for r in base_rel],
                    comparison=label,
                    metric="Precision@5",
                    n_boot=n_boot,
                    seed=seed + 101,
                ),
                paired_bootstrap_delta(
                    [r.recall for r in hybrid_rel],
                    [r.recall for r in base_rel],
                    comparison=label,
                    metric="Recall@5",
                    n_boot=n_boot,
                    seed=seed + 103,
                ),
                paired_bootstrap_delta(
                    [r.ndcg for r in hybrid_rel],
                    [r.ndcg for r in base_rel],
                    comparison=label,
                    metric="NDCG@5",
                    n_boot=n_boot,
                    seed=seed + 107,
                ),
                paired_bootstrap_delta(
                    [r.tfidf_div for r in runs_by_model["hybrid"]],
                    [r.tfidf_div for r in runs_by_model[base_key]],
                    comparison=label,
                    metric="TFIDF_Diversity@5",
                    n_boot=n_boot,
                    seed=seed + 109,
                ),
            ]
        )

    # Step 4: End-to-end HTTP assessment + recommendation latency verification (NFR-05 < 2.0s)
    e2e_latency = benchmark_end_to_end_http_latency(db, n_iterations=latency_iterations)

    unique_users_with_fb = len({rec.student_id for rec in split.train + split.validation + split.test})
    n_topics = len(db.scalars(select(Topic.topic_id)).all())
    denom_cells = unique_users_with_fb * len(catalog)
    density = round(split.deduplicated_count / denom_cells, 6) if denom_cells > 0 else 0.0

    provenance = DatasetProvenance(
        data_origin="documented_cohort_simulation",
        simulation_seed=COHORT_RANDOM_SEED,
        active_topics=n_topics,
        active_catalog_resources=len(catalog),
        eligible_catalog_union_size=len(eligible_union_ids),
        total_students_with_feedback=unique_users_with_fb,
        evaluated_test_students=len(queries),
        warm_start_test_students=sum(1 for q in queries if not q.is_cold_start),
        cold_start_test_students=sum(1 for q in queries if q.is_cold_start),
        raw_feedback_rows=split.raw_count,
        deduplicated_feedback_rows=split.deduplicated_count,
        duplicates_removed=split.duplicates_removed,
        user_item_matrix_density=density,
        train_interactions=len(split.train),
        validation_interactions=len(split.validation),
        test_interactions=len(split.test),
        train_end_at=split.train_end_at,
        validation_end_at=split.validation_end_at,
        selected_hybrid_cbf_weight=selected_cbf_weight,
        selected_hybrid_cf_weight=round(1.0 - selected_cbf_weight, 2),
        cf_min_common_items=cf_model.min_common_items,
        cf_min_neighbors=cf_model.min_neighbors,
    )

    limitations = [
        (
            "Interactions originate from a documented deterministic cohort simulation (seed=4912026) "
            "over a curated 54-resource Python catalog; simulated ratings reflect modelled topic-gap, "
            "format, difficulty, and peer-cluster preferences and therefore do not establish real-world "
            "pedagogical learning gains."
        ),
        (
            "A compact domain catalog (54 total resources; 42 English, 12 Turkish across 6 DAG topics) "
            "bounds maximum achievable diversity and may elevate top-5 hit rates relative to large "
            "open-web repositories."
        ),
        (
            "Cold-start slice uncertainty (n=8 cold-start students) is reported with both paired "
            "bootstrap intervals and exact descriptive slice counts per RAD Section 3.4.4."
        ),
        (
            "Offline ranking metrics (Precision@5, Recall@5, NDCG@5) measure alignment with held-out "
            "high-utility resource feedback (rating >= 4); a consent-based human learner study with "
            "pre/post-testing is required to claim improved learning outcomes."
        ),
    ]

    report = FullEvaluationReport(
        generated_at=datetime.now(UTC).isoformat(),
        k=k,
        relevance_definition="explicit_5_point_rating >= 4",
        bootstrap_samples=n_boot,
        bootstrap_seed=seed,
        environment=collect_environment_metadata(db_backend),
        provenance=provenance,
        models=summaries,
        rq1_paired_bootstrap_vs_hybrid=rq1_deltas,
        end_to_end_latency=e2e_latency,
        study_limitations=limitations,
    )

    if write_artifacts:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "model_evaluation.json").write_text(
            json.dumps(asdict(report), indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Saved model evaluation artifact to %s (evaluated_students=%d, e2e_p95_ms=%.2f)",
            ARTIFACTS_DIR / "model_evaluation.json",
            provenance.evaluated_test_students,
            e2e_latency.assessment_plus_recommendation_p95_ms,
        )

    return report


def format_evaluation_console_table(report: FullEvaluationReport) -> str:
    """Formats a concise Markdown table for terminal inspection."""
    lines = [
        "### RQ1 / RQ2 / RQ4 Model Comparison (Test Split, K = 5)",
        "",
        "| Model | Precision@5 (95% CI) | Recall@5 (95% CI) | NDCG@5 (95% CI) | Warm NDCG@5 | Cold NDCG@5 | Eligible Cov. | TF-IDF Div@5 | Topic Div@5 | Cold Fallback | p95 (ms) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for m in report.models:
        p = m.overall.precision_at_5
        r = m.overall.recall_at_5
        n = m.overall.ndcg_at_5
        lines.append(
            f"| {m.display_name} | "
            f"{p.mean:.3f} [{p.ci_95_low:.3f}, {p.ci_95_high:.3f}] | "
            f"{r.mean:.3f} [{r.ci_95_low:.3f}, {r.ci_95_high:.3f}] | "
            f"{n.mean:.3f} [{n.ci_95_low:.3f}, {n.ci_95_high:.3f}] | "
            f"{m.warm_start.ndcg_at_5.mean:.3f} | "
            f"{m.cold_start.ndcg_at_5.mean:.3f} | "
            f"{m.catalog_coverage_eligible:.1%} | "
            f"{m.tfidf_cosine_diversity_at_5.mean:.3f} | "
            f"{m.topic_tag_diversity_at_5.mean:.3f} | "
            f"{m.overall.cold_start_fallback_rate:.1%} | "
            f"{m.ranking_latency_p95_ms:.2f} |"
        )
    e2e = report.end_to_end_latency
    lines.extend(
        [
            "",
            (
                f"- **End-to-End Assessment Submit + Hybrid Recommendation Latency (`NFR-05 < 2000 ms`)**: "
                f"`p50 = {e2e.assessment_plus_recommendation_p50_ms:.2f} ms`, "
                f"`p95 = {e2e.assessment_plus_recommendation_p95_ms:.2f} ms`, "
                f"`max = {e2e.assessment_plus_recommendation_max_ms:.2f} ms` "
                f"-> **{'PASS' if e2e.passes_nfr05 else 'FAIL'}**"
            ),
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate LearnPath recommendation models (RQ1, RQ2, RQ4, and NFR-05)."
    )
    parser.add_argument(
        "--db",
        choices=("auto", "postgres", "sqlite"),
        default="auto",
        help="Database connection mode (defaults to 'auto').",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=DEFAULT_BOOTSTRAP_SAMPLES,
        help="Number of paired student-level bootstrap resamples (default: 1000).",
    )
    args = parser.parse_args()

    configure_logging()
    with open_experiment_session(args.db) as (db, db_backend):
        report = run_model_evaluation(
            db,
            db_backend=db_backend,
            n_boot=args.bootstrap_samples,
            write_artifacts=True,
        )
        print(format_evaluation_console_table(report))


if __name__ == "__main__":
    main()
