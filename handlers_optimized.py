"""
Optimized handlers:
- GET /api/users: avoid COUNT(*) by reading pre-computed value from `counters` table; keep pagination semantics identical.
- GET /api/users/1/followers: fetch follower user rows with a single JOIN (no N+1).

These changes keep the same request/response shape but reduce DB work per request.
"""
from typing import Dict, Any
from app import get_db_session, User, Follower, Counter
from sqlalchemy import select, join

# authentication check (fixed token)
def _check_auth(headers: Dict[str, str]):
    auth = headers.get('Authorization', '')
    if auth != 'Bearer test-token':
        return False
    return True


def _parse_pagination(query: Dict[str, Any]):
    page = int(query.get('page', 1))
    per_page = int(query.get('per_page', 20))
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20
    return page, per_page


def get_users(request):
    """Optimized: read total from counters table (O(1)) and use OFFSET for rows."""
    if not _check_auth(request.headers):
        return 401, {'error': 'unauthorized'}

    page, per_page = _parse_pagination(request.query)
    offset = (page - 1) * per_page

    db = get_db_session()
    try:
        # read pre-computed total from counters table instead of COUNT(*)
        counter = db.query(Counter).filter(Counter.name == 'users').one_or_none()
        total = counter.value if counter is not None else db.query(User).count()

        users_q = db.query(User).order_by(User.id).offset(offset).limit(per_page)
        users = [{'id': u.id, 'name': u.name} for u in users_q]

        return 200, {
            'page': page,
            'per_page': per_page,
            'total': total,
            'items': users
        }
    finally:
        db.close()


def get_user_followers(request):
    """Optimized: single JOIN query to avoid N+1."""
    if not _check_auth(request.headers):
        return 401, {'error': 'unauthorized'}

    parts = request.path.strip('/').split('/')
    user_id = int(parts[2])

    page, per_page = _parse_pagination(request.query)
    offset = (page - 1) * per_page

    db = get_db_session()
    try:
        # single query: join followers -> users to fetch follower user data in one roundtrip
        rows = (
            db.query(User.id, User.name)
              .join(Follower, Follower.follower_id == User.id)
              .filter(Follower.user_id == user_id)
              .order_by(Follower.id)
              .offset(offset)
              .limit(per_page)
              .all()
        )
        items = [{'id': r.id, 'name': r.name} for r in rows]

        return 200, {
            'page': page,
            'per_page': per_page,
            'items': items
        }
    finally:
        db.close()
