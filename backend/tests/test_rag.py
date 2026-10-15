import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from rag.retriever import rag_retriever
from services.qdrant_service import qdrant_service, sanitize_code_and_text

def test_qdrant_has_records():
    count = qdrant_service.count()
    assert count >= 35, f"Expected at least 35 records, got {count}"

def test_rag_retrieval_similarity():
    query = "ZeroDivisionError denominator is zero when calculating average"
    hits = rag_retriever.retrieve(query, limit=2)
    assert len(hits) > 0
    top = hits[0]
    assert "ZeroDivisionError" in top["error_type"] or top["score"] > 0.0

def test_sanitize_secrets():
    leak_code = 'api_key = "sk-1234567890abcdef1234567890"\npassword = "secretPassword123"'
    cleaned = sanitize_code_and_text(leak_code)
    assert "sk-1234567890abcdef1234567890" not in cleaned
    assert "[REDACTED_SECRET]" in cleaned
