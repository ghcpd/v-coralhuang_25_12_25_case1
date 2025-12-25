from flask import request, jsonify, abort
from app import db
from models import User, Follow
from sqlalchemy import func
from sqlalchemy.orm import selectinload

def authenticate():
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        abort(401)
    token = auth[7:]
    if token != 'test-token':
        abort(401)

def get_users():
    authenticate()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 100))
    offset = (page - 1) * per_page
    # optimized: still 2 queries, but perhaps faster
    total = db.session.query(func.count(User.id)).scalar()
    users = db.session.query(User).offset(offset).limit(per_page).all()
    return jsonify({'users': [{'id': u.id, 'name': u.name} for u in users], 'total': total, 'page': page, 'per_page': per_page})

def get_user_followers(user_id):
    authenticate()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 100))
    offset = (page - 1) * per_page
    # optimized: join to avoid N+1, 2 queries
    total = db.session.query(func.count(Follow.id)).filter(Follow.user_id == user_id).scalar()
    follows = db.session.query(Follow, User).join(User, Follow.follower_id == User.id).filter(Follow.user_id == user_id).offset(offset).limit(per_page).all()
    followers = [{'id': u.id, 'name': u.name} for f, u in follows]
    return jsonify({'followers': followers, 'total': total, 'page': page, 'per_page': per_page})