"""Standalone baseline handlers (used only for reproducible measurements).

These are identical in behavior to the original baseline used to produce the
`before_optimization` artifacts: they perform COUNT(*) on each paginated
request and trigger N+1 when loading per-user stats / follower users.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session
from models import User, Follow, UserStats

TEST_TOKEN = "test-token"


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
    if not _auth_ok(headers):
        return 401, {"error": "unauthorized"}

    page, per_page, offset = _paginate_params(query)

    items = db.query(User).order_by(User.id).offset(offset).limit(per_page).all()

    # N+1: per-user stats fetched separately
    items_with_stats = []
    for u in items:
        s = db.query(UserStats).filter(UserStats.user_id == u.id).one()
        d = u.to_dict()
        d.update(s.to_dict())
        items_with_stats.append(d)

    total = db.query(func.count(User.id)).scalar()
    return 200, {"items": items_with_stats, "total": total}


def get_user_followers(db: Session, headers: dict, path_params: dict, query: dict):
    if not _auth_ok(headers):
        return 401, {"error": "unauthorized"}

    user_id = int(path_params.get("user_id", 0))
    page, per_page, offset = _paginate_params(query)

    follows = (
        db.query(Follow).filter(Follow.user_id == user_id).order_by(Follow.id).offset(offset).limit(per_page).all()
    )

    items = [f.follower.to_dict() for f in follows]
    total = db.query(func.count(Follow.id)).filter(Follow.user_id == user_id).scalar()
    return 200, {"items": items, "total": total}
