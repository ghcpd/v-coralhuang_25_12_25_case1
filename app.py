"""Minimal application import surface required by the test harness.

The test runner will import `app` (this module) and use `handlers` as entrypoints.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base
import handlers

# SQLite database file local to workspace for reproducibility
DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = scoped_session(sessionmaker(bind=engine))


def init_db():
    Base.metadata.create_all(bind=engine)


# expose the handlers module so the runner can import by the mapping in input.json
__all__ = ["handlers", "init_db", "SessionLocal", "engine"]
