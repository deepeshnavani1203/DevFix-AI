import urllib.request
import json

def test_code(name, code):
    req = urllib.request.Request(
        'http://localhost:8000/api/debug',
        data=json.dumps({'code': code, 'error_message': ''}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    print(f"=== {name} ===")
    print("Detected error:", data.get("error_type"))
    print("Corrected code:\n", repr(data.get("corrected_code")))
    print("Test code:\n", repr(data.get("test_code")))
    print("Validation:\n", json.dumps(data.get("validation_result"), indent=2))
    print()

test_code("Syntax error unclosed quote", 'name = \'Deepesh"\nprint(name)')
test_code("Dict KeyError", 'user = {"id": 1}\nprint(user["name"])')
