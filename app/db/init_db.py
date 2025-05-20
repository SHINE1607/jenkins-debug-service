from app.core.config import settings, logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from app.models import Base
import asyncio
import os
import sys
from pathlib import Path

schema_name = settings.DB_SCHEMA
connection_string = settings.DB_CONNECTION_STRING(
    environment=settings.ENVIRONMENT)

# Create engine with connection pooling
engine = create_engine(
    connection_string, 
    pool_size=20,
    max_overflow=20,
    pool_timeout=60,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    session = SessionLocal()
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        session.close()

async def init_db():
    """Initialize the database by creating all tables and schemas."""
    try:
        # Create schema if it doesn't exist
        with engine.connect() as connection:
            logger.info("Creating database schema...")
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name};"))
            connection.commit()
            logger.info(f"Schema {schema_name} created or already exists")

        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    except SQLAlchemyError as e:
        logger.error(f"Error initializing database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize database: {str(e)}"
        )

if __name__ == "__main__":
    asyncio.run(init_db())
