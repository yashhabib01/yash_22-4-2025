from sqlalchemy import Column, Integer, String, DateTime, Enum, Time, JSON
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class StoreStatus(enum.Enum):
    active = "active"
    inactive = "inactive"

class ReportStatus(enum.Enum):
    running = "Running"
    completed = "Complete"
    failed = "Failed"

class StoreStatusLog(Base):
    __tablename__ = "store_status_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(36), index=True) 
    timestamp_utc = Column(DateTime, nullable=False)
    status = Column(Enum(StoreStatus), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class BusinessHours(Base):
    __tablename__ = "business_hours"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(36), index=True)  
    day_of_week = Column(Integer, nullable=False)  
    start_time_local = Column(Time, nullable=False)
    end_time_local = Column(Time, nullable=False)

class StoreTimezone(Base):
    __tablename__ = "store_timezones"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(36), unique=True, index=True)  
    timezone_str = Column(String(50), nullable=False, default="America/Chicago")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(100), unique=True, index=True)
    status = Column(Enum(ReportStatus), default=ReportStatus.running)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    url = Column(String(500), nullable=True) 