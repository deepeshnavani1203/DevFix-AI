import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from mcp_server.server import run_tests

def test_runner_passing_assertions():
    solution = """def is_even(n):
    return n % 2 == 0
"""
    tests = """assert is_even(4) is True
assert is_even(3) is False
"""
    result = run_tests(solution, tests, timeout_seconds=3)
    assert result["passed"] is True
    assert result["status"] == "passed"

def test_runner_failing_assertion():
    solution = """def add(a, b):
    return a - b
"""
    tests = """assert add(2, 2) == 4"""
    result = run_tests(solution, tests, timeout_seconds=3)
    assert result["passed"] is False
    assert result["status"] == "failed"
    assert "AssertionError" in result["stderr"]

def test_runner_infinite_loop_timeout():
    solution = """def loop_forever():
    while True:
        pass
"""
    tests = """loop_forever()"""
    result = run_tests(solution, tests, timeout_seconds=1)
    assert result["passed"] is False
    assert result["status"] == "timeout"

def test_runner_security_disallowed_call():
    solution = """def exploit():
    eval('__import__(\"os\").system(\"echo hacked\")')
"""
    tests = """exploit()"""
    result = run_tests(solution, tests, timeout_seconds=2)
    assert result["passed"] is False
    assert result["status"] == "security_block"
