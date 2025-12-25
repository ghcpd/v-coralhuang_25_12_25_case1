"""
Baseline handlers (for audit):
- GET /api/users: uses COUNT(*) for total and OFFSET-based pagination
- GET /api/users/1/followers: loads follower rows and then queries user info per follower (N+1)
"""
from typing import Dict, Any
from app import get_db_session, User, Follower

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
    """Baseline: OFFSET pagination + COUNT(*) per request (slow on large tables)."""
    if not _check_auth(request.headers):
        return 401, {'error': 'unauthorized'}

    page, per_page = _parse_pagination(request.query)
    offset = (page - 1) * per_page

    db = get_db_session()
    try:
        # COUNT(*) executed on every paginated request (expensive)
        total = db.query(User).count()

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
    """Baseline: causes N+1 by loading follower user info lazily per follower."""
    if not _check_auth(request.headers):
        return 401, {'error': 'unauthorized'}

    # path like /api/users/1/followers -> extract user id (simple implementation)
    parts = request.path.strip('/').split('/')
    user_id = int(parts[2])

    page, per_page = _parse_pagination(request.query)
    offset = (page - 1) * per_page

    db = get_db_session()
    try:
        # load follower rows
        follower_rows = db.query(Follower).filter(Follower.user_id == user_id).order_by(Follower.id).offset(offset).limit(per_page).all()

        # N+1: for each follower row, we query the follower's user record
        items = []
        for fr in follower_rows:
            u = db.query(User).filter(User.id == fr.follower_id).one()
            items.append({'id': u.id, 'name': u.name})

        return 200, {
            'page': page,
            'per_page': per_page,
            'items': items
        }
    finally:
        db.close()
