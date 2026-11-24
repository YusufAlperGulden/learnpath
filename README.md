# LearnPath — Personalized Python Learning Path & Explainable Resource Recommendation System

**COME 491 Graduation Project (Revised RAD v2.0)**

LearnPath is an end-to-end personalized Python fundamentals learning platform and comparative recommender-system research testbed. Students configure learning goals and format preferences, take diagnostic or topic-specific Python code assessments, track prerequisite-gated curriculum mastery on an interactive DAG roadmap, and receive transparent, explainable learning resource recommendations across five live strategies (`rule_based`, `popularity`, `cbf`, `cf`, and `hybrid`).

---

## 1. System Architecture & Stack

| Layer | Technology Stack | Key Responsibilities |
| :--- | :--- | :--- |
| **Frontend (`frontend/`)** | React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, `@xyflow/react`, Recharts, Prism | Auth & onboarding, stateless diagnostic/topic exam UI with skipped-question warnings, item-level solution review, DAG roadmap, live 5-strategy recommendations, study library, and admin catalog studio |
| **Backend (`backend/app/`)** | Python 3.11+ (verified on Python 3.14), FastAPI, SQLAlchemy 2.0, Alembic, Psycopg 3 (`postgresql+psycopg://`), PyJWT, Argon2 (`pwdlib`), Scikit-learn | RBAC auth, cycle-safe DAG catalog & immutable question versioning, atomic assessment grading, dual progress tracking (`OPENED`/`COMPLETED` vs. exam mastery), and `< 200 ms` cached TF-IDF/CF/Hybrid recommenders |
| **Database (`docker-compose.yml`)** | PostgreSQL 16 (`learnpath` + `learnpath_test` via `docker/postgres/init-test-db.sql`) | Exact 13 normalized tables (`users`, `student_profiles`, `topics`, `topic_prerequisites`, `resources`, `questions`, `test_attempts`, `answers`, `topic_scores`, `topic_progress`, `resource_progress`, `saved_resources`, `feedback`) |
| **Research Suite (`backend/experiments/`)** | Scikit-learn (`TfidfVectorizer`, `cosine_similarity`), NumPy, SciPy | Leak-free `70/15/15` chronological split, validation-only Hybrid tuning, `RQ1`–`RQ4` evaluation, `NFR-05` HTTP latency verification, and paired student-level bootstrap (`B = 1000`) |

### Repository Layout

```text
learnpath/
├── docker-compose.yml                 # PostgreSQL 16 container + healthcheck
├── docker/postgres/init-test-db.sql   # Auto-creates learnpath_test database
├── .env.example                       # Environment configuration template
├── backend/
│   ├── alembic/                       # 13-table schema migration history
│   ├── app/
│   │   ├── core/                      # Config, enums, Argon2/JWT security, RBAC deps, logging
│   │   ├── models/                    # 13 SQLAlchemy 2.0 ORM models
│   │   ├── schemas/                   # Strict Pydantic v2 request/response contracts
│   │   ├── services/                  # DAG validator, atomic grading, progress, 5 recommenders
│   │   └── routers/                   # /api/v1/{auth,profile,assessments,recommendations,progress,admin}
│   ├── scripts/                       # Idempotent curriculum & 48-student cohort seeders
│   ├── experiments/                   # split_dataset.py, evaluate_models.py, run_ablation.py, EVALUATION_REPORT.md
│   └── tests/                         # Full pytest verification suite (Increments 1–6)
└── frontend/
    └── src/
        ├── api/                       # Typed Axios API clients + JWT interceptor
        ├── components/                # Accessible UI primitives (<dialog>, CodeSnippetBlock, etc.)
        └── pages/                     # Student & Admin screens (Figma Figures 3–7)
```

---

## 2. Clean Setup & Local Run Guide

### Prerequisites
- **Python** `3.11+` (tested on `Python 3.14.6`)
- **Node.js** `20+` and `npm`
- **Docker Desktop** (for PostgreSQL 16; offline experiments and `pytest` also support isolated in-memory SQLite automatically when Docker is stopped)

### Step 1 — Environment & PostgreSQL 16

From the repository root:

```powershell
Copy-Item .env.example .env
# Note: If native PostgreSQL already occupies localhost:5432, set POSTGRES_PORT=5433
# and update DATABASE_URL / TEST_DATABASE_URL ports to 5433 in .env.
docker compose up -d
```

### Step 2 — Backend Virtual Environment, Migrations & Seed Data

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Apply the 13-table PostgreSQL schema
alembic upgrade head

# Seed 6 Python DAG topics, 54 curated resources (en & tr), 36 code questions, and demo users
python -m scripts.seed_data

# (Optional) Seed the 48-student interaction cohort (~622 chronological 1–5 ratings) for CF/Hybrid
python -m scripts.seed_interactions

# Start the FastAPI server on http://localhost:8000
uvicorn app.main:app --reload --port 8000
```

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

### Step 3 — Frontend Development Server & Production Build

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` in Chrome, Firefox, or Edge.

### Default Seeded Demo Accounts

| Role | Email | Password | Seeded State |
| :--- | :--- | :--- | :--- |
| `ADMIN` | `admin@learnpath.local` | `AdminPass123!` | Full access to Topic DAG, Question Versioning, and Resource Catalog Studio |
| `STUDENT` | `student@learnpath.local` | `StudentPass123!` | Cold-start `BEGINNER` profile (`PYTHON_FUNDAMENTALS`, `VIDEO` + `EXERCISE`, `en`) |
| `STUDENT (Cohort)` | `cohort-01@learnpath.local` .. `cohort-48@learnpath.local` | `CohortLearner123!` | `cohort-01..40` warm-start learners; `cohort-41..48` cold-start test learners |

