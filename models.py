"""SQLAlchemy ORM models and metadata creation."""
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Index, Table

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, index=True)

class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)  # the user being followed
    follower_id = Column(Integer, index=True)  # the user who follows

    # composite index to speed lookup by (user_id, follower_id)
    __table_args__ = (Index("ix_relationship_user_follower", "user_id", "follower_id"),)

class Counter(Base):
    __tablename__ = "counters"
    key = Column(String, primary_key=True)
    value = Column(Integer)
