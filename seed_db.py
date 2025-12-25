"""Seed the SQLite database with users and follower relationships.

Creates >= 10k users and >= 10k follow relationships as required by the input.json.
Also creates an auxiliary table `user_counts` (for the upcoming optimization) but
in baseline it's only populated so the schema change exists for the optimized run.
"""
import random
from faker import Faker
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from models import Base, User, Follow, UserStats
from app import DATABASE_URL, engine

fake = Faker()

NUM_USERS = 15000
NUM_FOLLOWS = 30000


def seed(force: bool = False):
    print(f"Initializing DB ({DATABASE_URL}) and seeding data...")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as s:
        existing = s.query(User).count()
        if existing >= NUM_USERS and not force:
            print(f"DB already has {existing} users — skipping full reseed (will ensure auxiliary tables exist)")
        else:
            print("Clearing tables and inserting users...")
            s.query(Follow).delete()
            s.query(User).delete()
            s.commit()

            users = [User(username=fake.user_name() + str(i)) for i in range(NUM_USERS)]
            s.bulk_save_objects(users)
            s.commit()

            user_ids = [u.id for u in s.query(User.id).all()]
            follows = []
            for _ in range(NUM_FOLLOWS):
                a = random.choice(user_ids)
                b = random.choice(user_ids)
                if a == b:
                    continue
                follows.append(Follow(user_id=a, follower_id=b))

            s.bulk_save_objects(follows)
            s.commit()

        # ensure user_stats exists and is populated (idempotent)
        stats_count = s.query(UserStats).count()
        if stats_count < NUM_USERS:
            print(f"Populating user_stats (found {stats_count})...")
            user_ids = [u.id for u in s.query(User.id).all()]
            follower_counts = dict()
            for f in s.query(Follow.user_id, func.count(Follow.id)).group_by(Follow.user_id):
                follower_counts[f[0]] = f[1]

            # delete existing then bulk insert (idempotent)
            s.execute("DELETE FROM user_stats")
            stats = []
            for uid in user_ids:
                stats.append({"user_id": uid, "followers_count": follower_counts.get(uid, 0), "posts_count": random.randint(0, 50)})
            s.execute(
                "INSERT INTO user_stats (user_id, followers_count, posts_count) VALUES (:user_id, :followers_count, :posts_count)",
                stats,
            )
            s.commit()

        # populate app_meta with a precomputed users_count to avoid COUNT(*) at read time
        from models import AppMeta
        existing_meta = {m.key: m.value_int for m in s.query(AppMeta).all()}
        if existing_meta.get('users_count', 0) != NUM_USERS:
            s.execute("DELETE FROM app_meta")
            s.execute("INSERT INTO app_meta (key, value_int) VALUES (:k, :v)", [{"k": "users_count", "v": NUM_USERS}])
            s.commit()

    print(f"Seed complete: users={NUM_USERS} follows~={NUM_FOLLOWS}")


if __name__ == "__main__":
    seed()
