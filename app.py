"""Application wiring: DB, session, instrumentation, and config."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import contextvars

# context var to hold per-request query counter
current_request_id = contextvars.ContextVar("current_request_id", default=None)
query_count_store = {}

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

config = {"OPTIMIZED": False, "AUTH_TOKEN": "test-token"}

# SQLAlchemy event listener to count queries per request
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    req_id = current_request_id.get()
    if req_id is not None:
        query_count_store.setdefault(req_id, 0)
        query_count_store[req_id] += 1


def get_query_count_for_request(req_id):
    return query_count_store.get(req_id, 0)


def reset_query_counts():
    query_count_store.clear()

# simple in-memory counters cache used by optimized handlers to avoid a DB read per request
counters_cache = {}

def load_counters_from_db():
    # populate counters_cache from DB
    session = SessionLocal()
    try:
        from models import Counter
        for c in session.query(Counter).all():
            counters_cache[c.key] = c.value
    finally:
        session.close()


def get_db_session():
    return SessionLocal()
