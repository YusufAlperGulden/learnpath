# LearnPath (COME 491) — Master Specification Reference

Synchronized across:
1. **Requirements Analysis Document (RAD — Sections 1–4, Figures 1–7)**
2. **LearnPath Haftalık Hazırlık ve Görev Dağılımı (COME 491 Weekly Team Plan)**
3. **LearnPath — Teknoloji Yığını, Ekip İş Bölümü ve Kodlama Rehberi (v2.0 — 100% RAD Synchronized)**

---

## 1. Project Identity, Scope & Team Module Ownership

- **Project**: LearnPath — A Personalized Learning and Course Recommendation System (`COME 491` Graduation Project, Doğuş Üniversitesi)
- **Workspace**: `C:\Users\stajyer\.gemini\antigravity\scratch\learnpath`
- **GitHub Repository**: https://github.com/YusufAlperGulden/learnpath (`develop` = integration branch, `main` = production auto-deployed branch)
- **Live Cloud Service**: https://learnpath-sfdj.onrender.com (`srv-dc2j89d9fdbs73fru350`)
- **In-Scope**: Foundational Python curriculum; `STUDENT` and `ADMIN` roles; <3-min profile & format setup; diagnostic & topic assessments; prerequisite-aware DAG study path; 5-method explainable recommendations; dual progress, bookmarks & 1–5 ratings; admin catalog, DAG, and versioned question management.
- **Strictly Out-of-Scope**: Automated web scraping/video crawling; in-browser Python code execution/compiler; non-Python languages; native mobile binaries/offline app.

| Student ID | Member | Module Ownership |
| :--- | :--- | :--- |
| `202003001090` | Eren Onur | DevOps, Docker, 13-table SQLAlchemy 2.0/Alembic (`postgresql+psycopg://`), JWT RBAC, StudentProfile API, timestamped logging |
| `202203001112` | Emre Kaplan | Topic DAG (pure-Python DFS), Resource Catalog CRUD (`is_active` soft-deactivate, duplicate URL `409`), Versioned Question Pool (`version + 1`), Admin UI, `seed_data.py` |
| `202303001020` | Yusuf Alper Gülden | Stateless `test_session_token` delivery, Atomic Assessment Grading (skipped `NULL`, `422` invalid guard), Dual Progress (`ResourceProgress` & `TopicProgress`), Bookmarks, Feedback, Exam & Answer Review UI |
| `202303001131` | Yusuf Uzun | 5-Strategy Explainable Recommender (`rule_based`, `popularity`, `cbf`, `cf`, `hybrid`), Prerequisite Gate, Cold-Start/Format Fallbacks, Chronological Evaluation & Paired Bootstrap Ablation (`RQ1–RQ4`) |
| `202303001046` | Selin Kuğu | React 18 + TS + Tailwind Design System, Protected Routing, Auth, 3-Step Profile Setup, Student Overview, React Flow Prerequisite Roadmap, Results & Recommendations UI |

---

## 2. Project Objectives (`OBJ-01`–`OBJ-05`)

- **`OBJ-01` (Structured Onboarding & Profiling)**: 100% of registered students configure learning goals and preferred content formats in under 3 minutes and persist preferences across sessions.
- **`OBJ-02` (Topic-Level Diagnostic Assessment)**: Automated scoring calculating both overall score and per-topic accuracy immediately upon test submission.
- **`OBJ-03` (Prerequisite-Aware Learning Path)**: Recommended learning sequences strictly respect directed acyclic prerequisite relationships so foundational topics precede dependent topics.
- **`OBJ-04` (Explainable Resource Recommendations)**: 100% of recommended items display a title, valid external URL, content format, target topic, and human-readable recommendation rationale.
- **`OBJ-05` (Offline Recommendation Evaluation)**: Compare Popularity, Content-Based Filtering, Collaborative Filtering, and Hybrid strategies under a unified leak-free chronological train/val/test split using `Precision@5`, `Recall@5`, `NDCG@5`, `Catalog Coverage`, `Intra-List Diversity`, and `p50`/`p95` latency (`< 2.0s`).

