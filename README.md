# API pagination performance optimization

What I changed (high level):
- Identified COUNT(*) and N+1 queries as the dominant bottlenecks.
- Replaced COUNT(*) with a pre-computed `counters` lookup for `users`.
- Rewrote follower lookup to use a single JOIN and added a composite index on `(user_id, follower_id)`.

How to reproduce:
- Install dependencies: pip install -r requirements.txt
- Seed DB: python seed_db.py
- Run the orchestration: python run_tests.py

Artifacts produced:
- metrics_baseline.json, metrics_optimized.json
- run_output_baseline.log, run_output_optimized.log
- REVIEW_SUMMARY.md
