# LearnPath — Experimental Evaluation & Ablation Report (COME 491, RAD v2.0)

> **Methodological Scope Notice (RAD Section 3.4.4)**: All offline metrics below are computed on a documented deterministic cohort simulation (`data_origin = documented_cohort_simulation`, `seed = 4912026`) over the curated 54-resource Python fundamentals catalog. Offline ranking metrics evaluate alignment with held-out high-utility student ratings (`rating >= 4`); they do **not** establish real-world pedagogical learning gains without a future consent-based human study.

## 1. Dataset Provenance, Split Integrity & Environment

| Property | Recorded Value |
| :--- | :--- |
| Data Origin | `documented_cohort_simulation` (`seed = 4912026`) |
| Active Curriculum Topics / Resources | `6` DAG topics / `54` active resources (`42` in evaluated English unlocked union) |
| Total Learners / Evaluated Test Learners | `48` total / `48` test queries (`40` warm-start, `8` cold-start) |
| Raw / Deduplicated Feedback Rows | `622` raw / `622` deduplicated (`0` duplicates removed pre-split) |
| User–Resource Matrix Density | `24.00%` (unrated entries treated strictly as unknown, never `0`) |
| Chronological Split (`70 / 15 / 15`) | Train: `435` (<= `2026-11-01T08:48:41.406092+00:00`) · Validation: `94` (<= `2026-11-12T02:38:35.522328+00:00`) · Test: `93` |
| Validation-Selected Hybrid Weights | `w_cbf = 0.60`, `w_cf = 0.40` (`min_common_items = 2`, `min_neighbors = 2`) |
| Bootstrap Configuration | Paired student-level percentile bootstrap (`B = 1000`, `seed = 4912026`) |
| Runtime Environment | Python `3.14.6` · scikit-learn `1.9.1` · NumPy `2.5.5` · SQLAlchemy `2.1.9` · OS `Windows 10 (10.0.19045)` (`sqlite_in_memory`) |

---

## 2. RQ1 — Overall Ranking Quality Across Benchmark Methods (`K = 5`)

All methods rank the **exact same prerequisite-unlocked, language-matched, unseen candidate pool** per test student, breaking exact score ties deterministically by `resource_id`. Queries with zero held-out eligible relevant items (`rating >= 4`) are excluded from `Recall@5` and `NDCG@5` aggregation (`excluded_zero_relevant_queries` reported explicitly).

| Method | Evaluated / Total Queries (Excluded 0-Rel) | Precision@5 (95% CI) | Precision@5 (All Queries) | Recall@5 (95% CI) | NDCG@5 (95% CI) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Popularity Baseline** | `27 / 48` (`21`) | `0.156` [`0.111`, `0.207`] | `0.087` | `0.593` [`0.426`, `0.753`] | `0.364` [`0.255`, `0.488`] |
| **Content-Based Filtering (TF-IDF)** | `27 / 48` (`21`) | `0.230` [`0.185`, `0.274`] | `0.129` | `0.864` [`0.741`, `0.975`] | `0.633` [`0.512`, `0.752`] |
| **Collaborative Filtering (User-KNN)** | `27 / 48` (`21`) | `0.156` [`0.111`, `0.200`] | `0.087` | `0.648` [`0.481`, `0.815`] | `0.476` [`0.322`, `0.626`] |
| **Weighted Hybrid (w_cbf=0.60)** | `27 / 48` (`21`) | `0.237` [`0.200`, `0.281`] | `0.133` | `0.901` [`0.802`, `0.988`] | `0.669` [`0.558`, `0.782`] |
| **Rule-Based Prototype (Phase 3 Reference)** *(Prototype Ref.)* | `27 / 48` (`21`) | `0.237` [`0.185`, `0.289`] | `0.133` | `0.877` [`0.765`, `0.988`] | `0.666` [`0.545`, `0.780`] |

### Paired Student-Level Bootstrap Comparisons (`RQ1`: `Hybrid - Baseline`)

