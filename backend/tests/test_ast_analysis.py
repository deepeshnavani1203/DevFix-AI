import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from mcp_server.server import analyze_code, read_error_log

def test_syntax_valid():
    code = "def add(a, b):\n    return a + b"
    result = analyze_code(code)
    assert result["syntax_valid"] is True
    assert len(result["functions"]) == 1
    assert result["functions"][0]["name"] == "add"

def test_syntax_invalid():
    code = "def broken(:\n    pass"
    result = analyze_code(code)
    assert result["syntax_valid"] is False
    assert result["syntax_error_line"] == 1
    assert "SyntaxError" in result["warnings"][0]

def test_risky_call_detection():
    code = "import os\ndef run_danger():\n    eval('2 + 2')\n    os.system('ls')"
    result = analyze_code(code)
    assert result["syntax_valid"] is True
    risky_calls = [c["call"] for c in result["risky_calls"]]
    assert "eval" in risky_calls or "system" in risky_calls

def test_mutable_default_warning():
    code = "def append_item(x, target=[]):\n    target.append(x)\n    return target"
    result = analyze_code(code)
    assert result["syntax_valid"] is True
    assert any("mutable default" in w for w in result["warnings"])

def test_traceback_parser():
    tb = """Traceback (most recent call last):
  File "calculator.py", line 14, in compute_ratio
    return total / count
ZeroDivisionError: division by zero"""
    parsed = read_error_log(tb)
    assert parsed["has_error"] is True
    assert parsed["exception_type"] == "ZeroDivisionError"
    assert parsed["message"] == "division by zero"
    assert parsed["probable_line"] == 14
    assert len(parsed["frames"]) == 1
