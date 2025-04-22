from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create the base class
Base = declarative_base()

# Create engine and session
engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import models here to avoid circular imports
    from app.models.models import StoreStatusLog, BusinessHours, StoreTimezone, Report
    Base.metadata.create_all(bind=engine) 