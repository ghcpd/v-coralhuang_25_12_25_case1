"""
Minimal app module exposing the DB session, models and helper to create the schema.
This module is intentionally simple so handlers can import models and sessions.
"""
from sqlalchemy import (create_engine, Column, Integer, String, ForeignKey, Index, Table)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = "sqlite:///./test_perf.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)

class Follower(Base):
    __tablename__ = 'followers'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    follower_id = Column(Integer, index=True, nullable=False)

    # Baseline: no composite index (known perf trap). Optimized run will add an index here.
    __table_args__ = (
        Index('ix_followers_user_follower', 'user_id', 'follower_id'),
    )


class Counter(Base):
    __tablename__ = 'counters'
    name = Column(String, primary_key=True)
    value = Column(Integer, nullable=False)


def create_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


# small helper used by runner & seed
def get_db_session():
    return SessionLocal()
