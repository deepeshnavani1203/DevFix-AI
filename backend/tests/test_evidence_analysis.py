import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient

from agents.analyzer import error_analysis_agent
from main import app
from mcp_server.server import analyze_code


def analyze(code):
    return error_analysis_agent({"code": code, "error_message": "", "request_id": "test"})


def test_correct_print_has_no_findings():
    result = analyze('print("Hello World")')
    assert result["issues"] == []
    assert result["status"] == "no_issues_detected"
    assert result["execution_result"]["executed"] is True


def test_name_error_is_confirmed_from_execution():
    result = analyze("print(unknown_variable)")
    issue = next(issue for issue in result["issues"] if issue["error_type"] == "NameError")
    assert issue["line"] == 1
    assert issue["confirmed"] is True
    assert "unknown_variable" in issue["explanation"]


def test_literal_zero_division_is_confirmed():
    result = analyze("print(10 / 0)")
    issue = next(issue for issue in result["issues"] if issue["error_type"] == "ZeroDivisionError")
    assert issue["line"] == 1
    assert issue["confirmed"] is True


def test_multiple_independent_bugs_include_masked_empty_input():
    code = "def calculate_average(marks):\n    return sum(marks) / len(mark)\n\nprint(calculate_average([]))"
    ast_result = analyze_code(code)
    assert {issue["error_type"] for issue in ast_result["issues"]} == {"NameError", "ZeroDivisionError"}
    result = analyze(code)
    assert any(issue["error_type"] == "NameError" and issue["confirmed"] for issue in result["issues"])
    zero_division = next(issue for issue in result["issues"] if issue["error_type"] == "ZeroDivisionError")
    assert not zero_division["confirmed"]
    assert "masked" in zero_division["explanation"]


def test_guarded_average_has_no_findings():
    code = "def calculate_average(numbers):\n    if not numbers:\n        return 0.0\n    return sum(numbers) / len(numbers)\n\nprint(calculate_average([10, 20, 30]))"
    result = analyze(code)
    assert result["issues"] == []
    assert result["status"] == "no_issues_detected"


def test_workflow_failure_is_not_returned_as_fake_success(monkeypatch):
    import main

    monkeypatch.setattr(main, "run_debugging_session", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("workflow unavailable")))
    with TestClient(app) as client:
        response = client.post("/api/debug", json={"code": "print(1)"})
    assert response.status_code == 500
    assert "Analysis failed" in response.json()["detail"]