---

## 3. Functional Requirements (`FR01`–`FR12`) & Verifiable Acceptance Criteria

| ID | Role | Requirement & Acceptance Criterion |
| :--- | :--- | :--- |
| **`FR01`** | Student / Admin | Login with valid credentials redirects to role-specific workspace; Student access to `/api/v1/admin/*` returns HTTP `403` and `/admin/*` UI routes block/redirect. |
| **`FR02`** | Student | Create, view, and update `display_name`, `learning_goal`, `experience_level`, multi-select `preferred_formats` (`VIDEO`, `ARTICLE`, `EXERCISE`), and `preferred_language` (`en`/`tr`), persisted across logout/login. |
| **`FR03`** | Student | Present topic-tagged multiple-choice Python questions without exposing `correct_option` or `explanation` before submission and without writing draft DB rows; allow confirmed blank answers (`selected_option = NULL`, `is_correct = False`); reject malformed payloads with HTTP `422`. |
| **`FR04`** | Student | Atomically compute and persist overall percentage score and per-topic `correct_count / question_count` (`score_percent`), displaying immediate item-level solution explanations and a dedicated `Skipped Questions` section. |
| **`FR05`** | Student | Generate an ordered Python learning path where any topic with an unmastered prerequisite (`< 70%`) remains `LOCKED` and foundational weak prerequisites are prioritized first. |
| **`FR06`** | Student | Rank active, language-matched, unseen curated resources aligned with weak unlocked topics, proficiency level, and preferred formats; relax format with an explicit notice (`Scenario 2 — 3a`) if insufficient preferred-format items exist. |
| **`FR07`** | Student | Render clickable title/external URL, format badge, target topic, and non-empty human-readable `rationale` on every recommendation card; never fabricate collaborative peer claims during cold start. |
| **`FR08`** | Student | Bookmark resources (`saved_resources`), track `OPENED` vs `COMPLETED` (`resource_progress`), and toggle personal topic study checklists (`topic_progress.is_manually_completed`) independently of exam-verified `mastery_status`. |
| **`FR09`** | Student | Submit `1..5` usefulness rating and optional text comment (`feedback`, unique per `(student_id, resource_id)`). |
| **`FR10`** | Admin | Resource CRUD (`title`, mandatory TF-IDF `description`, unique `external_url`, `topic_id`, `content_type`, `difficulty`, `language`, `estimated_minutes`), duplicate URL `409` alert with edit link (`Scenario 3 — 4a`), and FK-safe soft deactivation (`is_active = False`). |
| **`FR11`** | Admin | Create/edit/delete Python curriculum topics and directed prerequisites while pure-Python DFS rejects self-references and cycles (`HTTP 400`). |
| **`FR12`** | Admin | Question bank CRUD (`question_text`, optional `code_snippet`, `option_a..d`, `correct_option`, `explanation`, `difficulty`); editing an answered question preserves the old row untouched (`is_active = False`) and creates `version + 1` with `previous_question_id`. |

---

## 4. Use Cases (`UC01`–`UC08`) & Operational Scenarios

- **`UC01`**: Manage Profile & Goals (`FR01`, `FR02`)
- **`UC02`**: Take Assessment Test (`FR03`, `FR04`) — `«include»` -> `UC03`
  - *Alt `3a` (Unanswered Questions)*: Warn student with count/numbers; allow jumping to first unanswered or confirming skipped submission.
  - *Alt `4a` (Network Failure)*: Persist draft in `sessionStorage` and auto-sync when browser `online` event fires.
- **`UC03`**: View Recommended Resources (`FR06`, `FR07`)
  - *Alt `3a` (No Specific Format Match)*: Relax format constraint with explicit fallback badge/message without relaxing prerequisite locks.
