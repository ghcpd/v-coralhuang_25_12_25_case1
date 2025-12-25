from app import db, app
from models import Follow

with app.app_context():
    count = db.session.query(db.func.count(Follow.id)).filter_by(user_id=1).scalar()
    print(f"User 1 has {count} followers")