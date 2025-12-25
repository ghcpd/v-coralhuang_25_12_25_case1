Summary of code changes (audit)

- handlers.py: replaced COUNT(*) + per-item `UserStats` lookups with a single joined query; changed followers handler to JOIN follower users and read follower count from `user_stats`.
- models.py: added `UserStats` and `AppMeta` models and a composite index on `(user_id, follower_id)`.
- seed_db.py: populate `user_stats` and `app_meta.users_count` during seeding.

The full unified diff is in `artifacts/optimization.patch`.