---

## 3. Sharing with Classmates & Presenting at School (Zero Desktop Needed)

LearnPath includes three ready-to-use portable demo modes so classmates and instructors can review code and run the live application on campus without your home desktop:

### Option A — Present Directly in Any Classroom Browser (GitHub Codespaces)
1. Open `https://github.com/YusufAlperGulden/learnpath` in Chrome, Firefox, or Edge on any school computer.
2. Click **Code -> Codespaces -> Create codespace on main** (or `develop`).
3. `.devcontainer/devcontainer.json` automatically starts PostgreSQL 16, applies the 13-table schema, seeds the 54-resource Python catalog + 48-learner cohort, launches FastAPI (`:8000`) and Vite (`:5173`), and opens the live app in a browser tab.

### Option B — Deploy a Permanent Public HTTPS Link on Render (`render.yaml`)
1. Sign in at `https://dashboard.render.com` with your GitHub account.
2. Click **New + -> Blueprint** and select the `YusufAlperGulden/learnpath` repository.
3. Render reads [`render.yaml`](render.yaml) and automatically provisions:
   - `learnpath-db`: Free managed PostgreSQL database
   - `learnpath`: Unified Docker Web Service serving both `/api/v1/*` and the compiled React SPA under one public `https://*.onrender.com` URL (auto-migrated & auto-seeded on boot).

### Option C — 1-Command Offline Demo on Any Classmate's Laptop
Any teammate with Docker Desktop installed can run the entire 3-tier stack with one command:

```powershell
git clone https://github.com/YusufAlperGulden/learnpath.git
cd learnpath
docker compose -f docker-compose.demo.yml up --build
```

Then open `http://localhost:5173` (works completely offline during the presentation once built).

### Team Branching & Code Review Workflow
- `main`: Stable presentation-ready release branch.
- `develop`: Team integration branch (default target for Pull Requests).
- Every `push` and `Pull Request` triggers [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (`ruff check .`, `alembic upgrade head --sql`, `pytest -v`, and `npm run build`).

---

## 4. Reproducing Offline Research Experiments (`RQ1`–`RQ4` & `NFR-05`)

All experiment scripts live in `backend/experiments/` and support `--db auto` (default: uses PostgreSQL if running, or falls back cleanly to an isolated in-memory database seeded deterministically with `seed = 4912026`).

```powershell
cd backend

# 1. Pre-split deduplication, 70/15/15 chronological split, and Validation-only Hybrid weight tuning
.\.venv\Scripts\python.exe -m experiments.split_dataset

# 2. RQ1, RQ2, RQ4 model benchmark + paired bootstrap 95% CIs + NFR-05 (< 2.0s) HTTP latency check
.\.venv\Scripts\python.exe -m experiments.evaluate_models

# 3. RQ3 feature & collaborative-evidence ablation study + regenerate EVALUATION_REPORT.md
.\.venv\Scripts\python.exe -m experiments.run_ablation
```

- Human-readable academic tables, paired student-level bootstrap intervals (`B = 1000`), slice analyses, latency percentiles, and methodological limitations are committed at [`backend/experiments/EVALUATION_REPORT.md`](backend/experiments/EVALUATION_REPORT.md).
- Raw machine-readable JSON outputs (`split_summary.json`, `hybrid_tuning.json`, `model_evaluation.json`, `ablation_results.json`) are written to `backend/experiments/artifacts/`.

---

## 5. Quality Gates & Automated Verification

```powershell
# Backend lint, migration DDL check, and full pytest suite
cd backend
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\alembic.exe upgrade head --sql
.\.venv\Scripts\pytest.exe -v

# Frontend strict TypeScript check and production bundle build
cd ..\frontend
npm run build
```

---

## 6. Core RAD v2.0 Invariants Enforced

1. **Answer-Key Confidentiality & Zero Draft Orphans (`FR03`)**: `GET /api/v1/assessments/questions` never serializes `correct_option` or `explanation` and writes zero DB rows until submission, binding `student_id`, `attempt_id`, and `question_ids` inside a signed `test_session_token`.
2. **Atomic, Idempotent Grading & Skipped-Question Support (`FR04`, `NFR-04`)**: `POST /api/v1/assessments/submit` commits `TestAttempt`, `Answer` (`selected_option = NULL` recorded as `is_correct = False`), `TopicScore`, and `TopicProgress` in one transaction with duplicate-click idempotency on `attempt_id`.
3. **Dual Progress & Latest-Attempt Mastery (`FR05`, `FR08`)**: `OPENED` resource clicks never mark resources `COMPLETED`; manual topic checkboxes (`is_manually_completed`) never unlock DAG prerequisites; exam mastery (`>= 70%` -> `MASTERED`, `< 70%` -> `NEEDS_PRACTICE`) recalculates truthfully from the latest attempt.
4. **Catalog Audit Integrity (`FR11`, `FR12`)**: Historical resources use soft deactivation (`is_active = False`), and editing an already-answered question preserves the old version untouched while creating `version + 1` linked via `previous_question_id`.
5. **Cold-Start Honesty & Leak-Free ML (`Section 3.4.4`, `FR07`)**: Unrated items remain strictly unknown (never imputed as `0`), `TfidfVectorizer` and `CF`/`Popularity` never see test labels, and `Hybrid` falls back to content/profile signals (`fallback_reason = "cold_start_insufficient_neighbors"`) without fabricating peer claims when neighbor support is unavailable.
