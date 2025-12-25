from app import db, app
from models import User, Follow
import random
from sqlalchemy import text

with app.app_context():
    db.create_all()
    db.session.execute(text('PRAGMA journal_mode=WAL;'))
    db.session.commit()
    users = [User(name=f'User {i}') for i in range(10000)]
    db.session.add_all(users)
    db.session.commit()
    follows = []
    for _ in range(20000):
        user_id = random.randint(1, 10000)
        follower_id = random.randint(1, 10000)
        if user_id != follower_id:
            follows.append(Follow(user_id=user_id, follower_id=follower_id))
    db.session.add_all(follows)
    db.session.commit()