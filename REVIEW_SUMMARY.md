# REVIEW SUMMARY

- baseline SLA status: FAIL (p95/p99 exceed thresholds)
- optimized SLA status: PASS (all latency percentiles within SLA)

- query count change per endpoint:
  - `list_users`: avg queries per request **11.481 -> 1.499** (−87.0%)
  - `followers_page`: avg queries per request **11.519 -> 1.501** (−87.0%)

- applied optimizations (concise):
  1. Replace per-request COUNT(*) with O(1) lookup from `counters.users`.
  2. Remove N+1 by switching follower lookup to a single JOIN.
  3. Add composite index on `(user_id, follower_id)` to speed follower lookup.

(See `metrics_baseline.json` and `metrics_optimized.json` for full measurements.)


## Bottleneck → Fix mapping
- COUNT(*) on `users` table → added `counters.users` lookup to avoid full-table aggregation per request
- N+1 when resolving follower -> user → single JOIN query to fetch follower user rows
- Missing composite index → add `ix_followers_user_follower (user_id, follower_id)` to speed follower lookups

## Code diff summary
- modified `handlers.py` — replaced COUNT(*) + N+1 code paths with O(1) counters lookup and JOIN
- modified `app.py` — added composite index on `(user_id, follower_id)` (non-destructive)

## Artifacts
- metrics: `metrics_baseline.json`, `metrics_optimized.json`
- logs: `run_output_baseline.log`, `run_output_optimized.log`
- seed script: `seed_db.py`
- runner (in-process): `runner.py`

