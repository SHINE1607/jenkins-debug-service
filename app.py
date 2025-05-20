from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from sqlalchemy import create_engine, Column, String, Integer, Float, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os
import google.generativeai as genai
import time
from fastapi.responses import JSONResponse

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyCDSyBtofxUkuL5YWKWiNbSvuu2uD7vYPU")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Database configuration
DB_USER = os.getenv("DB_USER", "shine")
DB_PASSWORD = os.getenv("DB_PASSWORD", "45TraderManv4!!")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "debug")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine with connection pool settings
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class TestResult(Base):
    __tablename__ = "test_results"

    test_name = Column(String, primary_key=True)
    total_tests = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    fail_percentage = Column(Float, default=0.0)
    failure_details = Column(JSONB)  # List of failure details
    analysis = Column(JSONB)  # Contains causes and solutions
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)  # For tracking changes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with history
    history = relationship("TestResultHistory", back_populates="test_result")

class TestResultHistory(Base):
    __tablename__ = "test_result_history"

    id = Column(Integer, primary_key=True)
    test_name = Column(String, ForeignKey('test_results.test_name'))
    version = Column(Integer)
    total_tests = Column(Integer)
    passed = Column(Integer)
    failed = Column(Integer)
    fail_percentage = Column(Float)
    failure_details = Column(JSONB)
    analysis = Column(JSONB)
    change_type = Column(String)  # 'create', 'update', 'delete'
    changed_at = Column(DateTime, default=datetime.utcnow)
    changed_by = Column(String)  # Could be system or user identifier
    change_reason = Column(Text, nullable=True)

    # Relationship with main table
    test_result = relationship("TestResult", back_populates="history")

# Pydantic models for request/response
class FailureLocation(BaseModel):
    file: str
    line: str
    method: str
    full_stack_line: str

class FailureDetail(BaseModel):
    message: str
    trace: str
    failure_location: Optional[FailureLocation]
    test_method: str
    full_test_name: str
    test_file: str

class Cause(BaseModel):
    cause: str
    confidence: str
    technical_details: str

class Solution(BaseModel):
    solution: str
    priority: str
    implementation_steps: List[str]

class Analysis(BaseModel):
    causes: List[Cause]
    solutions: List[Solution]

class TestResultCreate(BaseModel):
    test_name: str
    total_tests: int
    passed: int
    failed: int
    fail_percentage: float
    failure_details: List[FailureDetail]
    analysis: Analysis

class TestResultResponse(TestResultCreate):
    last_updated: datetime
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class TestResultHistoryResponse(BaseModel):
    id: int
    test_name: str
    version: int
    total_tests: int
    passed: int
    failed: int
    fail_percentage: float
    failure_details: List[FailureDetail]
    analysis: Analysis
    change_type: str
    changed_at: datetime
    changed_by: str
    change_reason: Optional[str]

    class Config:
        orm_mode = True

class BatchUploadResponse(BaseModel):
    total_files: int
    processed_files: int
    failed_files: List[str]
    success_message: str

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="Jenkins Debug Service")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_history_entry(db: SessionLocal, test_result: TestResult, change_type: str, changed_by: str, change_reason: Optional[str] = None):
    """Create a history entry for a test result change"""
    history_entry = TestResultHistory(
        test_name=test_result.test_name,
        version=test_result.version,
        total_tests=test_result.total_tests,
        passed=test_result.passed,
        failed=test_result.failed,
        fail_percentage=test_result.fail_percentage,
        failure_details=test_result.failure_details,
        analysis=test_result.analysis,
        change_type=change_type,
        changed_by=changed_by,
        change_reason=change_reason
    )
    db.add(history_entry)
    db.commit()

@app.post("/test-results/", response_model=TestResultResponse)
async def create_or_update_test_result(test_result: TestResultCreate, db: SessionLocal = Depends(get_db)):
    db_test = db.query(TestResult).filter(TestResult.test_name == test_result.test_name).first()
    
    if db_test:
        # Update existing record
        old_version = db_test.version
        for key, value in test_result.dict().items():
            setattr(db_test, key, value)
        db_test.version = old_version + 1
        db_test.updated_at = datetime.utcnow()
        
        # Create history entry for update
        create_history_entry(
            db, 
            db_test, 
            'update', 
            'system', 
            f'Updated test result from version {old_version} to {db_test.version}'
        )
    else:
        # Create new record
        db_test = TestResult(**test_result.dict())
        db.add(db_test)
        
        # Create history entry for creation
        create_history_entry(
            db, 
            db_test, 
            'create', 
            'system', 
            'Initial test result creation'
        )
    
    db.commit()
    db.refresh(db_test)
    return db_test

@app.get("/test-results/{test_name}", response_model=TestResultResponse)
async def get_test_result(test_name: str, db: SessionLocal = Depends(get_db)):
    db_test = db.query(TestResult).filter(TestResult.test_name == test_name).first()
    if db_test is None:
        raise HTTPException(status_code=404, detail="Test result not found")
    return db_test

@app.get("/test-results/", response_model=List[TestResultResponse])
async def get_all_test_results(db: SessionLocal = Depends(get_db)):
    return db.query(TestResult).filter(TestResult.is_active == True).all()

@app.get("/test-results/{test_name}/history", response_model=List[TestResultHistoryResponse])
async def get_test_result_history(test_name: str, db: SessionLocal = Depends(get_db)):
    history = db.query(TestResultHistory).filter(
        TestResultHistory.test_name == test_name
    ).order_by(TestResultHistory.changed_at.desc()).all()
    return history

@app.post("/upload-job-files/", response_model=BatchUploadResponse)
async def upload_job_files(files: List[UploadFile] = File(...), db: SessionLocal = Depends(get_db)):
    processed_files = 0
    failed_files = []
    
    for file in files:
        try:
            # Read and parse JSON content
            content = await file.read()
            file_content = json.loads(content.decode())
            
            # Process each test result in the file
            for test_name, test_data in file_content.items():
                try:
                    test_result = TestResultCreate(
                        test_name=test_name,
                        total_tests=test_data["total_tests"],
                        passed=test_data["passed"],
                        failed=test_data["failed"],
                        fail_percentage=test_data["fail_percentage"],
                        failure_details=test_data["failure_details"],
                        analysis=test_data["analysis"]
                    )
                    await create_or_update_test_result(test_result, db)
                except KeyError as e:
                    failed_files.append(f"{file.filename} - {test_name}: Missing required field {str(e)}")
                except Exception as e:
                    failed_files.append(f"{file.filename} - {test_name}: {str(e)}")
            
            processed_files += 1
                
        except json.JSONDecodeError:
            failed_files.append(f"{file.filename}: Invalid JSON format")
        except Exception as e:
            failed_files.append(f"{file.filename}: {str(e)}")
    
    return BatchUploadResponse(
        total_files=len(files),
        processed_files=processed_files,
        failed_files=failed_files,
        success_message=f"Successfully processed {processed_files} out of {len(files)} files"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 