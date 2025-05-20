import json
import time
from app.core.config import get_model
from app.models import TestResult
from app.schemas import TestResultResponse
from typing import List
from sqlalchemy.orm import Session

def process_test_file(data):
    try:
        # Extract test information
        class_name = None
        status = data.get('status', '')
        failure_message = data.get('statusMessage', '')
        failure_trace = data.get('statusTrace', '')
        
        # Get class name from labels
        for label in data.get('labels', []):
            if label['name'] == 'testClass':
                class_name = label['value']
                break
        
        # Extract detailed failure location from stack trace
        failure_location = None
        if failure_trace:
            # Split stack trace into lines
            stack_lines = failure_trace.split('\n')
            for line in stack_lines:
                if 'at ' in line and '(' in line and ')' in line:
                    try:
                        # Extract the method and file information
                        method_part = line.split('at ')[1].split('(')[0].strip()
                        file_part = line.split('(')[1].split(')')[0]
                        
                        # Split file part into file and line number
                        file_parts = file_part.split(':')
                        if len(file_parts) >= 2:
                            file_name = file_parts[0]
                            line_number = file_parts[1]
                            
                            failure_location = {
                                'file': file_name,
                                'line': line_number,
                                'method': method_part,
                                'full_stack_line': line.strip()
                            }
                            break
                    except:
                        continue
        
        return {
            'class_name': class_name,
            'status': 'failed' if status in ['failed', 'broken'] else status,
            'failure_data': {
                'message': failure_message,
                'trace': failure_trace,
                'failure_location': failure_location,
                'test_method': data.get('name', ''),  # Add test method name
                'full_test_name': data.get('fullName', '')  # Add full test name
            } if status in ['failed', 'broken'] else None
        }
    except Exception as e:
        print(f"Error processing file {data}: {str(e)}")
        return None

def generate_failure_analysis(failure_data):
    model = get_model()
    prompt = f"""
    Analyze these test failure details and provide a detailed analysis:
    1. Possible causes (be specific about the technical reasons)
    2. Possible solutions (provide concrete steps to resolve)
    
    Failure Details:
    Error Message: {failure_data['message']}
    Stack Trace: {failure_data['trace']}
    
    Format the response as JSON with the following structure:
    {{
        "causes": [
            {{
                "cause": "detailed cause description",
                "confidence": "high/medium/low",
                "technical_details": "specific technical explanation"
            }}
        ],
        "solutions": [
            {{
                "solution": "detailed solution steps",
                "priority": "high/medium/low",
                "implementation_steps": ["step1", "step2", ...]
            }}
        ]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Add delay to respect API rate limits
        time.sleep(1)
        
        # Extract the JSON part from the response
        response_text = response.text
        # Find the first '{' and last '}'
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in response")
            
    except Exception as e:
        print(f"Error in analyze_failures: {str(e)}")
        return {
            "causes": [{
                "cause": "Error analyzing failures",
                "confidence": "low",
                "technical_details": str(e)
            }],
            "solutions": [{
                "solution": "Unable to generate solutions",
                "priority": "low",
                "implementation_steps": ["Check the error logs"]
            }]
        }

def analyze_failures(class_results):
    for class_name, results in class_results.items():
        if results['total_tests'] > 0:
            results['fail_percentage'] = (results['failed'] / results['total_tests']) * 100
            
            # Analyze failures if any
            if results['failure_details']:
                print(f"Analyzing failures for class: {class_name}")
                # Combine all failure details for analysis
                combined_failures = {
                    'message': '\n'.join(f['message'] for f in results['failure_details']),
                    'trace': '\n'.join(f['trace'] for f in results['failure_details'])
                }
                analysis = generate_failure_analysis(combined_failures)
                results['analysis'] = analysis
    return dict(class_results)

def push_to_db(test_results: List[TestResultResponse], session: Session):
    for test_result in test_results:
        test_result_obj = TestResult(**test_result)
        session.add(test_result_obj)
    session.commit()