| Comparison | Metric | Mean Paired Delta | 95% Bootstrap CI | Two-Sided p-value | Paired Students (`n`) | 95% CI Excludes 0 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `Hybrid - Popularity` | `Precision@5` | `+0.081` | [`+0.044`, `+0.119`] | `0.0000` | `27` | `Yes` |
| `Hybrid - Popularity` | `Recall@5` | `+0.309` | [`+0.148`, `+0.475`] | `0.0000` | `27` | `Yes` |
| `Hybrid - Popularity` | `NDCG@5` | `+0.305` | [`+0.209`, `+0.396`] | `0.0000` | `27` | `Yes` |
| `Hybrid - Popularity` | `TFIDF_Diversity@5` | `-0.002` | [`-0.005`, `+0.000`] | `0.0860` | `48` | `No` |
| `Hybrid - CBF` | `Precision@5` | `+0.007` | [`+0.000`, `+0.022`] | `0.6940` | `27` | `No` |
| `Hybrid - CBF` | `Recall@5` | `+0.037` | [`+0.000`, `+0.111`] | `0.7100` | `27` | `No` |
| `Hybrid - CBF` | `NDCG@5` | `+0.036` | [`-0.025`, `+0.110`] | `0.2720` | `27` | `No` |
| `Hybrid - CBF` | `TFIDF_Diversity@5` | `+0.001` | [`+0.000`, `+0.002`] | `0.0180` | `48` | `Yes` |
| `Hybrid - CF` | `Precision@5` | `+0.081` | [`+0.037`, `+0.133`] | `0.0000` | `27` | `Yes` |
| `Hybrid - CF` | `Recall@5` | `+0.253` | [`+0.099`, `+0.407`] | `0.0000` | `27` | `Yes` |
| `Hybrid - CF` | `NDCG@5` | `+0.193` | [`+0.086`, `+0.313`] | `0.0000` | `27` | `Yes` |
| `Hybrid - CF` | `TFIDF_Diversity@5` | `-0.001` | [`-0.004`, `+0.001`] | `0.3920` | `48` | `No` |

---

## 3. RQ2 — Warm-Start vs. Cold-Start Performance & Fallback Honesty

- **Warm-Start Slice**: Test learners with `>= 2` pre-test historical ratings (`n = 40`).
- **Cold-Start Slice**: New/limited-history learners with `0` pre-test historical ratings (`n = 8`). When collaborative neighbor support is unavailable, `Hybrid` automatically falls back to pure `CBF` (`cold_start_fallback_rate = 100%` on cold-start learners) and never fabricates peer-similarity explanations.

| Method | Warm-Start NDCG@5 (95% CI) | Warm-Start Precision@5 | Cold-Start NDCG@5 (95% CI) | Cold-Start Precision@5 | Overall Cold-Start Fallback | Format Relaxation Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Popularity Baseline** | `0.407` [`0.263`, `0.544`] | `0.158` | `0.260` [`0.102`, `0.437`] | `0.150` | `0.0%` | `77.1%` |
| **Content-Based Filtering (TF-IDF)** | `0.659` [`0.494`, `0.817`] | `0.189` | `0.571` [`0.485`, `0.679`] | `0.325` | `0.0%` | `25.0%` |
| **Collaborative Filtering (User-KNN)** | `0.586` [`0.406`, `0.763`] | `0.168` | `0.215` [`0.066`, `0.377`] | `0.125` | `16.7%` | `41.7%` |
| **Weighted Hybrid (w_cbf=0.60)** | `0.710` [`0.559`, `0.857`] | `0.200` | `0.571` [`0.485`, `0.679`] | `0.325` | `16.7%` | `25.0%` |
| **Rule-Based Prototype (Phase 3 Reference)** | `0.673` [`0.508`, `0.830`] | `0.189` | `0.649` [`0.550`, `0.752`] | `0.350` | `0.0%` | `22.9%` |

---

## 4. RQ3 — Feature & Collaborative-Evidence Ablation Study (`K = 5`)

Prerequisite DAG access gates and language eligibility remain strictly fixed across all four ablation conditions, and `w_cbf` is re-tuned solely on each condition's own Validation split.

| Ablation Condition | Tuned `w_cbf` (Val NDCG@5) | Precision@5 (95% CI) | Recall@5 (95% CI) | NDCG@5 (95% CI) | Warm NDCG@5 | Cold NDCG@5 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full Hybrid (Profile + Assessment + CF)** | `0.60` (`0.620`) | `0.237` [`0.200`, `0.281`] | `0.901` [`0.802`, `0.988`] | `0.669` [`0.558`, `0.782`] | `0.710` | `0.571` |
| **Hybrid w/o Profile Preferences (-Profile)** | `0.40` (`0.612`) | `0.222` [`0.178`, `0.267`] | `0.827` [`0.691`, `0.938`] | `0.625` [`0.498`, `0.754`] | `0.687` | `0.476` |
| **Hybrid w/o Assessment Scores (-Assessment)** | `0.20` (`0.550`) | `0.156` [`0.111`, `0.200`] | `0.660` [`0.481`, `0.833`] | `0.505` [`0.354`, `0.661`] | `0.663` | `0.129` |
| **Hybrid w/o Collaborative Evidence (-CF / CBF-Only)** | `1.00` (`0.571`) | `0.230` [`0.185`, `0.274`] | `0.864` [`0.741`, `0.975`] | `0.633` [`0.512`, `0.752`] | `0.659` | `0.571` |

