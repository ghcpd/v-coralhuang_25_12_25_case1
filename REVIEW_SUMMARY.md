Baseline SLA status: FAIL (baseline `list_users` p95 = 524 ms > 300 ms; `followers_page` p95 = 2583 ms > 300 ms)
Optimized SLA status: PASS (optimized `list_users` p95 = 102 ms <= 300 ms; `followers_page` p95 = 221 ms <= 300 ms)

Query count change per endpoint (measured):
- `list_users` (GET /api/users): baseline avg_queries = 2.0 -> optimized avg_queries = 1.0 (DB count removed via in-memory counter)
- `followers_page` (GET /api/users/1/followers): baseline avg_queries = 102.0 -> optimized avg_queries = 2.0 (N+1 -> single join)

Applied optimizations (concise):
- **Avoid per-request COUNT(*)** by loading `users_total` into an in-memory `counters_cache` (reduces DB queries per request from 2->1).
- **Fix N+1 on followers** by querying Users JOIN Relationship to fetch follower rows in one query and relying on composite index `(user_id, follower_id)`.
- **Select only required columns** in list endpoints in optimized mode to reduce data materialization.

Artifacts produced: `baseline_results.json`, `optimized_results.json`, `run_output_log.txt`, `bottleneck_fix_table.md`, `code_diff_summary.md`.