- **`UC04`**: Save & Bookmark Resource (`FR08`)
- **`UC05`**: Track Learning Path & Progress (`FR05`, `FR08`)
- **`UC06`**: Submit Resource Feedback (`FR09`)
- **`UC07`**: Manage Resource Catalog (`FR10`)
  - *Alt `4a` (Duplicate URL)*: Alert admin on HTTP `409` and offer direct `"Edit existing resource instead"` action.
- **`UC08`**: Manage Question Pool & Prerequisites (`FR11`, `FR12`)

---

## 5. Nonfunctional Requirements (`NFR-01`–`NFR-14`)

- **`NFR-01` (Intuitive Navigation)**: Seamless role-based navigation without external guidance.
- **`NFR-02` (Readability & Form Accessibility)**: High-contrast typography, PrismJS code blocks, `<InlineCodeText />` inline code formatting, and explicit `<label>` associations on all inputs.
- **`NFR-03` (Data Persistence)**: PostgreSQL ACID persistence across sessions.
- **`NFR-04` (Error Handling & Duplicate Prevention)**: Friendly validation messages, immediate submit button lock (`isLoading`), and server-side `attempt_id` + `IntegrityError` idempotency.
- **`NFR-05` (Response Time)**: `< 2.0s` end-to-end assessment grading + personalized recommendation rendering.
- **`NFR-06` (Modular Architecture)**: Separated UI (`frontend/`), routers/services/recommenders (`backend/app/`), and ORM/Alembic persistence.
- **`NFR-07` (Logging)**: Timestamped backend error and recommendation execution logs.
- **`NFR-08` / `NFR-09` (Stack & Evolution)**: React + FastAPI + PostgreSQL + Scikit-learn; transparent Rule-Based prototype retained alongside Popularity, CBF, CF, and Hybrid models.
- **`NFR-10` / `NFR-11` (Browser & REST JSON)**: Plugin-free Chrome/Firefox/Edge compatibility; structured `/api/v1` REST JSON contracts.
- **`NFR-12` (Packaging)**: Monorepo with `frontend/package.json`, `backend/requirements.txt`, `docker-compose.yml`, Alembic migrations, seed scripts, and step-by-step `README.md`.
- **`NFR-13` / `NFR-14` (Legal & Privacy)**: External links only (no hosted third-party copyrighted media); Argon2id password hashing and strict educational data scope.

---

## 6. Complete 13-Table PostgreSQL Data Dictionary (Revised RAD v2.0)

1. **`users`**: `user_id` (UUID PK), `email` (UNIQUE), `password_hash`, `role` (`STUDENT`|`ADMIN`), `created_at`
2. **`student_profiles`**: `student_id` (UUID PK/FK -> `users`), `display_name`, `learning_goal`, `experience_level`, `preferred_formats` (JSONB), `preferred_language`, `updated_at`
3. **`topics`**: `topic_id` (UUID PK), `name`, `slug` (UNIQUE), `description`, `display_order`
4. **`topic_prerequisites`**: `(topic_id, prerequisite_topic_id)` composite PK/FK -> `topics`
5. **`resources`**: `resource_id` (UUID PK), `topic_id` (FK), `created_by` (FK -> `users`), `title`, `description`, `external_url` (UNIQUE), `content_type`, `difficulty`, `language`, `estimated_minutes` (NULL), `is_active`, `created_at`
6. **`questions`**: `question_id` (UUID PK), `topic_id` (FK), `created_by` (FK -> `users`), `question_text`, `code_snippet` (NULL), `option_a`, `option_b`, `option_c`, `option_d`, `correct_option`, `explanation`, `difficulty`, `version`, `previous_question_id` (NULL FK -> `questions`), `is_active`, `created_at`
7. **`test_attempts`**: `attempt_id` (UUID PK), `student_id` (FK -> `users`), `test_type` (`DIAGNOSTIC`|`TOPIC_QUIZ`), `target_topic_id` (NULL FK -> `topics`), `overall_score_percent`, `started_at`, `submitted_at`
8. **`answers`**: `(attempt_id, question_id)` composite PK/FK, `selected_option` (`A`..`D` or `NULL`), `is_correct`
9. **`topic_scores`**: `(attempt_id, topic_id)` composite PK/FK, `correct_count`, `question_count`, `score_percent`
10. **`topic_progress`**: `(student_id, topic_id)` composite PK/FK, `is_manually_completed`, `manually_completed_at` (NULL), `latest_score_percent` (NULL), `mastery_status` (`UNKNOWN`|`NEEDS_PRACTICE`|`MASTERED`), `updated_at`
11. **`resource_progress`**: `(student_id, resource_id)` composite PK/FK, `status` (`OPENED`|`COMPLETED`), `first_opened_at`, `completed_at` (NULL), `last_accessed_at`
12. **`saved_resources`**: `(student_id, resource_id)` composite PK/FK, `saved_at`
13. **`feedback`**: `feedback_id` (UUID PK), `student_id` (FK), `resource_id` (FK), `rating` (`1..5`), `comment` (NULL), `created_at` (`UNIQUE(student_id, resource_id)`)

