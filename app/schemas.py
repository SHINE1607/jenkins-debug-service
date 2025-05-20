from pydantic import BaseModel, field_validator
from typing import List, Annotated, Any, Dict
from datetime import datetime, timezone

class TestResultResponse(BaseModel):
    test_name: str
    total_tests: int
    passed: int
    failed: int
    fail_percentage: float
    failure_details: List[Dict[str, Any]]
    analysis: Dict[str, Any]
    