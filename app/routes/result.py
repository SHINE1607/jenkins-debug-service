from fastapi import HTTPException, Depends, UploadFile, File, APIRouter    
from sqlalchemy.orm import Session
from typing import List, Any
from collections import defaultdict
import json
import os
import google.generativeai as genai
import time
from app.db.init_db import get_session
from app.core.utils import process_test_file, analyze_failures
from app.core.config import settings
from app.models import TestResult
from datetime import datetime, timezone
import asyncio

router = APIRouter(prefix="/result", tags=["result"])

@router.post(
        "/upload", 
        response_model=Any
        )
async def create_or_update_test_result(
    files: List[UploadFile] = File(...), 
    session: Session = Depends(get_session)
    ):
    
    response = []
    for file in files:
        class_results = defaultdict(lambda: {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'fail_percentage': 0,
            'failure_details': [],
            'analysis': {
                'causes': [],
                'solutions': []
            }
        })
        try:
            # Read and parse JSON content
            content = await file.read()
            file_content = json.loads(content.decode())
            test_info = process_test_file(file_content)
            if test_info and test_info['class_name']:
                class_name = test_info['class_name']
                class_results[class_name]['total_tests'] += 1
                
                if test_info['status'] == 'passed':
                    class_results[class_name]['passed'] += 1
                elif test_info['status'] == 'failed':
                    class_results[class_name]['failed'] += 1
                    if test_info['failure_data']:
                        # Add test file information to failure details
                        failure_data = test_info['failure_data']
                        failure_data['test_file'] = file.filename
                        class_results[class_name]['failure_details'].append(failure_data)
            class_results = analyze_failures(class_results)
            
            # Save results to database asynchronously
            for class_name, result in class_results.items():
                # Calculate fail percentage
                if result['total_tests'] > 0:
                    result['fail_percentage'] = (result['failed'] / result['total_tests']) * 100
                
                # Create or update test result
                test_result = session.query(TestResult).filter_by(test_name=class_name).first()
                if test_result:
                    # Update existing record
                    test_result.total_tests = result['total_tests']
                    test_result.passed = result['passed']
                    test_result.failed = result['failed']
                    test_result.fail_percentage = result['fail_percentage']
                    test_result.failure_details = result['failure_details']
                    test_result.analysis = result['analysis']
                    test_result.last_updated = datetime.now(timezone.utc)
                    test_result.version += 1
                else:
                    # Create new record
                    test_result = TestResult(
                        test_name=class_name,
                        total_tests=result['total_tests'],
                        passed=result['passed'],
                        failed=result['failed'],
                        fail_percentage=result['fail_percentage'],
                        failure_details=result['failure_details'],
                        analysis=result['analysis']
                    )
                    session.add(test_result)
                
                # Commit changes asynchronously
                await asyncio.to_thread(session.commit)
            
            response.append(class_results)
        except Exception as e:
            print(f"Error processing {file.filename}: {str(e)}")
            session.rollback()
            
    return {"message": "Test results uploaded successfully"} 

            


            
