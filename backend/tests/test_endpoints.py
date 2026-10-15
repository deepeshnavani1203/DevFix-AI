import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "groq" in data["services"]
    assert "qdrant" in data["services"]
    assert "mcp_server" in data["services"]
    assert "langgraph" in data["services"]

def test_debug_endpoint_basic():
    payload = {
        "code": "def div(a, b):\n    return a / b\n\nres = div(10, 0)",
        "error_message": "ZeroDivisionError: division by zero"
    }
    response = client.post("/api/debug", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "error_type" in data
    assert "root_cause" in data
    assert "corrected_code" in data
    assert "validation_result" in data
    assert "rag_references" in data
    assert "mcp_calls_made" in data
    assert len(data["mcp_calls_made"]) >= 1

def test_history_endpoint():
    response = client.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert data["total"] >= 1

def test_knowledge_list_endpoint():
    response = client.get("/api/knowledge")
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert data["total_in_collection"] >= 35
