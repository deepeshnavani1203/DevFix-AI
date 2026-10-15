import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_dynamic_analysis_name_error():
    """Verify that a NameError code input dynamically produces a NameError diagnosis and fix."""
    payload = {
        "code": "def greet():\n    return 'Hello ' + unknown_user_name\n\nprint(greet())",
        "error_message": "NameError: name 'unknown_user_name' is not defined"
    }
    response = client.post("/api/debug", json=payload)
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()

    assert data["request_id"].startswith("req_")
    assert data["error_type"] == "NameError"
    # Ensure it did NOT return the hardcoded ZeroDivision demo!
    assert "ZeroDivisionError" not in data["error_type"]
    assert "calculate_average" not in data["corrected_code"]
    assert "unknown_user_name" in data["corrected_code"] or "greet" in data["corrected_code"]
    assert data["validation_result"]["passed"] is True
    assert "analyze_code" in data["mcp_calls_made"]
    assert "run_tests" in data["mcp_calls_made"]

def test_dynamic_analysis_index_error():
    """Verify that an IndexError code input dynamically produces an IndexError diagnosis and fix."""
    payload = {
        "code": "def get_third_element(items):\n    return items[2]\n\nres = get_third_element([10])",
        "error_message": "IndexError: list index out of range"
    }
    response = client.post("/api/debug", json=payload)
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()

    assert data["request_id"].startswith("req_")
    assert data["error_type"] == "IndexError"
    assert "ZeroDivisionError" not in data["error_type"]
    assert "calculate_average" not in data["corrected_code"]
    assert "get_third_element" in data["corrected_code"] or "items" in data["corrected_code"]
    assert data["validation_result"]["passed"] is True
    assert "search_debug_knowledge" in data["mcp_calls_made"]

def test_dynamic_analysis_zero_division():
    """Verify that a ZeroDivisionError code input produces a tailored fix for its specific function."""
    payload = {
        "code": "def compute_velocity(distance, time_elapsed):\n    return distance / time_elapsed\n\nv = compute_velocity(100, 0)",
        "error_message": "ZeroDivisionError: division by zero"
    }
    response = client.post("/api/debug", json=payload)
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()

    assert data["request_id"].startswith("req_")
    assert data["error_type"] == "ZeroDivisionError"
    # Must fix compute_velocity, NOT the hardcoded calculate_average demo
    assert "compute_velocity" in data["corrected_code"]
    assert "time_elapsed" in data["corrected_code"]
    assert data["validation_result"]["passed"] is True
