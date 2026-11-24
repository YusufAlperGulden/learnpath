"""Feature & collaborative-evidence ablation study for RQ3 (RAD v2.0 Section 3.4.4).

Compares four controlled conditions on identical chronological splits and fixed prerequisite-gated
candidate pools, tuning `cbf_weight` exclusively on each condition's own validation data:
1. `full_hybrid`: Full Hybrid (Profile Preferences + Assessment Scores + Collaborative Filtering)
2. `no_profile_preferences`: Removes preferred formats, experience level, and learning-goal query
   expansion from CBF/Hybrid while keeping DAG prerequisite & language constraints fixed.
3. `no_assessment_features`: Removes topic assessment scores and mastery urgency/difficulty
   calibration from CBF/Hybrid while keeping DAG prerequisite access gates fixed.
4. `no_collaborative_evidence`: Content-only (`cbf_weight = 1.0`), removing CF neighbor evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging_config import configure_logging, get_logger
from app.services.recommenders import (
    CollaborativeFilteringRecommender,
    ContentBasedRecommender,
    HybridRecommender,
)
from experiments.evaluate_models import (
    EVALUATION_K,
    FullEvaluationReport,
    SliceMetrics,
    _build_slice_metrics,
    _PerStudentModelRun,
    prepare_test_queries,
    run_model_evaluation,
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
    precision_at_k,
    recall_at_k,
)
from experiments.split_dataset import (
    ARTIFACTS_DIR,
    load_active_catalog_candidates,
    load_or_seed_interactions,
    select_hybrid_weight_on_validation,
    split_interactions_chronologically,
)

logger = get_logger("experiments.ablation")

DEFAULT_MARKDOWN_REPORT_PATH = Path(__file__).resolve().parent / "EVALUATION_REPORT.md"


@dataclass(frozen=True, slots=True)
class AblationConditionSummary:
    condition_key: str
    display_name: str
    use_profile_features: bool
    use_assessment_features: bool
    use_collaborative_evidence: bool
    selected_cbf_weight: float
    selected_cf_weight: float
    validation_ndcg_at_5: float
    overall: SliceMetrics
    warm_start: SliceMetrics
    cold_start: SliceMetrics
    catalog_coverage_eligible: float
    topic_tag_diversity_at_5: BootstrapEstimate
    tfidf_cosine_diversity_at_5: BootstrapEstimate


@dataclass(frozen=True, slots=True)
class AblationStudyReport:
    generated_at: str
    k: int
    bootstrap_samples: int
    bootstrap_seed: int
    environment: dict[str, str]
    conditions: list[AblationConditionSummary]
    rq3_paired_deltas_vs_full_hybrid: list[PairedBootstrapDelta]


def run_ablation_study(
    db: Session,
    *,
    db_backend: str = "postgresql",
    k: int = EVALUATION_K,
    n_boot: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
    write_artifacts: bool = True,
) -> AblationStudyReport:
    """Executes RQ3 ablation study with condition-specific validation tuning and paired bootstrap."""
    interactions = load_or_seed_interactions(db)
    split = split_interactions_chronologically(interactions)
    catalog = load_active_catalog_candidates(db)

    pre_test_history = [*split.train, *split.validation]
    cf_test = CollaborativeFilteringRecommender().fit(pre_test_history)
    reference_cbf = ContentBasedRecommender().fit(catalog)

    queries = prepare_test_queries(
        db,
        prior_interactions=pre_test_history,
        test_interactions=split.test,
        catalog=catalog,
    )
    eligible_union_ids: set[UUID] = set()
    for q in queries:
        eligible_union_ids.update(c.resource_id for c in q.eligible_candidates)

    condition_defs: tuple[tuple[str, str, bool, bool, bool], ...] = (
        ("full_hybrid", "Full Hybrid (Profile + Assessment + CF)", True, True, True),
        ("no_profile_preferences", "Hybrid w/o Profile Preferences (-Profile)", False, True, True),
        (
            "no_assessment_features",
            "Hybrid w/o Assessment Scores (-Assessment)",
            True,
            False,
            True,
        ),
        (
            "no_collaborative_evidence",
            "Hybrid w/o Collaborative Evidence (-CF / CBF-Only)",
            True,
            True,
            False,
        ),
    )

    runs_by_condition: dict[str, list[_PerStudentModelRun]] = {}
    condition_summaries: list[AblationConditionSummary] = []

    for cond_key, display_name, use_prof, use_assess, use_cf in condition_defs:
        cbf_cond = ContentBasedRecommender(
            use_profile_features=use_prof,
            use_assessment_features=use_assess,
        ).fit(catalog)

        if use_cf:
            best_w, val_grid = select_hybrid_weight_on_validation(
                db,
                split,
                k=k,
                cbf_recommender=cbf_cond,
            )
            val_ndcg = max((pt.validation_ndcg_at_5 for pt in val_grid), default=0.0)
        else:
            # Content-only ablation fixes cbf_weight = 1.0 (zero collaborative contribution)
            _, val_grid = select_hybrid_weight_on_validation(
                db,
                split,
                k=k,
                weight_grid=(1.0,),
                cbf_recommender=cbf_cond,
            )
            best_w = 1.0
            val_ndcg = val_grid[0].validation_ndcg_at_5 if val_grid else 0.0

        per_user_runs: list[_PerStudentModelRun] = []
        rec_union: set[UUID] = set()

        for q in queries:
            if use_cf:
                model = HybridRecommender(cbf=cbf_cond, cf=cf_test, cbf_weight=best_w)
                outcome = model.rank_with_diagnostics(
                    q.eligible_candidates, q.context, limit=k
                )
                ranked = outcome.items
                cold_fb = outcome.cold_start_fallback
            else:
                ranked = cbf_cond.rank(q.eligible_candidates, q.context, limit=k)
                cold_fb = False

            rec_ids = [item.candidate.resource_id for item in ranked]
            rec_cands = [item.candidate for item in ranked]
            rec_union.update(rec_ids)

            has_rel = len(q.relevant_test_ids) > 0
            prec = precision_at_k(rec_ids, q.relevant_test_ids, k=k)
            rec = recall_at_k(rec_ids, q.relevant_test_ids, k=k) if has_rel else 0.0
            ndcg = ndcg_at_k(rec_ids, q.relevant_test_ids, k=k) if has_rel else 0.0

            per_user_runs.append(
                _PerStudentModelRun(
                    student_id=q.student_id,
                    is_cold_start=q.is_cold_start,
                    has_eligible_relevant=has_rel,
                    precision=prec,
                    recall=rec,
                    ndcg=ndcg,
                    topic_div=compute_topic_tag_diversity(rec_cands),
                    topic_fmt_div=compute_topic_format_diversity(rec_cands),
                    tfidf_div=reference_cbf.compute_intra_list_diversity(rec_ids),
                    cold_start_fallback=cold_fb,
                    format_relaxed=any(it.format_fallback_used for it in ranked),
                    recommended_ids=rec_ids,
                    latency_ms=0.0,
                )
            )

        runs_by_condition[cond_key] = per_user_runs
        warm_runs = [r for r in per_user_runs if not r.is_cold_start]
        cold_runs = [r for r in per_user_runs if r.is_cold_start]
        cov_elig = (
            round(len(rec_union) / len(eligible_union_ids), 6) if eligible_union_ids else 0.0
        )

        condition_summaries.append(
            AblationConditionSummary(
                condition_key=cond_key,
                display_name=display_name,
                use_profile_features=use_prof,
                use_assessment_features=use_assess,
                use_collaborative_evidence=use_cf,
                selected_cbf_weight=best_w,
                selected_cf_weight=round(1.0 - best_w, 2),
                validation_ndcg_at_5=val_ndcg,
                overall=_build_slice_metrics("overall", per_user_runs, n_boot=n_boot, seed=seed),
                warm_start=_build_slice_metrics("warm_start", warm_runs, n_boot=n_boot, seed=seed),
                cold_start=_build_slice_metrics("cold_start", cold_runs, n_boot=n_boot, seed=seed),
                catalog_coverage_eligible=cov_elig,
                topic_tag_diversity_at_5=bootstrap_mean_ci(
                    [r.topic_div for r in per_user_runs], n_boot=n_boot, seed=seed + 61
                ),
                tfidf_cosine_diversity_at_5=bootstrap_mean_ci(
                    [r.tfidf_div for r in per_user_runs], n_boot=n_boot, seed=seed + 71
                ),
            )
        )

    # Paired bootstrap differences: Delta = Ablated - Full Hybrid (negative => removing hurts)
    full_rel = [r for r in runs_by_condition["full_hybrid"] if r.has_eligible_relevant]
    rq3_deltas: list[PairedBootstrapDelta] = []
    for abl_key, short_name in (
        ("no_profile_preferences", "(-Profile) - Full Hybrid"),
        ("no_assessment_features", "(-Assessment) - Full Hybrid"),
        ("no_collaborative_evidence", "(-CF / CBF-Only) - Full Hybrid"),
    ):
        abl_rel = [r for r in runs_by_condition[abl_key] if r.has_eligible_relevant]
        rq3_deltas.extend(
            [
                paired_bootstrap_delta(
                    [r.precision for r in abl_rel],
                    [r.precision for r in full_rel],
                    comparison=short_name,
                    metric="Precision@5",
                    n_boot=n_boot,
                    seed=seed + 211,
                ),
                paired_bootstrap_delta(
                    [r.recall for r in abl_rel],
                    [r.recall for r in full_rel],
                    comparison=short_name,
                    metric="Recall@5",
                    n_boot=n_boot,
                    seed=seed + 223,
                ),
                paired_bootstrap_delta(
                    [r.ndcg for r in abl_rel],
                    [r.ndcg for r in full_rel],
                    comparison=short_name,
                    metric="NDCG@5",
                    n_boot=n_boot,
                    seed=seed + 227,
                ),
            ]
        )

    report = AblationStudyReport(
        generated_at=datetime.now(UTC).isoformat(),
        k=k,
        bootstrap_samples=n_boot,
        bootstrap_seed=seed,
        environment=collect_environment_metadata(db_backend),
        conditions=condition_summaries,
        rq3_paired_deltas_vs_full_hybrid=rq3_deltas,
    )

    if write_artifacts:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "ablation_results.json").write_text(
            json.dumps(asdict(report), indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Saved ablation study artifact to %s",
            ARTIFACTS_DIR / "ablation_results.json",
        )

    return report


def render_academic_evaluation_markdown(
    eval_report: FullEvaluationReport,
    ablation_report: AblationStudyReport,
) -> str:
    """Renders the complete COME 491 academic evaluation report (RQ1–RQ4 + NFR-05 + Limitations)."""
    prov = eval_report.provenance
    env = eval_report.environment
    e2e = eval_report.end_to_end_latency

    lines: list[str] = [
        "# LearnPath — Experimental Evaluation & Ablation Report (COME 491, RAD v2.0)",
        "",
        (
            "> **Methodological Scope Notice (RAD Section 3.4.4)**: All offline metrics below are "
            "computed on a documented deterministic cohort simulation (`data_origin = "
            f"{prov.data_origin}`, `seed = {prov.simulation_seed}`) over the curated 54-resource "
            "Python fundamentals catalog. Offline ranking metrics evaluate alignment with held-out "
            "high-utility student ratings (`rating >= 4`); they do **not** establish real-world "
            "pedagogical learning gains without a future consent-based human study."
        ),
        "",
        "## 1. Dataset Provenance, Split Integrity & Environment",
        "",
        "| Property | Recorded Value |",
        "| :--- | :--- |",
        f"| Data Origin | `{prov.data_origin}` (`seed = {prov.simulation_seed}`) |",
        f"| Active Curriculum Topics / Resources | `{prov.active_topics}` DAG topics / `{prov.active_catalog_resources}` active resources (`{prov.eligible_catalog_union_size}` in evaluated English unlocked union) |",
        f"| Total Learners / Evaluated Test Learners | `{prov.total_students_with_feedback}` total / `{prov.evaluated_test_students}` test queries (`{prov.warm_start_test_students}` warm-start, `{prov.cold_start_test_students}` cold-start) |",
        f"| Raw / Deduplicated Feedback Rows | `{prov.raw_feedback_rows}` raw / `{prov.deduplicated_feedback_rows}` deduplicated (`{prov.duplicates_removed}` duplicates removed pre-split) |",
        f"| User–Resource Matrix Density | `{prov.user_item_matrix_density:.2%}` (unrated entries treated strictly as unknown, never `0`) |",
        f"| Chronological Split (`70 / 15 / 15`) | Train: `{prov.train_interactions}` (<= `{prov.train_end_at}`) · Validation: `{prov.validation_interactions}` (<= `{prov.validation_end_at}`) · Test: `{prov.test_interactions}` |",
        f"| Validation-Selected Hybrid Weights | `w_cbf = {prov.selected_hybrid_cbf_weight:.2f}`, `w_cf = {prov.selected_hybrid_cf_weight:.2f}` (`min_common_items = {prov.cf_min_common_items}`, `min_neighbors = {prov.cf_min_neighbors}`) |",
        f"| Bootstrap Configuration | Paired student-level percentile bootstrap (`B = {eval_report.bootstrap_samples}`, `seed = {eval_report.bootstrap_seed}`) |",
        f"| Runtime Environment | Python `{env['python_version']}` · scikit-learn `{env['pkg_scikit_learn']}` · NumPy `{env['pkg_numpy']}` · SQLAlchemy `{env['pkg_sqlalchemy']}` · OS `{env['os']}` (`{env['database_backend']}`) |",
        "",
        "---",
        "",
        "## 2. RQ1 — Overall Ranking Quality Across Benchmark Methods (`K = 5`)",
        "",
        "All methods rank the **exact same prerequisite-unlocked, language-matched, unseen candidate pool** per test student, breaking exact score ties deterministically by `resource_id`. Queries with zero held-out eligible relevant items (`rating >= 4`) are excluded from `Recall@5` and `NDCG@5` aggregation (`excluded_zero_relevant_queries` reported explicitly).",
        "",
        "| Method | Evaluated / Total Queries (Excluded 0-Rel) | Precision@5 (95% CI) | Precision@5 (All Queries) | Recall@5 (95% CI) | NDCG@5 (95% CI) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]

    for m in eval_report.models:
        ov = m.overall
        p = ov.precision_at_5
        r = ov.recall_at_5
        n = ov.ndcg_at_5
        tag = "" if m.is_primary_rad_benchmark else " *(Prototype Ref.)*"
        lines.append(
            f"| **{m.display_name}**{tag} | "
            f"`{ov.evaluated_relevant_queries} / {ov.total_queries}` (`{ov.excluded_zero_relevant_queries}`) | "
            f"`{p.mean:.3f}` [`{p.ci_95_low:.3f}`, `{p.ci_95_high:.3f}`] | "
            f"`{ov.precision_at_5_all_queries:.3f}` | "
            f"`{r.mean:.3f}` [`{r.ci_95_low:.3f}`, `{r.ci_95_high:.3f}`] | "
            f"`{n.mean:.3f}` [`{n.ci_95_low:.3f}`, `{n.ci_95_high:.3f}`] |"
        )

    lines.extend(
        [
            "",
            "### Paired Student-Level Bootstrap Comparisons (`RQ1`: `Hybrid - Baseline`)",
            "",
            "| Comparison | Metric | Mean Paired Delta | 95% Bootstrap CI | Two-Sided p-value | Paired Students (`n`) | 95% CI Excludes 0 |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
    )
    for d in eval_report.rq1_paired_bootstrap_vs_hybrid:
        lines.append(
            f"| `{d.comparison}` | `{d.metric}` | `{d.mean_delta:+.3f}` | "
            f"[`{d.ci_95_low:+.3f}`, `{d.ci_95_high:+.3f}`] | `{d.p_value_two_sided:.4f}` | "
            f"`{d.n_paired_students}` | `{'Yes' if d.statistically_significant_95 else 'No'}` |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. RQ2 — Warm-Start vs. Cold-Start Performance & Fallback Honesty",
            "",
            (
                "- **Warm-Start Slice**: Test learners with `>= 2` pre-test historical ratings "
                f"(`n = {prov.warm_start_test_students}`)."
            ),
            (
                "- **Cold-Start Slice**: New/limited-history learners with `0` pre-test historical "
                f"ratings (`n = {prov.cold_start_test_students}`). When collaborative neighbor support "
                "is unavailable, `Hybrid` automatically falls back to pure `CBF` "
                "(`cold_start_fallback_rate = 100%` on cold-start learners) and never fabricates "
                "peer-similarity explanations."
            ),
            "",
            "| Method | Warm-Start NDCG@5 (95% CI) | Warm-Start Precision@5 | Cold-Start NDCG@5 (95% CI) | Cold-Start Precision@5 | Overall Cold-Start Fallback | Format Relaxation Rate |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )
    for m in eval_report.models:
        wn = m.warm_start.ndcg_at_5
        cn = m.cold_start.ndcg_at_5
        lines.append(
            f"| **{m.display_name}** | "
            f"`{wn.mean:.3f}` [`{wn.ci_95_low:.3f}`, `{wn.ci_95_high:.3f}`] | "
            f"`{m.warm_start.precision_at_5.mean:.3f}` | "
            f"`{cn.mean:.3f}` [`{cn.ci_95_low:.3f}`, `{cn.ci_95_high:.3f}`] | "
            f"`{m.cold_start.precision_at_5.mean:.3f}` | "
            f"`{m.overall.cold_start_fallback_rate:.1%}` | "
            f"`{m.overall.format_relaxation_rate:.1%}` |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. RQ3 — Feature & Collaborative-Evidence Ablation Study (`K = 5`)",
            "",
            "Prerequisite DAG access gates and language eligibility remain strictly fixed across all four ablation conditions, and `w_cbf` is re-tuned solely on each condition's own Validation split.",
            "",
            "| Ablation Condition | Tuned `w_cbf` (Val NDCG@5) | Precision@5 (95% CI) | Recall@5 (95% CI) | NDCG@5 (95% CI) | Warm NDCG@5 | Cold NDCG@5 |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )
    for c in ablation_report.conditions:
        p = c.overall.precision_at_5
        r = c.overall.recall_at_5
        n = c.overall.ndcg_at_5
        lines.append(
            f"| **{c.display_name}** | "
            f"`{c.selected_cbf_weight:.2f}` (`{c.validation_ndcg_at_5:.3f}`) | "
            f"`{p.mean:.3f}` [`{p.ci_95_low:.3f}`, `{p.ci_95_high:.3f}`] | "
            f"`{r.mean:.3f}` [`{r.ci_95_low:.3f}`, `{r.ci_95_high:.3f}`] | "
            f"`{n.mean:.3f}` [`{n.ci_95_low:.3f}`, `{n.ci_95_high:.3f}`] | "
            f"`{c.warm_start.ndcg_at_5.mean:.3f}` | "
            f"`{c.cold_start.ndcg_at_5.mean:.3f}` |"
        )

    lines.extend(
        [
            "",
            "### Paired Student-Level Bootstrap Ablation Deltas (`RQ3`: `Ablated - Full Hybrid`)",
            "",
            "| Ablation Contrast | Metric | Mean Paired Delta | 95% Bootstrap CI | Two-Sided p-value | 95% CI Excludes 0 |",
            "| :--- | :--- | :---: | :---: | :---: | :---: |",
        ]
    )
    for d in ablation_report.rq3_paired_deltas_vs_full_hybrid:
        lines.append(
            f"| `{d.comparison}` | `{d.metric}` | `{d.mean_delta:+.3f}` | "
            f"[`{d.ci_95_low:+.3f}`, `{d.ci_95_high:+.3f}`] | `{d.p_value_two_sided:.4f}` | "
            f"`{'Yes' if d.statistically_significant_95 else 'No'}` |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 5. RQ4 & NFR-05 — Catalog Coverage, Intra-List Diversity@5 & Latency",
            "",
            "| Method | Unique Items | Coverage (Eligible Pool) | Coverage (Full 54 Catalog) | Topic-Tag Diversity@5 | Topic+Format Diversity@5 | TF-IDF Cosine Diversity@5 | Rank p50 (ms) | Rank p95 (ms) |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )
    for m in eval_report.models:
        lines.append(
            f"| **{m.display_name}** | "
            f"`{m.unique_recommended_resources}` | "
            f"`{m.catalog_coverage_eligible:.1%}` | "
            f"`{m.catalog_coverage_all_active:.1%}` | "
            f"`{m.topic_tag_diversity_at_5.mean:.3f}` | "
            f"`{m.topic_format_diversity_at_5.mean:.3f}` | "
            f"`{m.tfidf_cosine_diversity_at_5.mean:.3f}` | "
            f"`{m.ranking_latency_p50_ms:.2f}` | "
            f"`{m.ranking_latency_p95_ms:.2f}` |"
        )

    lines.extend(
        [
            "",
            "### End-to-End Server Turnaround Verification (`NFR-05 < 2000 ms`)",
            "",
            f"- **Benchmark Protocol**: `{e2e.n_iterations}` sequential authenticated HTTP iterations (`POST /api/v1/assessments/submit` + `GET /api/v1/recommendations?strategy=hybrid&limit=5`) with warm TF-IDF catalog cache (`warm_cache = {e2e.warm_cache}`).",
            f"- **End-to-End Assessment + Hybrid Recommendation**: `p50 = {e2e.assessment_plus_recommendation_p50_ms:.2f} ms` · `p95 = {e2e.assessment_plus_recommendation_p95_ms:.2f} ms` · `max = {e2e.assessment_plus_recommendation_max_ms:.2f} ms` (Requirement: `< {e2e.nfr05_threshold_ms:.0f} ms` -> **{'PASS' if e2e.passes_nfr05 else 'FAIL'}**).",
            f"- **`GET /api/v1/recommendations?strategy=hybrid` Only**: `p50 = {e2e.recommendation_get_only_p50_ms:.2f} ms` · `p95 = {e2e.recommendation_get_only_p95_ms:.2f} ms`.",
            "",
            "---",
            "",
            "## 6. Research Limitations & Threats to Validity (RAD Section 3.4.4)",
            "",
        ]
    )
    for idx, lim in enumerate(eval_report.study_limitations, start=1):
        lines.append(f"{idx}. {lim}")
    lines.append("")
    return "\n".join(lines)


def format_ablation_console_table(report: AblationStudyReport) -> str:
    lines = [
        "### RQ3 Feature & Collaborative-Evidence Ablation (Test Split, K = 5)",
        "",
        "| Condition | Tuned w_cbf | Precision@5 (95% CI) | Recall@5 (95% CI) | NDCG@5 (95% CI) | Warm NDCG@5 | Cold NDCG@5 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for c in report.conditions:
        p = c.overall.precision_at_5
        r = c.overall.recall_at_5
        n = c.overall.ndcg_at_5
        lines.append(
            f"| {c.display_name} | {c.selected_cbf_weight:.2f} | "
            f"{p.mean:.3f} [{p.ci_95_low:.3f}, {p.ci_95_high:.3f}] | "
            f"{r.mean:.3f} [{r.ci_95_low:.3f}, {r.ci_95_high:.3f}] | "
            f"{n.mean:.3f} [{n.ci_95_low:.3f}, {n.ci_95_high:.3f}] | "
            f"{c.warm_start.ndcg_at_5.mean:.3f} | "
            f"{c.cold_start.ndcg_at_5.mean:.3f} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LearnPath RQ3 ablation study and optionally render EVALUATION_REPORT.md."
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
    parser.add_argument(
        "--write-markdown-report",
        action="store_true",
        default=True,
        help="Generate backend/experiments/EVALUATION_REPORT.md combining RQ1–RQ4 results.",
    )
    args = parser.parse_args()

    configure_logging()
    with open_experiment_session(args.db) as (db, db_backend):
        ablation_report = run_ablation_study(
            db,
            db_backend=db_backend,
            n_boot=args.bootstrap_samples,
            write_artifacts=True,
        )
        print(format_ablation_console_table(ablation_report))

        if args.write_markdown_report:
            eval_report = run_model_evaluation(
                db,
                db_backend=db_backend,
                n_boot=args.bootstrap_samples,
                write_artifacts=True,
            )
            md = render_academic_evaluation_markdown(eval_report, ablation_report)
            DEFAULT_MARKDOWN_REPORT_PATH.write_text(md, encoding="utf-8")
            logger.info("Wrote academic evaluation Markdown report to %s", DEFAULT_MARKDOWN_REPORT_PATH)


if __name__ == "__main__":
    main()
