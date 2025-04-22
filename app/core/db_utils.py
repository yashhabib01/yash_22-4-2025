from contextlib import contextmanager
from sqlalchemy.orm import Session
from .database import SessionLocal

@contextmanager
def get_db_session():
    """Provide a transactional scope around a series of operations."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close() 