---
name: learnpath-spec
description: >-
  Complete requirements, 13-table data dictionary, API contracts, 5-method ML evaluation protocol,
  team module ownership, and 7-screen Figma UI specification for the LearnPath COME 491 Python
  learning path and explainable recommendation system. Activate whenever working on, auditing,
  testing, or extending LearnPath.
---

# LearnPath Specification & Audit Skill

Use this skill whenever the user asks to build, review, test, debug, or verify **LearnPath** (`C:\Users\stajyer\.gemini\antigravity\scratch\learnpath` and live deployment `https://learnpath-sfdj.onrender.com`) against project documents.

## Workflow
1. Read [references/rad_and_ui_spec.md](./references/rad_and_ui_spec.md) to check exact acceptance criteria across:
   - Objectives `OBJ-01`–`OBJ-05` & Functional Requirements `FR01`–`FR12`
   - Use Cases `UC01`–`UC08` & Scenarios 1–3 (including Alternative Flows `3a`/`4a`)
   - Nonfunctional Requirements `NFR-01`–`NFR-14`
   - Complete 13-Table PostgreSQL Data Dictionary & Integrity Rules
   - 5-Strategy Recommender & Offline `RQ1`–`RQ4` Evaluation/Ablation Protocol (`K = 5`)
   - 7-Screen Figma Navigational Paths & Visual Layout Checklist
2. Verify backend changes with `ruff check . ../.devcontainer` and `pytest -v` inside `backend/.venv`, and frontend changes with `npm run build` inside `frontend/`.
3. For live UI/deployment checks on `https://learnpath-sfdj.onrender.com`, delegate to the `browser` subagent and verify claims against `BROWSER_HOST_FACTS`.
