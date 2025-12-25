"""
Database seed script - generates test data with >= 10000 users and >= 10000 relationships.
"""
import os
from app import app, db, User, Follower, setup_query_listener

def seed_database():
    """Populate the database with test data"""
    
    with app.app_context():
        # Setup query listener
        setup_query_listener()
        # Drop all tables and recreate
        db.drop_all()
        db.create_all()
        
        print("Seeding database...")
        
        # Create >= 10000 users
        num_users = 10000
        print(f"Creating {num_users} users...")
        
        for i in range(1, num_users + 1):
            user = User(
                username=f"user_{i}",
                email=f"user_{i}@example.com"
            )
            db.session.add(user)
            
            if i % 1000 == 0:
                db.session.commit()
                print(f"  ... {i} users created")
        
        db.session.commit()
        print(f"[OK] All {num_users} users created")
        
        # Create >= 10000 relationships
        # User 1 has relationships with users 2-10001 (10000 followers)
        print("Creating 10000+ relationships...")
        
        num_relationships = 10000
        for j in range(2, num_relationships + 2):
            follower = Follower(
                user_id=1,
                follower_id=j
            )
            db.session.add(follower)
            
            if (j - 1) % 1000 == 0:
                db.session.commit()
                print(f"  ... {j - 1} relationships created")
        
        db.session.commit()
        print(f"[OK] All {num_relationships} relationships created")
        
        print("\n[OK] Database seeding complete!")

if __name__ == "__main__":
    seed_database()