---

## 7. 7-Screen Figma UI Design Checklist (`RAD §3.4.5`, Palette `#14532d` & `#e6efea`)

1. **Screen 1 — Login / Create Account (`/auth`)**: Top bar (`LearnPath` green book icon + `Sign in` / `Register` pills), sage `#e6efea` canvas, centered `Learn Path` / `Your Learning Guide.`, white card (`Full Name`, `Email`, `Password`, dark forest-green submit button).
2. **Screen 2 — Student Overview (`/dashboard`)**: Left workspace sidebar + motivational card, breadcrumb + search + user chip, mint hero banner with `1 Learn — 2 Practice — 3 Build` card, `Picked for your potential` topic pills + spotlight + 3 visual resource cards, `Pick up where you left off` resume card, right-rail `Progress dashboard` semi-circular gauge + `Learning activity` bar chart + warm sand `Check my skills` card.
3. **Screen 3 — Profile & Goal Setup (`/profile/setup`)**: Focused header, 3-step stepper (`1 Your profile — 2 Placement test — 3 Your learning path`), goal dropdown, 3 experience radio cards, multi-select format checkboxes + language option, forest-green `Save & Start Placement Test` CTA.
4. **Screen 4 — Python Placement Test (`/assessment`)**: Centered header pill (`Python Placement Test | Question X of Y`), answered-count progress bar + question pills, `Topic:` badge, `<InlineCodeText />` stem + PrismJS Python code snippet, 2x2 option cards (`A–D`), `Previous` / `Submit test` (skip-warning modal) / `Next Question`, `Your progress is saved automatically.` footer.
5. **Screen 5 — Detailed Answer & Gap Review (`/assessment/attempts/:id`)**: Centered `Detail Test Analysis and Gap Review` `<h1>`, `NEW PATHWAY LOCKED` / `UNLOCKED` banner, topic score pills, filter tabs (`All`, `Incorrect`, `Skipped`, `Correct`), red incorrect vs green correct option highlights, green `Solution & Explanation` box, and dedicated `Skipped Questions` section.
6. **Screen 6 — Results & Reasoned Recommendations (`/recommendations` + `/roadmap` + `/bookmarks`)**: 2-column top summary (`Placement Test Results` donut + `Topic Based Breakdown` mastery bars), 5-strategy selector, 3-column resource cards with `Open Resource`, `Done`, `Save`, `Rate`, `Quiz`, and green `Why recommended:` rationale box, plus bottom `Your learning path is ready.` banner linking to React Flow DAG (`/roadmap`).
7. **Screen 7 — Admin Studio (`/admin/resources` & `/admin/topics-questions`)**: `ADMIN` sidebar (`Resource Management`, `Question Pool`, `Topics & Prerequisites`), `+ Add New Resource` & `+ Add Test Question` buttons, 3 KPI cards, search + dropdowns + topic pills, paginated catalog table, interactive 6-node DAG editor, and versioned question bank.
