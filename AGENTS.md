# LearnPath (COME 491) — Mandatory Project & Architecture Rules

Whenever modifying, reviewing, or deploying LearnPath (`C:\Users\stajyer\.gemini\antigravity\scratch\learnpath`), enforce these invariants from **Revised RAD v2.0** and **Technology & Coding Guide v2.0**:

## 1. Scope & Stack Invariants
- **Domain Scope**: Foundational Python only (curated external videos, articles, and exercise links). Never add automated web scraping/crawling or in-browser Python code execution (`RAD §1.2`, `NFR-13`).
- **Stack**: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL (`postgresql+psycopg://` driver prefix required for `psycopg` v3) + Scikit-learn on backend; React 18 + TypeScript + Vite + Tailwind CSS + TanStack Query + Recharts + `@xyflow/react` + `prism-react-renderer` on frontend (`NFR-08`).
- **Canonical Uppercase Enums**: Keep `STUDENT`/`ADMIN`, `BEGINNER`/`INTERMEDIATE`/`ADVANCED`, `VIDEO`/`ARTICLE`/`EXERCISE`, `DIAGNOSTIC`/`TOPIC_QUIZ`, `UNKNOWN`/`NEEDS_PRACTICE`/`MASTERED`, and `OPENED`/`COMPLETED` identical across DB, Pydantic, and TypeScript (`en`/`tr` lowercase ISO 639-1).

## 2. Database & Assessment Security Rules (13 Exact Tables)
- **Exact 13 Tables**: `users`, `student_profiles`, `topics`, `topic_prerequisites`, `resources`, `questions`, `test_attempts`, `answers`, `topic_scores`, `topic_progress`, `resource_progress`, `saved_resources`, `feedback`. Coordinate any schema changes via a single linear Alembic revision.
- **Answer-Key Confidentiality (`FR03`)**: Question delivery endpoints (`/api/v1/assessments/questions`) MUST NEVER expose `correct_option` or `explanation` before submission, and MUST NOT insert draft `test_attempts` rows. Bind question sets with a signed `test_session_token` and client `attempt_id` for idempotent atomic submission (`NFR-04`).
- **Skipped vs Malformed Submissions (`FR03`, Scenario 1 `3a`)**: Confirmed blank answers are valid (`selected_option = NULL`, `is_correct = False`); malformed/tampered JSON payloads must fail with HTTP `422` without creating orphan DB rows.
- **Historical Assessment Preservation (`FR10`, `FR12`)**: Never hard-delete resources (`is_active = False` soft-deactivation). Editing a question already referenced in `answers` must preserve the historical row unchanged, mark it inactive, and create a new row with `version + 1` and `previous_question_id`.
- **Dual Progress & Prerequisite Gate (`FR05`, `FR08`)**: `TopicProgress.is_manually_completed` tracks personal study checklists only; downstream DAG topics unlock strictly when all prerequisites reach `mastery_status == 'MASTERED'` (`>= 70.0%` exam score). Pure-Python DFS must block self-references and cycles (`HTTP 400`, `FR11`).

## 3. Explainable Recommendation & Evaluation Rules (`FR05–FR07`, `OBJ-04–OBJ-05`, `NFR-05`)
- **5 Ranking Strategies**: `rule_based`, `popularity` (tie-break by `resource_id`), `cbf` (Scikit-learn `TfidfVectorizer` + `cosine_similarity` fitted strictly on training/catalog text), `cf` (unknown-aware User-KNN feedback matrix), and `hybrid` (validation-tuned blend).
- **Cold-Start & Fallback Honesty (`RAD §3.4.4.3`)**: Never fabricate collaborative peer claims (`"students like you liked..."`) when neighbor evidence is insufficient; fall back to CBF/profile signals and surface explicit `fallback_applied` / `format_fallback_used` notices. Every recommendation card must display a non-empty human-readable `rationale`.
- **Latency Budget (`NFR-05`)**: Keep end-to-end exam grading + recommendation delivery under `2.0s`.

## 4. 7-Screen Figma UI & Git/Render Deployment Rules
- **Figma Design System (`RAD §3.4.5`)**: Preserve the Forest-Green (`#14532d`) & Sage (`#e6efea` / `#f6f8f7`) palette across all 7 screens (Auth, Student Overview, 3-Step Profile Setup, Step-by-Step Placement Test, Detailed Gap Review with Skipped Questions & Explanations, Placement Results & 3-Col Recommendations + React Flow DAG, and Admin Resource/DAG/Question Studio). Render inline backtick code via `<InlineCodeText />`, clear TanStack Query cache on account switches, and keep user-facing copy free of raw SQL or `(FRxx)` spec tags.
- **Verification & Git Flow**: Never push untested code directly to `main`. Validate with `ruff check .`, `pytest -v`, and `npm run build` on `develop`, then merge `--no-ff` into `main` to trigger Render auto-deploy (`https://learnpath-sfdj.onrender.com`). For full requirement tables, activate the `learnpath-spec` skill.
