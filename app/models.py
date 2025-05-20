from app.core.config import settings
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

Base = declarative_base()

class TestResult(Base):
    __tablename__ = "test_results"

    test_name = Column(String, primary_key=True)
    total_tests = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    fail_percentage = Column(Float, default=0.0)
    failure_details = Column(JSONB)  # List of failure details
    analysis = Column(JSONB)  # Contains causes and solutions
    last_updated = Column(DateTime, default=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)  # For tracking changes
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))



