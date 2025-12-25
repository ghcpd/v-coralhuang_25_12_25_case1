# Performance Optimization Exercise

This project implements a small in-process API and a custom runner to measure baseline and optimized behavior for paginated endpoints.

What I changed and why:
- Baseline had COUNT(*) on every `/api/users` request and N+1 queries on `/api/users/<id>/followers`.
- Optimization 1: Avoid COUNT(*) by maintaining a `counters` table and reading the `users_total` counter in optimized mode.
- Optimization 2: Replace per-follower lookups with a single join query on the followers endpoint and ensure a composite index on `(user_id, follower_id)`.

How to reproduce:
1. pip install -r requirements.txt
2. python seed_db.py  # seeds >= 10000 users and relationships

# To force a reseed and create a follower hotspot (to reveal N+1), run:
python seed_db.py --users 200000 --rels 100000 --force --hotspot 50000

3. python run_tests.py

Artifacts written by `run_tests.py`:
- `baseline_results.json`
- `optimized_results.json`
- `run_output_log.txt`

Notes:
- The runner executes handlers in-process with concurrent threads and counts SQL queries using SQLAlchemy events.
- Authentication behavior is preserved (Bearer token `test-token`).
