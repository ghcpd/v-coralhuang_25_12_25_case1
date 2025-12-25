"""
Seed script to create schema and populate users + followers.
Creates 10,000 users and 20,000 follower relationships by default.
Also populates `counters` table with users count (used by optimized handler).
Run: python seed_db.py
"""
from app import create_schema, get_db_session, User, Follower, Counter

NUM_USERS = 10000
NUM_FOLLOWERS = 20000


def seed():
    print(f"Creating schema and seeding {NUM_USERS} users + {NUM_FOLLOWERS} follower rows...")
    create_schema()
    db = get_db_session()
    try:
        # bulk insert users
        users = [User(id=i+1, name=f'user_{i+1}') for i in range(NUM_USERS)]
        db.bulk_save_objects(users)
        db.commit()

        # create follower relationships (simple pattern to ensure many rows)
        followers = []
        for i in range(NUM_FOLLOWERS):
            user_id = (i % 1000) + 1   # distribute followers across first 1000 users
            follower_id = ((i + 1) % NUM_USERS) + 1
            followers.append(Follower(user_id=user_id, follower_id=follower_id))
        db.bulk_save_objects(followers)
        db.commit()

        # populate counters table with users total (used by optimized handler)
        existing = db.query(Counter).filter(Counter.name == 'users').one_or_none()
        if existing:
            existing.value = NUM_USERS
        else:
            db.add(Counter(name='users', value=NUM_USERS))
        db.commit()

        print("Seeding complete.")
    finally:
        db.close()


if __name__ == '__main__':
    seed()
