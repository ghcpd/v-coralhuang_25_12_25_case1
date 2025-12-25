"""SQLAlchemy models for the users + followers demo (baseline implementation).

This baseline intentionally includes two known performance traps:
- handlers call COUNT(*) on every paginated request
- followers are accessed via relationship (causing N+1)

The optimized change will be introduced later and clearly documented.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Index,
    Table,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, index=True)

    def to_dict(self):
        return {"id": self.id, "username": self.username}

class Follow(Base):
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), index=True)

    # baseline: lazy relationship (can cause N+1)
    follower = relationship("User", foreign_keys=[follower_id], lazy="select")

# NOTE: composite index is intentionally *absent* in baseline to reproduce the trap

class UserStats(Base):
    """Small per-user stats table. Baseline code will fetch this per-user (N+1).
    The optimized change will fetch stats in bulk with a single query.
    """
    __tablename__ = "user_stats"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    followers_count = Column(Integer, nullable=False, default=0, index=True)
    posts_count = Column(Integer, nullable=False, default=0)

    def to_dict(self):
        return {"user_id": self.user_id, "followers_count": self.followers_count, "posts_count": self.posts_count}


class AppMeta(Base):
    """Lightweight key/value table for precomputed counters (single-row lookups).
    Used to avoid COUNT(*) on large tables for read-heavy endpoints.
    """
    __tablename__ = "app_meta"
    key = Column(String(50), primary_key=True)
    value_int = Column(Integer, nullable=False, default=0)

    def to_dict(self):
        return {"key": self.key, "value_int": self.value_int}


# Add composite index on follows to speed follower lookups (optimized schema change)
Index("ix_follows_user_follower", Follow.user_id, Follow.follower_id)

