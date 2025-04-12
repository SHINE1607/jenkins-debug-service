import json
import os
import argparse
import google.generativeai as genai
from typing import Dict, Any, Optional

def parse_jenkins_test_report(json_file_path: str) -> Dict[str, Any]:
    """
    Parse a Jenkins test report JSON file and extract relevant debugging information.
    
    Args:
        json_file_path: Path to the Jenkins JSON test report
        
    Returns:
        Dictionary containing relevant debugging information
    """
    try:
        with open(json_file_path, 'r') as f:
            report = json.load(f)
        
        # Extract basic test information
        test_name = report.get('name', 'Unknown Test')
        full_name = report.get('fullName', 'Unknown Full Name')
        description = report.get('description', 'No description available')
        
        # Extract status information
        status = report.get('status', 'Unknown')
        status_message = report.get('statusMessage', 'No status message available')
        status_trace = report.get('statusTrace', 'No stack trace available')
        
        # Extract timing information
        duration_ms = report.get('time', {}).get('duration', 0)
        duration_sec = duration_ms / 1000
        
        # Create the base debug info structure
        debug_info = {
            "test_info": {
                "name": test_name,
                "full_name": full_name,
                "description": description,
                "status": status,
                "duration_seconds": duration_sec
            },
            "history": extract_history_info(report)
        }
        
        # Only add error information and analysis if the test failed
        if status.lower() in ['failed', 'broken']:
            # Extract error location information
            error_location = extract_error_location(status_trace)
            
            # Extract stage information
            stage_info = extract_stage_info(report)
            
            # Get Gemini analysis for possible cause and fix
            gemini_analysis = get_gemini_analysis(status_message, status_trace, description)
            
            # Add error-specific information
            debug_info["error_info"] = {
                "message": status_message,
                "location": error_location,
                "stage": stage_info
            }
            
            debug_info["analysis"] = gemini_analysis
        else:
            # For passing tests, just add a simple message
            debug_info["summary"] = "Test passed successfully. No debugging information needed."
        
        return debug_info
    
    except Exception as e:
        return {"error": f"Failed to parse Jenkins test report: {str(e)}"}

def extract_error_location(stack_trace: str) -> Dict[str, Any]:
    """
    Extract file name and line number from stack trace.
    
    Args:
        stack_trace: The stack trace string from the test report
        
    Returns:
        Dictionary containing file name and line number
    """
    location = {"file": "Unknown", "line": "Unknown", "method": "Unknown"}
    
    if not stack_trace or stack_trace == 'No stack trace available':
        return location
    
    # Look for common Java stack trace patterns
    lines = stack_trace.split('\n')
    for line in lines:
        if '.java:' in line:
            parts = line.strip().split('(')
            if len(parts) > 1:
                # Extract method name
                method_parts = parts[0].strip().split('.')
                if method_parts:
                    location["method"] = method_parts[-1]
                
                # Extract file and line
                file_info = parts[1].split(')')[0]
                if ':' in file_info:
                    file_parts = file_info.split(':')
                    location["file"] = file_parts[0]
                    location["line"] = file_parts[1] if len(file_parts) > 1 else "Unknown"
                    break
    
    return location

