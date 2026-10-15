import urllib.request
import json
import time

test_cases = [
    {
        "name": "Undefined variable (NameError)",
        "code": "def greet(name):\n    return 'Hello ' + na\nprint(greet('Deepesh'))",
        "error": ""
    },
    {
        "name": "Syntax Error unclosed quote",
        "code": "name = 'Deepesh\"\nprint(name)",
        "error": ""
    },
    {
        "name": "ZeroDivisionError without error log",
        "code": "def avg(lst):\n    return sum(lst)/len(lst)\nprint(avg([]))",
        "error": ""
    },
    {
        "name": "IndexError out of range",
        "code": "nums = [1, 2, 3]\nprint(nums[10])",
        "error": ""
    },
    {
        "name": "Dict KeyError",
        "code": "user = {'id': 1}\nprint(user['name'])",
        "error": ""
    },
    {
        "name": "Mutable default argument bug",
        "code": "def add_item(item, items=[]):\n    items.append(item)\n    return items\nprint(add_item(1))\nprint(add_item(2))",
        "error": ""
    }
]

for tc in test_cases:
    t0 = time.time()
    try:
        req = urllib.request.Request(
            'http://localhost:8000/api/debug',
            data=json.dumps({'code': tc['code'], 'error_message': tc['error']}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        res = urllib.request.urlopen(req, timeout=30)
        data = json.loads(res.read())
        elapsed = round(time.time() - t0, 2)
        print(f"[{tc['name']}] Elapsed: {elapsed}s | Detected: {data.get('error_type')} (line {data.get('error_line')}) | Validation: {data.get('status')}")
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"[{tc['name']}] FAILED in {elapsed}s: {e}")
