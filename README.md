# LearnPath (COME 491 Capstone Project — v2.0)

Personalized Python Learning Path & Explainable Resource Recommendation System, 100% synchronized with the Revised Requirements Analysis Document (RAD v2.0).

## Architecture Overview

- **Backend (`backend/`)**: Python 3.11+ (tested on Python 3.14), FastAPI, SQLAlchemy 2.0, Alembic, Psycopg 3 (`postgresql+psycopg://`), PyJWT + Argon2 (`pwdlib`), Scikit-learn.
- **Database**: PostgreSQL 16 via Docker Compose (13 normalized tables including `topic_progress`, soft-deleted `resources`, and versioned `questions`).
- **Frontend (`frontend/`)**: React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, React Flow (`@xyflow/react`), Recharts, Prism React Renderer.
- **Offline Evaluation (`backend/experiments/`)**: Chronological split, Popularity / CBF / CF / Hybrid comparison, `Precision@5`, `Recall@5`, `NDCG@5`, `Catalog Coverage`, `Intra-List Diversity`, `Latency (p50/p95)`, and paired bootstrap ablation (`RQ1`–`RQ4`).

## Quick Start

### 1. Start PostgreSQL 16

Make sure Docker Desktop is running, then from the repository root:

```powershell
cp .env.example .env   # Adjust POSTGRES_PORT if 5432 is already occupied locally
docker compose up -d
```

### 2. Set Up Backend & Apply 13-Table Schema

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_data
uvicorn app.main:app --reload --port 8000
```

Interactive OpenAPI docs are served at `http://localhost:8000/docs`.

### 3. Set Up Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in Chrome, Firefox, or Edge.

### Default Seeded Accounts (`scripts.seed_data`)

| Role | Email | Password | Seeded Catalog |
| :--- | :--- | :--- | :--- |
| `ADMIN` | `admin@learnpath.local` | `AdminPass123!` | 6 DAG topics, 54 resources (`en` & `tr`), 36 code-snippet questions |
| `STUDENT` | `student@learnpath.local` | `StudentPass123!` | Pre-configured `BEGINNER` profile (`VIDEO`, `EXERCISE`) |

## Key Engineering Rules (RAD v2.0)

1. **Answer Key Confidentiality (`FR03`)**: Assessment question delivery never exposes `correct_option` or `explanation`; a signed `test_session_token` binds `student_id`, `attempt_id`, and `question_ids` without creating orphan draft DB rows.
2. **Atomic & Idempotent Exam Submission (`NFR-04`)**: `POST /api/v1/assessments/submit` persists `TestAttempt`, `Answer` (nullable `selected_option` for skipped questions), `TopicScore`, and `TopicProgress` in a single database transaction.
3. **Latest-Attempt Mastery Recalculation (`FR05`, `FR08`)**: `topic_progress.mastery_status` recalculates from the latest attempt (`>= 70%` -> `MASTERED`, `< 70%` -> `NEEDS_PRACTICE`), while `is_manually_completed` tracks self-paced study independently.
4. **Cold-Start Honesty (`FR07`)**: When collaborative evidence is insufficient, Hybrid falls back to content/profile signals and never fabricates collaborative rationale strings.
