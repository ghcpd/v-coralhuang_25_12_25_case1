"""Request handlers that mimic REST endpoints without running a server.
They accept a dict-like request object: {"method":..., "path":..., "query":{...}, "headers":{...}}
Return (status_code, json_body)
"""
from sqlalchemy import func
from models import User, Relationship, Counter
from app import get_db_session, config

DEFAULT_PER_PAGE = 100


def _auth_ok(headers):
    auth = headers.get("Authorization") or headers.get("authorization")
    if not auth:
        return False
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        return token == config["AUTH_TOKEN"]
    return False


def get_users(request):
    """List users with pagination.

    Baseline: uses COUNT(*) on every request (expensive), selects full ORM objects.
    Optimized: avoids COUNT by reading from counters table if present; selects only columns.
    """
    if not _auth_ok(request.get("headers", {})):
        return 401, {"error": "unauthorized"}

    q = request.get("query", {})
    page = int(q.get("page", 1))
    per_page = int(q.get("per_page", DEFAULT_PER_PAGE))
    offset = (page - 1) * per_page

    session = get_db_session()
    try:
        if config["OPTIMIZED"]:
            # Read cached total from the in-memory counters cache to avoid a DB read per request
            from app import counters_cache
            total = counters_cache.get("users_total")
            if total is None:
                # fallback to DB count if cache missing
                total = session.query(func.count(User.id)).scalar()
            # select only required columns
            rows = session.query(User.id, User.username).order_by(User.id).offset(offset).limit(per_page).all()
            users = [{"id": r.id, "username": r.username} for r in rows]
        else:
            # baseline: expensive count and full objects
            total = session.query(func.count(User.id)).scalar()
            users = session.query(User).order_by(User.id).offset(offset).limit(per_page).all()
            users = [{"id": u.id, "username": u.username} for u in users]

        return 200, {"data": users, "meta": {"page": page, "per_page": per_page, "total": total}}
    finally:
        session.close()


def get_user_followers(request, user_id):
    """List followers for a user with pagination.

    Baseline: retrieves follower ids then fetches User for each follower (N+1).
    Optimized: performs a single join query to fetch follower user info in one query and relies on composite index.
    """
    if not _auth_ok(request.get("headers", {})):
        return 401, {"error": "unauthorized"}

    q = request.get("query", {})
    page = int(q.get("page", 1))
    per_page = int(q.get("per_page", DEFAULT_PER_PAGE))
    offset = (page - 1) * per_page

    session = get_db_session()
    try:
        if config["OPTIMIZED"]:
            # Single query join to fetch follower user rows
            rows = session.query(User.id, User.username).join(Relationship, Relationship.follower_id == User.id).filter(Relationship.user_id == int(user_id)).order_by(User.id).offset(offset).limit(per_page).all()
            users = [{"id": r.id, "username": r.username} for r in rows]
            # we can also get total via COUNT on relationships (not expensive with index), but keep consistent
            total = session.query(func.count(Relationship.id)).filter(Relationship.user_id == int(user_id)).scalar()
        else:
            # baseline: N+1 -> first get follower ids, then fetch each User separately
            follower_rows = session.query(Relationship.follower_id).filter_by(user_id=int(user_id)).order_by(Relationship.follower_id).offset(offset).limit(per_page).all()
            users = []
            for fr in follower_rows:
                u = session.query(User).get(fr.follower_id)
                users.append({"id": u.id, "username": u.username})
            total = session.query(func.count(Relationship.id)).filter(Relationship.user_id == int(user_id)).scalar()

        return 200, {"data": users, "meta": {"page": page, "per_page": per_page, "total": total}}
    finally:
        session.close()
