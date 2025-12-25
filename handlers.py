"""Request handlers (baseline).

Handlers follow the constraints:
- authentication via bearer token (fixed-test-token accepted)
- pagination semantics: page, per_page
- response shape includes `items` and `total`

Baseline intentionally performs a COUNT(*) per paginated request and uses
lazy-loaded relationships for the followers endpoint to reproduce N+1.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session
from models import User, Follow, UserStats

# authentication config (kept simple and deterministic for tests)
TEST_TOKEN = "test-token"

# Flag used by the test harness to switch between baseline and optimized code paths.
# The initial run (baseline) keeps this False. The optimization will change code
# on-disk (so the baseline is auditable) and the runner will re-import.
OPTIMIZED = False


def _auth_ok(headers: dict) -> bool:
    auth = headers.get("authorization", "")
    return auth.strip().lower() == f"bearer {TEST_TOKEN}"


def _paginate_params(query_params: dict):
    page = int(query_params.get("page", 1))
    per_page = int(query_params.get("per_page", 20))
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 1000:
        per_page = 100
    offset = (page - 1) * per_page
    return page, per_page, offset


def get_users(db: Session, headers: dict, query: dict):
    """Optimized implementation (preserves pagination and response shape):

    - Eliminates the per-item N+1 by fetching `UserStats` for the page in a single
      query and merging results in-memory.
    - Avoids a full-table COUNT(*) by reading a precomputed counter from `app_meta`.

    The pagination semantics (page/per_page) and JSON schema are unchanged.
    """
    if not _auth_ok(headers):
        return 401, {"error": "unauthorized"}

    page, per_page, offset = _paginate_params(query)

    # single-query: join users -> user_stats and project only required columns
    rows = (
        db.query(
            User.id.label('id'),
            User.username.label('username'),
            UserStats.followers_count.label('followers_count'),
            UserStats.posts_count.label('posts_count'),
        )
        .outerjoin(UserStats, UserStats.user_id == User.id)
        .order_by(User.id)
        .offset(offset)
        .limit(per_page)
        .all()
    )

    items_with_stats = []
    for r in rows:
        items_with_stats.append({
            "id": r.id,
            "username": r.username,
            "followers_count": int(r.followers_count or 0),
            "posts_count": int(r.posts_count or 0),
        })

    # read precomputed total from app_meta (single-row indexed lookup)
    total_row = db.execute("SELECT value_int FROM app_meta WHERE key='users_count'").fetchone()
    total = int(total_row[0]) if total_row else db.query(func.count(User.id)).scalar()

    return 200, {"items": items_with_stats, "total": total}


def get_user_followers(db: Session, headers: dict, path_params: dict, query: dict):
    """Optimized followers endpoint:

    - Loads follower `User` rows with a single JOIN (no N+1).
    - Uses the precomputed follower count from `user_stats` to avoid COUNT(*).
    - Preserves pagination semantics and response shape.
    """
    if not _auth_ok(headers):
        return 401, {"error": "unauthorized"}

    user_id = int(path_params.get("user_id", 0))
    page, per_page, offset = _paginate_params(query)

    # join to load follower users in one query (no per-row lazy loads)
    rows = (
        db.query(User)
        .join(Follow, User.id == Follow.follower_id)
        .filter(Follow.user_id == user_id)
        .order_by(Follow.id)
        .offset(offset)
        .limit(per_page)
        .all()
    )

    items = [u.to_dict() for u in rows]

    # use the stored followers_count from user_stats (single-row lookup)
    stat = db.query(UserStats).filter(UserStats.user_id == user_id).one_or_none()
    total = stat.followers_count if stat is not None else 0

    return 200, {"items": items, "total": total}
