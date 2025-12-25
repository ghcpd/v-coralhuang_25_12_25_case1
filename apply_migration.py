"""
Apply non-destructive migrations (create missing indexes/tables).
This script calls SQLAlchemy's create_all so new Index objects are created without dropping data.
"""
from app import Base, engine

if __name__ == '__main__':
    print('Applying migrations (create_all)...')
    Base.metadata.create_all(bind=engine)
    print('Migrations applied.')
