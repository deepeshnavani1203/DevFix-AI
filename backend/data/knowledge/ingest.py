import sys
import json
import uuid
import hashlib
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from typing import List, Dict, Any
from qdrant_client.models import PointStruct
from rag.embeddings import embedding_model
from rag.chunking import prepare_knowledge_item
from services.qdrant_service import qdrant_service, sanitize_code_and_text

KNOWLEDGE_JSON_PATH = Path(__file__).resolve().parent / "python_errors.json"

def get_deterministic_id(key: str) -> str:
    """Creates a deterministic UUID from an item key to ensure idempotency and prevent duplicates."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"devfix_{key}"))

def ingest_knowledge_file(file_path: Path = KNOWLEDGE_JSON_PATH) -> Dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"Knowledge file not found at {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Knowledge JSON must contain an array of error objects.")

    prepared_docs = [prepare_knowledge_item(item) for item in data]
    texts = [doc["text"] for doc in prepared_docs]

    print(f"Generating embeddings for {len(texts)} knowledge items...")
    vectors = embedding_model.encode(texts)

    points = []
    for doc, vector in zip(prepared_docs, vectors):
        point_id = get_deterministic_id(doc["id"])
        
        # Sanitize payload just in case
        payload = {
            **doc["metadata"],
            "text": sanitize_code_and_text(doc["text"]),
            "root_cause": sanitize_code_and_text(doc["metadata"].get("root_cause", "")),
            "buggy_code": sanitize_code_and_text(doc["metadata"].get("buggy_code", "")),
            "corrected_code": sanitize_code_and_text(doc["metadata"].get("corrected_code", "")),
        }

        points.append(PointStruct(
            id=point_id,
            vector=vector,
            payload=payload
        ))

    success = qdrant_service.upsert_points(points)
    total_count = qdrant_service.count()

    return {
        "success": success,
        "ingested_count": len(points),
        "total_collection_count": total_count,
        "message": f"Successfully ingested {len(points)} verified debugging cases into Qdrant collection."
    }

def add_single_debugging_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """Saves an opt-in user approved debugging case to the knowledge base."""
    # Ensure sensitive data is completely scrubbed
    raw_code = sanitize_code_and_text(case.get("code", ""))
    corrected = sanitize_code_and_text(case.get("corrected_code", ""))
    root_cause = sanitize_code_and_text(case.get("root_cause", ""))
    test_code = sanitize_code_and_text(case.get("test_code", ""))

    case_id = case.get("id") or f"user-case-{uuid.uuid4().hex[:8]}"
    item = {
        "id": case_id,
        "error_type": case.get("error_type", "UserVerifiedError"),
        "title": case.get("title") or f"Fix for {case.get('error_type', 'Python issue')}",
        "root_cause": root_cause,
        "buggy_code": raw_code,
        "corrected_code": corrected,
        "test_code": test_code,
        "category": "UserVerified",
        "tags": ["user-saved", case.get("error_type", "").lower()],
        "source": "user_saved_case",
        "language": "python"
    }

    doc = prepare_knowledge_item(item)
    vector = embedding_model.encode_one(doc["text"])
    point_id = get_deterministic_id(case_id)

    point = PointStruct(
        id=point_id,
        vector=vector,
        payload=doc["metadata"]
    )

    success = qdrant_service.upsert_points([point])
    return {
        "success": success,
        "point_id": point_id,
        "title": item["title"],
        "error_type": item["error_type"],
    }

if __name__ == "__main__":
    result = ingest_knowledge_file()
    print(result)
