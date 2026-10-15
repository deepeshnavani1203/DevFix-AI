import urllib.request
import json
import time

test_scenarios = [
    {
        "name": "SyntaxError: Unterminated string",
        "code": "name = 'Deepesh\"\nprint(name)",
        "error": ""
    },
    {
        "name": "NameError: Typo variable name",
        "code": "name = 'Deepesh'\nprint(na)",
        "error": ""
    },
    {
        "name": "ZeroDivisionError: Division by zero",
        "code": "def divide(a, b):\n    return a / b\nprint(divide(10, 0))",
        "error": ""
    },
    {
        "name": "KeyError: Missing dict key",
        "code": "user = {'id': 101}\nprint(user['email'])",
        "error": ""
    },
    {
        "name": "IndexError: Out of bounds",
        "code": "items = [10, 20]\nprint(items[5])",
        "error": ""
    },
    {
        "name": "TypeError: Unsupported operand types",
        "code": "score = 100\nmsg = 'Score: ' + score\nprint(msg)",
        "error": ""
    },
    {
        "name": "AttributeError: NoneType attribute",
        "code": "def find_user():\n    return None\nu = find_user()\nprint(u.lower())",
        "error": ""
    },
    {
        "name": "UnboundLocalError: Scoped counter",
        "code": "val = 10\ndef inc():\n    val += 1\n    return val\nprint(inc())",
        "error": ""
    },
    {
        "name": "Code with No Error: Clean function",
        "code": "def multiply(x, y):\n    return x * y\nprint(multiply(3, 4))",
        "error": ""
    }
]

print(f"{'Test Scenario':<38} | {'Status':<8} | {'Detected Error':<18} | {'Elapsed':<7}")
print("-" * 80)

for sc in test_scenarios:
    t0 = time.time()
    try:
        req = urllib.request.Request(
            'http://localhost:8000/api/debug',
            data=json.dumps({'code': sc['code'], 'error_message': sc['error']}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        res = urllib.request.urlopen(req, timeout=30)
        data = json.loads(res.read())
        elapsed = round(time.time() - t0, 2)
        val_status = data.get("validation_result", {}).get("status", "unknown").upper()
        err_type = data.get("error_type", "None")[:17]
        print(f"{sc['name']:<38} | {val_status:<8} | {err_type:<18} | {elapsed}s")
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"{sc['name']:<38} | ERROR    | {str(e)[:18]} | {elapsed}s")
