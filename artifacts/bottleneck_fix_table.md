| Bottleneck | Fix applied | Evidence file |
|---|---|---|
| COUNT(*) on users table per request | add `app_meta` precomputed `users_count` + read instead of COUNT(*) | artifacts/optimized_list_users.json |
| N+1 loading of per-user stats | bulk JOIN of `user_stats` (single-query) | artifacts/optimized_list_users.json |
| Followers N+1 and missing index | join followers -> users + composite index on (user_id,follower_id) | artifacts/optimized_followers_page.json |