def extract_stage_info(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract information about the stage where the failure occurred.
    
    Args:
        report: The parsed JSON test report
        
    Returns:
        Dictionary containing stage information
    """
    stage_info = {"name": "Unknown", "phase": "Unknown"}
    
    # Check if failure occurred in before stages
    before_stages = report.get('beforeStages', [])
    for stage in before_stages:
        if stage.get('status') == 'failed':
            stage_info["name"] = stage.get('name', 'Unknown')
            stage_info["phase"] = "Setup"
            return stage_info
    
    # Check if failure occurred in test stage
    test_stage = report.get('testStage', {})
    if test_stage.get('status') == 'failed':
        stage_info["name"] = "Test Execution"
        stage_info["phase"] = "Test"
        return stage_info
    
    # Check if failure occurred in after stages
    after_stages = report.get('afterStages', [])
    for stage in after_stages:
        if stage.get('status') == 'failed':
            stage_info["name"] = stage.get('name', 'Unknown')
            stage_info["phase"] = "Teardown"
            return stage_info
    
    return stage_info

def extract_history_info(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant history information about the test.
    
    Args:
        report: The parsed JSON test report
        
    Returns:
        Dictionary containing history information
    """
    history = report.get('extra', {}).get('history', {})
    stats = history.get('statistic', {})
    
    return {
        "total_runs": stats.get('total', 0),
        "pass_rate": calculate_pass_rate(stats),
        "consistently_failing": is_consistently_failing(history.get('items', []))
    }

def calculate_pass_rate(stats: Dict[str, int]) -> float:
    """Calculate the pass rate from test statistics."""
    total = stats.get('total', 0)
    if total == 0:
        return 0.0
    
    passed = stats.get('passed', 0)
    return round((passed / total) * 100, 2)

def is_consistently_failing(history_items: list) -> bool:
    """Determine if the test has been consistently failing."""
    if not history_items or len(history_items) < 3:
        return False
    
    # Check the last 3 runs
    recent_items = history_items[:3]
    failing_statuses = ['failed', 'broken']
    
    return all(item.get('status') in failing_statuses for item in recent_items)

def get_gemini_analysis(status_message: str, stack_trace: str, description: str) -> Dict[str, str]:
    """
    Get analysis from Gemini about possible causes and fixes.
    
    Args:
        status_message: The error message
        stack_trace: The stack trace
        description: Test description
        
    Returns:
        Dictionary containing possible cause and fix
    """
    # Default response if Gemini call fails
    default_response = {
        "possible_cause": "Could not determine cause. Please analyze the error message and stack trace manually.",
        "possible_fix": "Could not determine fix. Please review the code at the error location."
    }
    
    # Get API key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: No API key found for Gemini. Using default analysis.")
        return default_response
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Set up the model
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Prepare the prompt for Gemini
        prompt = f"""
        Analyze this test failure and provide a concise explanation of the possible cause and fix.
        
        Test description: {description}
        Error message: {status_message}
        Stack trace: {stack_trace}
        
        Please respond with a JSON object containing two fields:
        1. "possible_cause": A brief explanation of what might have caused this error
        2. "possible_fix": A suggestion for how to fix this issue
        
        Keep each field under 200 characters and focus on the most likely explanation based on the error details.
        """
        
        # Generate response from Gemini
        response = model.generate_content(prompt)
        
        try:
            # Try to parse the Gemini response as JSON
            content = response.text
            
            # Check if the response contains JSON
            if '{' in content and '}' in content:
                # Extract JSON part from the response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
                
                llm_analysis = json.loads(json_str)
                return {
                    "possible_cause": llm_analysis.get("possible_cause", default_response["possible_cause"]),
                    "possible_fix": llm_analysis.get("possible_fix", default_response["possible_fix"])
                }
            else:
                # If no JSON format, try to extract information based on keywords
                cause = ""
                fix = ""
                
                lines = content.split('\n')
                for line in lines:
                    if "possible cause" in line.lower() or "possible_cause" in line.lower():
                        cause = line.split(":", 1)[1].strip() if ":" in line else line
                    elif "possible fix" in line.lower() or "possible_fix" in line.lower():
                        fix = line.split(":", 1)[1].strip() if ":" in line else line
                
                if cause and fix:
                    return {
                        "possible_cause": cause[:200],
                        "possible_fix": fix[:200]
                    }
                
                # If we couldn't extract structured information, use the whole response
                return {
                    "possible_cause": "Based on Gemini analysis: " + content[:200],
                    "possible_fix": "Review the error message and fix the assertion in the test code"
                }
                
        except json.JSONDecodeError:
            print("Warning: Could not parse Gemini response as JSON")
            return default_response
            
    except Exception as e:
        print(f"Warning: Failed to get Gemini analysis: {str(e)}")
        return default_response

def main():
    parser = argparse.ArgumentParser(description='Process Jenkins test report JSON files')
    parser.add_argument('input_file', help='Path to the Jenkins test report JSON file')
    parser.add_argument('--output', help='Path to save the output JSON file (optional)')
    
    args = parser.parse_args()
    
    debug_info = parse_jenkins_test_report(args.input_file)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(debug_info, f, indent=2)
        print(f"Debug information saved to {args.output}")
    else:
        print(json.dumps(debug_info, indent=2))

if __name__ == "__main__":
    main()