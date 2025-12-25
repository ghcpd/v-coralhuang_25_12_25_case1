"""Seed the database with users and relationships to meet dataset assumptions.

This script creates >= 10000 users and >= 10000 relationships.
It also populates a Counter "users_total" for optimized handler use.
"""
from app import engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Relationship, Counter
from faker import Faker
from tqdm import trange

Session = sessionmaker(bind=engine)

def seed(users_count=10000, rel_count=10000, force=False, hotspot_user_followers=50000):
    if force:
        # drop and recreate
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    fake = Faker()
    session = Session()

    # re-seed if needed or forced
    existing = session.query(User).count()
    if existing >= users_count and not force:
        print(f"Already seeded: {existing} users")
        session.close()
        return

    print(f"Seeding {users_count} users...")
    users = [User(username=fake.user_name() + str(i)) for i in range(users_count)]
    session.bulk_save_objects(users)
    session.commit()

    # refresh to get ids
    user_ids = [u.id for u in session.query(User.id).all()]

    print(f"Seeding {rel_count} relationships (hotspot to user 1 = {hotspot_user_followers})...")
    rels = []
    n = len(user_ids)
    hotspot_user_id = user_ids[0]

    # assign a large number of followers to user 1 to reveal N+1
    assign_hotspot = min(hotspot_user_followers, rel_count)
    for i in range(assign_hotspot):
        follower_id = user_ids[(i + 10) % n]
        rels.append(Relationship(user_id=hotspot_user_id, follower_id=follower_id))

    # remaining relationships distributed round-robin
    remaining = rel_count - assign_hotspot
    for i in range(remaining):
        uidx = user_ids[(i + assign_hotspot) % n]
        fidx = user_ids[(i + assign_hotspot + 1) % n]
        rels.append(Relationship(user_id=uidx, follower_id=fidx))

    session.bulk_save_objects(rels)
    session.commit()

    # populate counter
    c = Counter(key="users_total", value=users_count)
    session.merge(c)
    session.commit()
    session.close()
    print("Seeding complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=10000)
    parser.add_argument("--rels", type=int, default=10000)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--hotspot", type=int, default=50000)
    args = parser.parse_args()
    seed(users_count=args.users, rel_count=args.rels, force=args.force, hotspot_user_followers=args.hotspot)
