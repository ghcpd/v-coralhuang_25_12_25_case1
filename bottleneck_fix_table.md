| Endpoint | Bottleneck | Baseline (p95 / avg_queries) | Optimized (p95 / avg_queries) | Fix applied |
|---|---:|---:|---:|---|
| GET /api/users | COUNT(*) on every page (scans large table) | 524 ms / 2.0 | 102 ms / 1.0 | Load `users_total` into in-memory cache (avoid DB COUNT)
| GET /api/users/1/followers | N+1 queries when loading followers (~100+ queries) | 2583 ms / 102.0 | 221 ms / 2.0 | Single JOIN query to fetch follower rows; ensure composite index (user_id, follower_id)
