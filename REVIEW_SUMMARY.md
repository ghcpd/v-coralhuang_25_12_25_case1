Baseline SLA status: fail (error rate 92.5% > 0.1%)

Optimized SLA status: fail (p95 386 > 300, error 0.25% > 0.1%)

Query count change per endpoint:
- /api/users: 2 -> 2
- /api/users/1/followers: ~19 -> 2

List of applied optimizations:
- Added composite index on (user_id, follower_id)
- Used join query for followers to avoid N+1