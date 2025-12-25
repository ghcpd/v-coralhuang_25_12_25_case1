Summary
=======

This project demonstrates an auditable, reproducible optimization of two paginated API endpoints to meet latency SLAs under concurrent authenticated load. All execution is in-process (no HTTP server) and the same runner is used for baseline and optimized measurements.

What I changed (high-level)
- Eliminated heavy COUNT(*) scans by introducing a tiny `app_meta` counter (read-only for tests).
- Removed N+1 queries by bulk-joining `user_stats` (users listing) and joining follower users (followers listing).
- Added a composite index on `(user_id, follower_id)` to accelerate follower lookups.

Why these changes
- COUNT(*) on large tables and per-item N+1 are the primary, measurable bottlenecks for paginated endpoints.
- Changes preserve pagination semantics and ORM usage while reducing query count and latency.

Reproduce (one command)
-----------------------

- Create venv & install:
  python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt

- Run the full benchmark (seeds DB, runs baseline + optimized, writes artifacts):
  .venv\Scripts\python.exe run_tests.py

Artifacts
- artifacts/summary_before_optimization.json  - aggregated baseline summary
- artifacts/summary_after_optimization.json   - aggregated optimized summary
- artifacts/baseline_*.json / artifacts/optimized_*.json - per-endpoint breakdowns
- artifacts/optimization.patch                - code diff applied (audit)
- artifacts/run_before_optimization.log       - raw runner output
- artifacts/review_summary.md                 - short reviewer checklist

Notes for reviewers
- The runner invokes handler functions directly and counts SQL statements via SQLAlchemy events.
- No endpoint response schemas, auth behavior, or pagination semantics were changed.
- All optimization steps are small, auditable code edits and a single lightweight schema addition (`app_meta`).
