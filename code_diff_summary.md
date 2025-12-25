Files changed (minimal and focused):

- `handlers.py` - optimized handlers to avoid per-request COUNT and to replace N+1 follower fetches with a single join; selected only required columns in optimized mode.
- `app.py` - added a small in-memory `counters_cache` and `load_counters_from_db()`; added SQL query counting instrumentation (for per-request query counts).
- `seed_db.py` - added forced re-seed and a hotspot follower distribution to exercise N+1; populates `counters` table for `users_total`.
- `runner.py` / `run_tests.py` - implemented an in-process concurrent runner and test orchestration that invokes handlers directly and records latency and query counts.

All edits are small, localized, and reversible.
