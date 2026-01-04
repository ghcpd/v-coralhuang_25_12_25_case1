"""
Baseline app with known performance bottlenecks.
Used for measuring baseline performance before optimization.
"""
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, Index, func
import os
import json

app = Flask(__name__)

# Database configuration
db_path = os.path.join(os.path.dirname(__file__), "api_performance.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Global query counter for performance tracking
class QueryCounter:
    def __init__(self):
        self.queries = []
        self.count = 0
    
    def reset(self):
        self.queries = []
        self.count = 0
    
    def get_count(self):
        return self.count

query_counter = QueryCounter()

# Register query listener lazily within app context
def setup_query_listener():
    @event.listens_for(db.engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        query_counter.count += 1
        query_counter.queries.append(statement)

# ORM Models
class User(db.Model):
    __tablename__ = "user"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    
    # Relationships with lazy loading (causes N+1)
    followers = db.relationship(
        "Follower",
        foreign_keys="Follower.user_id",
        backref="user_obj",
        lazy="select"  # Lazy loading causes N+1 queries
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email
        }

class Follower(db.Model):
    __tablename__ = "follower"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    follower_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # NO COMPOSITE INDEX - this is the bottleneck
    
    follower_user = db.relationship(
        "User",
        foreign_keys=[follower_id],
        lazy="select"  # Lazy loading without joinedload causes N+1
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "follower_id": self.follower_id,
            "follower": self.follower_user.to_dict() if self.follower_user else None
        }

# Authentication middleware
def check_auth():
    """Verify bearer token"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    token = auth_header[7:]
    # Accept the fixed test token
    return token == "test-token"

def require_auth(f):
    """Decorator to require authentication"""
    def wrapper(*args, **kwargs):
        if not check_auth():
            return {"error": "Unauthorized"}, 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# API Handlers (handlers module simulation)
class handlers:
    @staticmethod
    @require_auth
    def get_users():
        """
        GET /api/users - Paginated list of all users
        BOTTLENECK: Uses COUNT(*) on every request
        """
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 100, type=int)
        
        # Bottleneck: COUNT(*) executes on every paginated request
        total = db.session.query(func.count(User.id)).scalar()
        
        users = User.query.limit(per_page).offset((page - 1) * per_page).all()
        
        return jsonify({
            "data": [u.to_dict() for u in users],
            "page": page,
            "per_page": per_page,
            "total": total
        }), 200
    
    @staticmethod
    @require_auth
    def get_user_followers():
        """
        GET /api/users/1/followers - Paginated followers of a user
        BOTTLENECK: N+1 queries due to lazy-loaded relationships and no composite index
        """
        user_id = 1
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 100, type=int)
        
        # Bottleneck: This causes N+1 queries
        # 1 query to get followers, then 1 query per follower to get the follower_user
        followers = db.session.query(Follower).filter(
            Follower.user_id == user_id
        ).limit(per_page).offset((page - 1) * per_page).all()
        
        return jsonify({
            "user_id": user_id,
            "followers": [f.to_dict() for f in followers],
            "page": page,
            "per_page": per_page
        }), 200

# Routes
@app.route("/api/users", methods=["GET"])
def get_users():
    return handlers.get_users()

@app.route("/api/users/1/followers", methods=["GET"])
def get_user_followers():
    return handlers.get_user_followers()

if __name__ == "__main__":
    app.run(debug=False, threaded=True)