### Paired Student-Level Bootstrap Ablation Deltas (`RQ3`: `Ablated - Full Hybrid`)

| Ablation Contrast | Metric | Mean Paired Delta | 95% Bootstrap CI | Two-Sided p-value | 95% CI Excludes 0 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `(-Profile) - Full Hybrid` | `Precision@5` | `-0.015` | [`-0.037`, `+0.000`] | `0.2520` | `No` |
| `(-Profile) - Full Hybrid` | `Recall@5` | `-0.074` | [`-0.185`, `+0.000`] | `0.2080` | `No` |
| `(-Profile) - Full Hybrid` | `NDCG@5` | `-0.044` | [`-0.098`, `+0.002`] | `0.0560` | `No` |
| `(-Assessment) - Full Hybrid` | `Precision@5` | `-0.081` | [`-0.141`, `-0.037`] | `0.0000` | `Yes` |
| `(-Assessment) - Full Hybrid` | `Recall@5` | `-0.241` | [`-0.401`, `-0.099`] | `0.0000` | `Yes` |
| `(-Assessment) - Full Hybrid` | `NDCG@5` | `-0.164` | [`-0.277`, `-0.040`] | `0.0020` | `Yes` |
| `(-CF / CBF-Only) - Full Hybrid` | `Precision@5` | `-0.007` | [`-0.022`, `+0.000`] | `0.7020` | `No` |
| `(-CF / CBF-Only) - Full Hybrid` | `Recall@5` | `-0.037` | [`-0.111`, `+0.000`] | `0.6800` | `No` |
| `(-CF / CBF-Only) - Full Hybrid` | `NDCG@5` | `-0.036` | [`-0.101`, `+0.032`] | `0.3020` | `No` |

---

## 5. RQ4 & NFR-05 — Catalog Coverage, Intra-List Diversity@5 & Latency

| Method | Unique Items | Coverage (Eligible Pool) | Coverage (Full 54 Catalog) | Topic-Tag Diversity@5 | Topic+Format Diversity@5 | TF-IDF Cosine Diversity@5 | Rank p50 (ms) | Rank p95 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Popularity Baseline** | `30` | `71.4%` | `55.6%` | `0.703` | `0.678` | `0.969` | `0.10` | `0.18` |
| **Content-Based Filtering (TF-IDF)** | `35` | `83.3%` | `64.8%` | `0.712` | `0.643` | `0.965` | `4.35` | `6.17` |
| **Collaborative Filtering (User-KNN)** | `35` | `83.3%` | `64.8%` | `0.739` | `0.661` | `0.968` | `1.31` | `1.83` |
| **Weighted Hybrid (w_cbf=0.60)** | `35` | `83.3%` | `64.8%` | `0.701` | `0.640` | `0.967` | `4.92` | `6.24` |
| **Rule-Based Prototype (Phase 3 Reference)** | `34` | `81.0%` | `63.0%` | `0.662` | `0.624` | `0.964` | `0.25` | `0.39` |

### End-to-End Server Turnaround Verification (`NFR-05 < 2000 ms`)

- **Benchmark Protocol**: `20` sequential authenticated HTTP iterations (`POST /api/v1/assessments/submit` + `GET /api/v1/recommendations?strategy=hybrid&limit=5`) with warm TF-IDF catalog cache (`warm_cache = True`).
- **End-to-End Assessment + Hybrid Recommendation**: `p50 = 48.66 ms` · `p95 = 63.86 ms` · `max = 142.87 ms` (Requirement: `< 2000 ms` -> **PASS**).
- **`GET /api/v1/recommendations?strategy=hybrid` Only**: `p50 = 28.58 ms` · `p95 = 36.10 ms`.

---

## 6. Research Limitations & Threats to Validity (RAD Section 3.4.4)

1. Interactions originate from a documented deterministic cohort simulation (seed=4912026) over a curated 54-resource Python catalog; simulated ratings reflect modelled topic-gap, format, difficulty, and peer-cluster preferences and therefore do not establish real-world pedagogical learning gains.
2. A compact domain catalog (54 total resources; 42 English, 12 Turkish across 6 DAG topics) bounds maximum achievable diversity and may elevate top-5 hit rates relative to large open-web repositories.
3. Cold-start slice uncertainty (n=8 cold-start students) is reported with both paired bootstrap intervals and exact descriptive slice counts per RAD Section 3.4.4.
4. Offline ranking metrics (Precision@5, Recall@5, NDCG@5) measure alignment with held-out high-utility resource feedback (rating >= 4); a consent-based human learner study with pre/post-testing is required to claim improved learning outcomes.
